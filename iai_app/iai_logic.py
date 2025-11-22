import json
import os
import re
from typing import Any, Dict, List

from openai import OpenAI

WEIGHTS_IAI = {
    "FSI": 0.30,
    "MPI": 0.25,
    "PTI": 0.20,
    "TMI": 0.15,
    "RRI": 0.10,
    "PI": 0.05,
}

# Явно берём ключ из переменной окружения
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def slugify(name: str) -> str:
    normalized = name.strip().lower()
    normalized = re.sub(r"[^a-z0-9\s\-а-яё]", "", normalized)
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = normalized.replace("--", "-")
    return normalized or "company"


def calculate_iai(subindices: Dict[str, Any]) -> float:
    total_weight = 0.0
    weighted_sum = 0.0
    for key, weight in WEIGHTS_IAI.items():
        node = subindices.get(key) or {}
        try:
            score = float(node.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        if score > 0:
            weighted_sum += score * weight
            total_weight += weight
    if total_weight == 0:
        return 0.0
    return round(weighted_sum / total_weight, 1)


def evaluate_company(company_name: str) -> Dict[str, Any]:
    research = _run_subindex_research(company_name)
    research_subindices = research.get("subindices", {})
    research_tags = research.get("tags", [])

    aggregation = _run_final_aggregation(company_name, research_subindices, research_tags)

    subindices = aggregation.get("subindices") or research_subindices
    cleaned_subindices = _sanitize_subindices(subindices)

    iai_value = aggregation.get("iai") or calculate_iai(cleaned_subindices)

    return {
        "company_name": aggregation.get("company_name") or research.get("company_name") or company_name,
        "tags": aggregation.get("tags") or research_tags,
        "subindices": cleaned_subindices,
        "iai": round(float(iai_value), 1),
    }


def _run_subindex_research(company_name: str) -> Dict[str, Any]:
    methodology_prompt = f"""
    Проведи глубокое исследование компании "{company_name}". Используй web-search для поиска фактических источников (официальные сайты, регуляторные реестры, СМИ, отчёты). Для каждого субиндекса IAI сформируй оценку 0–10 и минимум 2 факта с конкретными числами/метриками и рабочими URL-источниками. Структура ответа — только JSON:
    {{
      "company_name": "...",
      "tags": ["..."],
      "subindices": {{
        "FSI": {{"score": <float>, "facts": [{{"title": "...", "description": "...", "sources": ["https://..."]}}]}},
        "MPI": {{"score": <float>, "facts": [{{"title": "...", "description": "...", "sources": ["https://..."]}}]}},
        "PTI": {{"score": <float>, "facts": [{{"title": "...", "description": "...", "sources": ["https://..."]}}]}},
        "TMI": {{"score": <float>, "facts": [{{"title": "...", "description": "...", "sources": ["https://..."]}}]}},
        "RRI": {{"score": <float>, "facts": [{{"title": "...", "description": "...", "sources": ["https://..."]}}]}},
        "PI":  {{"score": <float>, "facts": [{{"title": "...", "description": "...", "sources": ["https://..."]}}]}}
      }}
    }}

    Методология и веса: FSI 30%, MPI 25%, PTI 20%, TMI 15%, RRI 10%, PI 5%. Применяй бэнды из методологии (рост выручки, маржа, Net Debt/EBITDA, NPS, TRL, локализация, точность прогнозов и др.) и выводи дробные баллы, если необходимо. Если данных нет — ставь score 0 и факт "нет данных" без выдуманных ссылок. Сохраняй только реальные ссылки, найденные через поиск.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Ты инвестиционный аналитик. Всегда проверяешь данные через web-search и возвращаешь только правдоподобные факты и рабочие URL. Формат ответа — строгий JSON без пояснений.",
            },
            {"role": "user", "content": methodology_prompt},
        ],
        temperature=0.3,
        max_tokens=1400,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Пустой ответ от модели (этап исследования)")

    return json.loads(content)


def _run_final_aggregation(company_name: str, subindices: Dict[str, Any], tags: List[str]) -> Dict[str, Any]:
    aggregation_prompt = """
    На основе уже собранных фактов и оценок рассчитай итоговый индекс IAI. Используй только предоставленные факты и источники, не придумывай новые данные. Применяй веса: FSI 30%, MPI 25%, PTI 20%, TMI 15%, RRI 10%, PI 5%.

    Верни JSON:
    {
      "company_name": "...",
      "tags": [...],
      "subindices": { same structure как вход },
      "iai": <float 0-10 с округлением до 0.1>
    }

    Оставь источники без изменений, сохрани по 2–3 ключевых факта на субиндекс и пересчитай score при необходимости по той же методологии.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Ты агрегируешь результаты 6 промптов и считаешь итоговый индекс по весовой модели IAI. Формат ответа — валидный JSON для UI, только на основе переданных данных.",
            },
            {"role": "user", "content": json.dumps({"company_name": company_name, "tags": tags, "subindices": subindices}, ensure_ascii=False)},
            {"role": "user", "content": aggregation_prompt},
        ],
        temperature=0.2,
        max_tokens=800,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Пустой ответ от модели (агрегация)")

    return json.loads(content)


def _sanitize_subindices(subindices: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for key, block in subindices.items():
        facts = []
        for fact in block.get("facts", []):
            sources = [src.strip() for src in fact.get("sources", []) if _is_http_url(src)]
            facts.append(
                {
                    "title": fact.get("title", ""),
                    "description": fact.get("description", ""),
                    "sources": sources,
                }
            )
        cleaned[key] = {
            "score": block.get("score", 0),
            "facts": facts,
        }
    return cleaned


def _is_http_url(value: str) -> bool:
    return isinstance(value, str) and value.strip().lower().startswith(("http://", "https://"))

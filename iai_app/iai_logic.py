import json
import os
import re
from typing import Dict, Any

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
    prompt = f"""
    Ты — аналитик инвестиций. Оцени инвестиционную привлекательность компании "{company_name}".
    Верни только валидный JSON без дополнительного текста. Структура:
    {{
      "company_name": "...",
      "tags": ["..."],
      "subindices": {{
        "FSI": {{"score": <float 0-10>, "facts": [{{"title": "...", "description": "...", "sources": ["..."]}}]}},
        "MPI": {{"score": <float 0-10>, "facts": [{{"title": "...", "description": "...", "sources": ["..."]}}]}},
        "PTI": {{"score": <float 0-10>, "facts": [{{"title": "...", "description": "...", "sources": ["..."]}}]}},
        "TMI": {{"score": <float 0-10>, "facts": [{{"title": "...", "description": "...", "sources": ["..."]}}]}},
        "RRI": {{"score": <float 0-10>, "facts": [{{"title": "...", "description": "...", "sources": ["..."]}}]}},
        "PI":  {{"score": <float 0-10>, "facts": [{{"title": "...", "description": "...", "sources": ["..."]}}]}}
      }}
    }}

    Оценивай каждую метрику по данным из открытых источников (финансы, рынок, продукт, команда, риски, планы).
    Значения score должны быть числами от 0 до 10 (можно дробные).
    Не добавляй пояснений до или после JSON.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Ты помогаешь инвестору оценивать стартапы и компании по шести метрикам: FSI, MPI, PTI, TMI, RRI, PI. Возвращай только JSON указанной структуры.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=1200,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Пустой ответ от модели")

    data = json.loads(content)
    subindices = data.get("subindices", {})
    iai_value = calculate_iai(subindices)
    data["iai"] = iai_value
    return data

import json
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


client = OpenAI()


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
    Ты — аналитик инвестиций. Оцени инвестиционную привлекательность компании "{company_name}" по методологии IAI (шесть субиндексов). Верни только валидный JSON без дополнительного текста. Структура:
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

    Методология и веса: FSI 30%, MPI 25%, PTI 20%, TMI 15%, RRI 10%, PI 5%.
    Коды и смысл: FSI = Financial Strength & Integrity (рентабельность, долговая нагрузка, OpCF), MPI = Market Potential & Intensity (CAGR, гео и каналы, конкуренция), PTI = Product & Technology Intensity (TRL, IP, R&D), TMI = Team & Management Integrity (лидеры, совет, ESOP, аудит, CG), RRI = Risk & Resilience Index (локализация, IP-риски, санкции, зависимость от B2G, компонентные риски), PI = Plan & Implementation (MAPE/WAPE, hit-ratio KPI, консистентность с CAGR).
    Считай score по бэндам 0–10 (можно дробные). Используй диапазоны:
    - Рост выручки YoY (%): <0→2; 0–10→3; 10–25→5; 25–50→7; 50–100→8; 100–200→9; >200→10 (↑ лучше).
    - Net margin (%): <0→1; 0–5→3; 5–10→5; 10–20→7; 20–30→8; 30–40→9; >40→10 (↑).
    - Net Debt/EBITDA: >5→1; 4–5→3; 3–4→5; 2–3→7; 1–2→8; 0–1→9; net cash→10 (↓ лучше).
    - Interest coverage (EBIT/Interest): <1.5→1; 1.5–2.5→3; 2.5–4→5; 4–6→7; 6–10→8; 10–15→9; >15→10 (↑).
    - CCC (дни): >90→2; 60–90→4; 30–60→6; 10–30→8; 0–10→9; <0→10 (↓ лучше). Формула: CCC = DIO + DSO − DPO.
    - CAGR рынка (%): <5→3; 5–10→5; 10–15→7; 15–20→8; 20–30→9; >30→10 (↑).
    - HHI рынка: >2500→3; 1800–2500→5; 1500–1800→7; <1500→9–10 (↓ лучше). NPS: (NPS+100)/20 → 0–10.
    - Длина цикла сделки (дни): >180→3; 90–180→5; 45–90→7; <45→9–10 (↓).
    - PTI: TRL 1≈1 … TRL9≈10 (линейно); IP-горизонт <1г→2; 1–3→4; 3–5→6; 5–10→8; >10→10; R&D/Revenue <3→3; 3–6→5; 6–10→7; 10–20→8; >20→9–10.
    - TMI: Leadership track (низк/средн/сильн → ~3/6/9), наличие совета/независимых/ESOP/аудита повышает балл; применяй G20/OECD CG.
    - RRI: Доля B2G >70%→3; 40–70→5; 20–40→7; <20→9. Учитывай локализацию (ПП-719/СТ-1), IP-риски, судебные/санкционные кейсы, компонентные зависимости.
    - PI: MAPE/WAPE >30→3; 20–30→5; 10–20→7; 5–10→8–9; <5→10. Hit-ratio KPI ≤60→4; 60–80→6; 80–95→8–9; >95→10.

    Требования к facts: минимум 2 факта на каждый субиндекс. Каждый факт = конкретная метрика с числом/диапазоном + краткое объяснение и 1–3 источника URL. Если данных нет — ставь score 0 и факт "нет данных" без выдумок.
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

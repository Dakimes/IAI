import json
import os
from flask import Flask, render_template, request, jsonify, abort

from db import init_db, fetch_companies, fetch_company, insert_company
from iai_logic import evaluate_company, slugify


METHODOLOGY_OVERVIEW = [
    {
        "code": "FSI",
        "name_en": "Financial Strength & Integrity",
        "name_ru": "Финансовая устойчивость",
        "summary": "Масштаб, рентабельность и долговая нагрузка",
        "metrics": [
            "Рост выручки YoY, чистая маржа, OpCF/Revenue",
            "Net Debt / EBITDA, Interest Coverage",
            "CCC = DIO + DSO − DPO",
        ],
        "weight": "30%",
        "links": [
            "Investopedia: CCC и Interest Coverage",
            "Corporate Finance Institute: Net Debt / EBITDA",
        ],
    },
    {
        "code": "MPI",
        "name_en": "Market Potential & Intensity",
        "name_ru": "Рынок и динамика",
        "summary": "Скорость роста, гео и каналы, конкуренция",
        "metrics": [
            "CAGR рынка, геодиверсификация",
            "Канальная диверсификация B2G/B2B/B2E/B2C",
            "HHI концентрации, NPS, длина сделки",
        ],
        "weight": "25%",
        "links": [
            "US DOJ/FTC: HHI пороги",
            "Bain: NPS формула",
        ],
    },
    {
        "code": "PTI",
        "name_en": "Product & Technology Intensity",
        "name_ru": "Продукт и технологии",
        "summary": "Зрелость, IP и интенсивность R&D",
        "metrics": [
            "TRL 1–9, ITC (tech momentum)",
            "Портфель и качество IP, горизонт защиты",
            "R&D / Revenue",
        ],
        "weight": "20%",
        "links": ["NASA: TRL шкала"],
    },
    {
        "code": "TMI",
        "name_en": "Team & Management Integrity",
        "name_ru": "Команда и управление",
        "summary": "Лидеры, совет, мотивация и прозрачность",
        "metrics": [
            "Опыт leadership, кризисы, международность",
            "Совет/независимые, комитеты, аудит",
            "ESOP покрытие, соответствие G20/OECD",
        ],
        "weight": "15%",
        "links": ["G20/OECD: Corporate Governance"],
    },
    {
        "code": "RRI",
        "name_en": "Risk & Resilience Index",
        "name_ru": "Риски и устойчивость",
        "summary": "Регуляторика, IP-горизонт, санкции",
        "metrics": [
            "Локализация (ПП-719/СТ-1)",
            "IP-риски, судебные/санкционные кейсы",
            "Доля B2G, компонентные зависимости",
        ],
        "weight": "10%",
        "links": ["G20/OECD: governance", "HHI метод"],
    },
    {
        "code": "PI",
        "name_en": "Plan & Implementation",
        "name_ru": "Планы и исполнение",
        "summary": "Попадание в KPI и реалистичность планов",
        "metrics": [
            "MAPE/WAPE точность прогнозов",
            "Hit-ratio KPI, NPS как прокси спроса",
            "Согласованность с CAGR отрасли",
        ],
        "weight": "5%",
        "links": ["Baeldung: MAPE/WAPE разбор"],
    },
]

app = Flask(__name__)


@app.before_first_request
def setup():
    init_db()


@app.route("/")
def index():
    companies = fetch_companies()
    return render_template("index.html", companies=companies)


@app.route("/company/<slug>")
def company(slug):
    row = fetch_company(slug)
    if not row:
        abort(404)
    subindices = json.loads(row["subindices_json"])
    return render_template(
        "company.html",
        name=row["name"],
        slug=slug,
        iai=row["iai"],
        subindices=subindices.get("subindices", {}),
        tags=subindices.get("tags", []),
        methodology=METHODOLOGY_OVERVIEW,
    )


@app.route("/methodology")
def methodology():
    return render_template("methodology.html", methodology=METHODOLOGY_OVERVIEW, title="Методология IAI")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"status": "error", "message": "Название не должно быть пустым"}), 400

    slug = slugify(name)
    existing = fetch_company(slug)
    if existing:
        return jsonify({"status": "exists", "slug": slug})

    try:
        analysis = evaluate_company(name)
    except Exception as exc:  # простая обработка ошибок для MVP
        return jsonify({"status": "error", "message": str(exc)}), 500

    insert_company(slug, analysis.get("company_name", name), analysis.get("iai", 0), analysis)
    return jsonify({"status": "created", "slug": slug})


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

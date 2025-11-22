import json
import os
from flask import Flask, render_template, request, jsonify, abort

from db import init_db, fetch_companies, fetch_company, insert_company
from iai_logic import evaluate_company, slugify

app = Flask(__name__)


# Инициализация БД при старте приложения
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
    )


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

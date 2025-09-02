# services/reporting.py
from weasyprint import HTML
from jinja2 import Template
import os
from datetime import datetime
from pathlib import Path

from shared.config import IMAGES_DIR, REPORTS_DIR

# Путь к папке отчётов и изображений
IMAGES_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

def generate_explanation_pdf(data: dict, explanation: dict, filename="reports/explanation_report.pdf"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    # Сохраняем путь к изображению как относительный от base_url
    image_path = "images/shap_waterfall.png"

    html_template = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <style>
            body { font-family: sans-serif; padding: 2cm; }
            h1, h2 { color: #2c3e50; }
            .field { margin: 8px 0; }
            .decision { 
                background-color: #d4edda; 
                color: #155724; 
                padding: 10px; 
                border-radius: 5px; 
                font-weight: bold;
                margin: 15px 0;
            }
            .risk { color: #c0392b; }
            .safe { color: #27ae60; }
            .shap-img { 
                margin: 20px 0; 
                max-width: 100%; 
                border: 1px solid #ddd; 
                border-radius: 5px; 
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
        </style>
    </head>
    <body>
        <h1>Отчет по кредитному скорингу</h1>
        <p><strong>Дата:</strong> {{ now }}</p>

        <h2>Данные заемщика</h2>
        <table>
            <tr><th>Параметр</th><th>Значение</th></tr>
            {% for k, v in data.items() %}
            <tr><td>{{ k }}</td><td>{{ v }}</td></tr>
            {% endfor %}
        </table>

        <h2>Результат анализа</h2>
        <div class="decision">
            Решение: 
            {% if decision == "approve" %}
                <span class="safe">ОДОБРЕНО</span>
            {% else %}
                <span class="risk">ОТКАЗ</span>
            {% endif %}
        </div>
        <div class="field"><strong>Вероятность возврата:</strong> {{ "%.1f"|format(probability_repaid * 100) }}%</div>

        <h2>Объяснение решения</h2>
        <ul class="explanation-list">
        {% for line in explanation.explanation.summary %}
            <li>{{ line }}</li> <!--.replace('↑ риск', 'повышает риск').replace('↓ риск', 'понижает риск') }}</li>--> 
        {% endfor %}
        </ul>

        <h2>Визуализация вклада признаков</h2>
        <img src="{{ image_path }}" class="shap-img" alt="SHAP Waterfall Plot">
        <p><em>График показывает, как каждый признак повлиял на предсказание.</em></p>
    </body>
    </html>
    """

    template = Template(html_template)
    html_out = template.render(
        data=data,
        explanation=explanation, #["explanation"],
        decision="approve" if explanation["prediction"] == 0 else "reject",
        probability_repaid=explanation["probability_repaid"],
        image_path=image_path,
        now=datetime.now().strftime("%d.%m.%Y %H:%M")
    )

    # ✅ Указываем base_url — это корень проекта
    HTML(string=html_out, base_url=REPORTS_DIR.resolve()).write_pdf(target=filename)
    return filename


def generate_model_comparison_pdf(results, roc_auc_path, filename="reports/model_comparison_report.pdf"):
    html_template = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <style>
            body { font-family: sans-serif; padding: 2cm; }
            h1, h2 { color: #2c3e50; }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            .chart {
                text-align: center;
                margin: 30px 0;
            }
            .chart img {
                max-width: 100%;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <h1>📊 Сравнение моделей машинного обучения</h1>
        <p><strong>Дата:</strong> {{ now }}</p>

        <h2>Точность и AUC моделей</h2>
        <table>
            <tr><th>Модель</th><th>Точность</th><th>AUC-ROC</th></tr>
            {% for r in results %}
            <tr>
                <td>{{ r.model }}</td>
                <td>{{ "%.4f"|format(r.accuracy) }}</td>
                <td>{{ "%.4f"|format(r.auc) }}</td>
            </tr>
            {% endfor %}
        </table>

        <div class="chart">
            <h2>ROC-AUC кривые</h2>
            <!-- ✅ Относительный путь: images/roc_auc.png -->
            <img src="{{ roc_auc_path }}" class="chart_img" alt="ROC-AUC Curve">
        </div>

        <p><em>Отчёт сгенерирован автоматически на основе тестовой выборки.</em></p>
    </body>
    </html>
    """

    template = Template(html_template)
    html_out = template.render(
        results=results,
        roc_auc_path=roc_auc_path,
        now=datetime.now().strftime("%d.%m.%Y %H:%M")
    )

    # ✅ Указываем base_url = REPORTS_DIR (родительский каталог отчёта)
    HTML(string=html_out, base_url=REPORTS_DIR.resolve()).write_pdf(target=filename)
    return filename
# app/services/reporting.py
"""
Модуль генерации PDF-отчётов

Модуль реализует:
- Генерацию PDF с объяснением решения модели (SHAP)
- Генерацию сравнительного отчёта моделей (с графиком ROC-AUC)
- Использование HTML + CSS + Jinja2 + WeasyPrint
- Поддержку кириллицы и русского языка

Основные функции:
- generate_explanation_pdf: отчёт по одному кредиту
- generate_model_comparison_pdf: отчёт по сравнению моделей

Автор: [Кочнева Арина]
Год: 2025
"""

from weasyprint import HTML
from jinja2 import Template
import os
from datetime import datetime
from pathlib import Path
import logging

# Импорт путей из централизованной конфигурации
from shared.config import IMAGES_DIR, REPORTS_DIR


logger = logging.getLogger(__name__)


def generate_explanation_pdf(
        data: dict,
        explanation: dict,
        filename="reports/explanation_report.pdf"
):
    """
    Генерирует PDF-отчёт с объяснением решения модели
    для одного заемщика.

    Отчёт включает:
        - Данные клиента
        - Решение (ОДОБРЕНО/ОТКАЗ)
        - Вероятность возврата
        - Текстовое объяснение (топ-5 признаков)
        - График SHAP waterfall

    Args:
        data (dict): Входные данные заемщика (из формы)
        explanation (dict): Результат функции explain_prediction
        filename (str or Path): Путь для сохранения PDF

    Returns:
        str: Абсолютный путь к сгенерированному PDF-файлу

    Raises:
        Exception: Если возникла ошибка при рендеринге или сохранении

    Примечания:
        - Используется Jinja2 для динамического формирования HTML
        - WeasyPrint корректно обрабатывает кириллицу
        - График SHAP предварительно сохраняется в images/
        - base_url нужен, чтобы WeasyPrint мог найти изображение

    Пример использования:
        >>> result = explain_prediction(request.model_dump())
        >>> pdf_path = generate_explanation_pdf(request.model_dump(), result)
        >>> print(f"Отчёт сохранён: {pdf_path}")
    """
    # Создаём путь к изображению (относительно REPORTS_DIR)
    image_path = "images/shap_waterfall.png"

    # HTML-шаблон с инлайн CSS
    html_template = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <style>
            body { 
                font-family: sans-serif; 
                padding: 2cm; 
                line-height: 1.6;
            }
            h1, h2 { 
                color: #2c3e50; 
                border-bottom: 1px solid #eee;
                padding-bottom: 8px;
            }
            .field { 
                margin: 8px 0; 
                font-size: 14px;
            }
            .decision { 
                background-color: #d4edda; 
                color: #155724; 
                padding: 12px; 
                border-radius: 5px; 
                font-weight: bold;
                margin: 15px 0;
                font-size: 16px;
            }
            .risk { color: #c0392b; }
            .safe { color: #27ae60; }
            .shap-img { 
                margin: 20px 0; 
                max-width: 100%; 
                border: 1px solid #ddd; 
                border-radius: 5px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 13px;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
            ul.explanation-list {
                padding-left: 20px;
                margin: 10px 0;
            }
            ul.explanation-list li {
                margin: 5px 0;
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
            <tr><td><strong>{{ k }}</strong></td><td>{{ v }}</td></tr>
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
        <div class="field">
            <strong>Вероятность возврата:</strong> 
            {{ "%.1f"|format(probability_repaid * 100) }}%
        </div>

        <h2>Объяснение решения</h2>
        <ul class="explanation-list">
        {% for line in explanation.summary %}
            <li>
                {{ line.replace('↑ риск', '⬆️ повышает риск') \
                       .replace('↓ риск', '⬇️ понижает риск') }}
            </li>
        {% endfor %}
        </ul>

        <h2>Визуализация вклада признаков</h2>
        <img src="{{ image_path }}" class="shap-img" alt="SHAP Waterfall Plot">
        <p><em>График показывает, как каждый признак повлиял на предсказание.</em></p>
    </body>
    </html>
    """

    # Рендеринг шаблона
    template = Template(html_template)
    html_out = template.render(
        data=data,
        explanation=explanation,
        decision="approve" if explanation["prediction"] == 0 else "reject",
        probability_repaid=explanation["probability_repaid"],
        image_path=image_path,
        now=datetime.now().strftime("%d.%m.%Y %H:%M")
    )

    # Создание директории
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    # Генерация PDF с указанием base_url (для корректной загрузки изображений)
    HTML(
        string=html_out,
        base_url=REPORTS_DIR.resolve()
    ).write_pdf(target=filename)

    # Возвращаем абсолютный путь
    return str(Path(filename).resolve())


def generate_model_comparison_pdf(
        results,
        roc_auc_path,
        filename="reports/model_comparison_report.pdf"
):
    """
    Генерирует PDF-отчёт с сравнением моделей машинного обучения.

    Отчёт включает:
        - Таблицу с метриками (accuracy, AUC)
        - График ROC-AUC кривых
        - Дату генерации

    Args:
        results (list of dict): Список словарей с метриками моделей
            Пример: [{
                "model": "RandomForest",
                "accuracy": 0.91,
                "auc": 0.93
            }, ...]
        roc_auc_path (str or Path): Путь к изображению ROC-AUC графика
        filename (str or Path): Имя выходного PDF-файла

    Returns:
        str: Абсолютный путь к сгенерированному PDF-файлу

    Raises:
        Exception: Если ошибка рендеринга или сохранения

    Примечания:
        - График должен быть предварительно сгенерирован
        - Используется тот же подход: HTML → WeasyPrint → PDF
        - Поддерживается русский язык и кириллица

    Пример использования:
        >>> roc_path = generate_roc_auc_plot(...)
        >>> pdf_path = generate_model_comparison_pdf(results, roc_path)
        >>> print(f"Отчёт сравнения: {pdf_path}")
    """
    # HTML-шаблон для сравнения
    html_template = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <style>
            body { 
                font-family: sans-serif; 
                padding: 2cm; 
                line-height: 1.6;
            }
            h1, h2 { 
                color: #2c3e50; 
                border-bottom: 1px solid #eee;
                padding-bottom: 8px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 14px;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
            .chart {
                text-align: center;
                margin: 30px 0;
            }
            .chart img {
                max-width: 100%;
                border: 1px solid #ddd;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .footer {
                margin-top: 50px;
                font-size: 0.9em;
                color: #777;
                text-align: center;
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
            <img src="{{ roc_auc_path }}" alt="ROC-AUC Curve" class="chart_img">
        </div>

        <div class="footer">
            <p>Отчёт сгенерирован автоматически на основе тестовой выборки.</p>
            <p>Кредитный скоринг — дипломный проект | 2025</p>
        </div>
    </body>
    </html>
    """

    # Рендеринг шаблона
    template = Template(html_template)
    html_out = template.render(
        results=results,
        roc_auc_path=roc_auc_path,
        now=datetime.now().strftime("%d.%m.%Y %H:%M")
    )

    # Создание директории
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    # Генерация PDF
    HTML(
        string=html_out,
        base_url=REPORTS_DIR.resolve()
    ).write_pdf(target=filename)

    # Возвращаем абсолютный путь
    return str(Path(filename).resolve())

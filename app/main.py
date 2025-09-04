# app/main.py
"""
Credit Scoring API — Основной модуль FastAPI

Модуль реализует RESTful API для кредитного скоринга с поддержкой:
- Прогнозирования риска дефолта
- Объяснения решений с SHAP
- Генерации PDF-отчётов
- Дообучения модели на обратной связи
- Сравнения моделей и визуализации

Архитектура:
- FastAPI: основа API
- Ансамблевая модель (RandomForest + XGBoost + CatBoost)
- SHAP: интерпретируемость
- WeasyPrint: генерация PDF
- JSONL: хранение фидбэков

Автор: [Ваше имя]
Год: 2025
"""

import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Импорт компонентов системы
from shared.auth import verify_credentials
from shared.data_processing import preprocess_data
from shared.config import DATA_SOURCE, HOST, PORT
from shared.models import LoanRequest, FeedbackRequest
from services.model_comparison import (
    compare_models, generate_roc_auc_plot
)
from services.reporting import (
    generate_model_comparison_pdf, generate_explanation_pdf
)
from services.model_training import train_ensemble_model
from app.services.retrain import retrain_model_from_feedback
from app.services.utils import explain_prediction, predict_loan_status


# --- 📝 Настройка логгирования ---
"""
Логирование используется для:
- Фиксации запуска API
- Отслеживания обучения и дообучения
- Регистрации ошибок и фидбэков
Файл: credit_scoring.log
"""
logging.basicConfig(
    filename='credit_scoring.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# --- 📥 Загрузка данных ---
"""
Данные загружаются при старте приложения.
Ожидается CSV-файл с историческими данными по кредитам.
Путь задаётся в shared/config.py
"""
data_path = DATA_SOURCE
try:
    df = pd.read_csv(data_path)
    logging.info(
        f"Данные загружены: {df.shape[0]} строк, "
        f"{df.shape[1]} колонок"
    )
except Exception as e:
    logging.critical(f"Не удалось загрузить данные: {e}")
    raise


# --- 🚀 Инициализация FastAPI ---
"""
FastAPI — современный фреймворк для создания API.
Поддерживает:
- Автоматическую документацию (Swagger/OpenAPI)
- Валидацию Pydantic
- CORS
- Авторизацию
"""
app = FastAPI(
    dependencies=[Depends(verify_credentials)],
    description='API кредитного скоринга',
    title='Credit Scoring API',
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# --- 🔐 Настройка CORS ---
"""
Разрешаем доступ со всех источников.
В production рекомендуется ограничить домены.
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# --- 📥 Хранение обратной связи ---
"""
feedback_data — временный буфер в памяти.
FEEDBACK_FILE — постоянное хранилище в формате JSONL 
(один JSON на строку).
"""
feedback_data = []
FEEDBACK_FILE = Path("data/feedback.jsonl")


# --- 🔄 Загрузка фидбэков при старте ---
def load_feedback():
    """
    Загружает сохранённые фидбэки из файла при запуске API.
    Используется для восстановления истории обратной связи
    после перезапуска.

    Примечание:
        - Формат: JSONL (один JSON-объект на строку)
        - Кодировка: UTF-8 (для поддержки кириллицы)
    """
    global feedback_data
    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        feedback_data.append(json.loads(line))
            logging.info(
                f"Загружено {len(feedback_data)} "
                f"записей из feedback.jsonl"
            )
        except Exception as e:
            logging.error(f"Ошибка при загрузке feedback: {e}")


# Выполняем при старте
load_feedback()


# --- 📡 Эндпоинты API ---

@app.get(
    path="/",
    dependencies=[Depends(verify_credentials)]
)
def read_root():
    """
    Корневой эндпоинт.

    Возвращает приветственное сообщение.
    Не требует тела запроса.

    Returns:
        dict: Приветственное сообщение
    """
    return {"message": "Добро пожаловать в Credit Scoring API"}


@app.post(
    path="/train-final",
    dependencies=[Depends(verify_credentials)]
)
def train_final_api():
    """
    Обучает ансамблевую модель на основе текущих данных.

    Этапы:
        1. Предобработка данных (OHE, feature engineering)
        2. Обучение VotingClassifier (RF + XGBoost + CatBoost)
        3. Сохранение модели, фичей и background_data

    Returns:
        dict: Результат обучения (модель, точность)
    """
    X, y = preprocess_data(df.copy())
    result = train_ensemble_model(X, y)
    logging.info(
        f"Ансамбль обучен. Точность: {result['accuracy']:.3f}"
    )
    return result


@app.post(
    path="/predict",
    dependencies=[Depends(verify_credentials)]
)
def predict_api(request: LoanRequest):
    """
    Выполняет прогноз статуса кредита.

    Args:
        request (LoanRequest): Данные заемщика

    Returns:
        dict: Прогноз, вероятности, решение
    """
    input_df = pd.DataFrame([request.model_dump()])
    result = predict_loan_status(input_df)
    return {
        "prediction": result["prediction"],
        "status": "repaid" if result["prediction"] == 0 else "default",
        "decision": "approve" if result["prediction"] == 0 else "reject",
        "probability_repaid": result["probability_repaid"],
        "probability_default": result["probability_default"]
    }


@app.post(
    path="/explain",
    dependencies=[Depends(verify_credentials)]
)
def explain_api(request: LoanRequest):
    """
    Генерирует объяснение решения с помощью SHAP.

    Использует универсальный Explainer для ансамблевой модели.

    Args:
        request (LoanRequest): Данные заемщика

    Returns:
        dict: Объяснение с SHAP-значениями и base_value
    """
    result = explain_prediction(request.model_dump())
    return result


@app.post(
    path="/report",
    dependencies=[Depends(verify_credentials)]
)
def generate_report(request: LoanRequest):
    """
    Генерирует PDF-отчёт с полным объяснением решения.

    Отчёт включает:
        - Данные заемщика
        - Решение и вероятности
        - Текстовое объяснение
        - График SHAP waterfall

    Args:
        request (LoanRequest): Данные заемщика

    Returns:
        dict: Путь к PDF-файлу
    """
    try:
        result = explain_prediction(request.model_dump())
        pdf_path = generate_explanation_pdf(
            request.model_dump(),
            result
        )
        logging.info(f"PDF-отчёт сгенерирован: {pdf_path}")
        return {"report_path": pdf_path}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при генерации отчёта: {str(e)}"
        )


@app.post(
    path='/feedback',
    dependencies=[Depends(verify_credentials)]
)
def feedback_api(request: FeedbackRequest):
    """
    Сохраняет обратную связь о реальном статусе кредита.

    Используется для последующего дообучения модели.

    Args:
        request (FeedbackRequest):
            Данные + predicted_status + actual_status

    Returns:
        dict: Статус сохранения
    """
    try:
        feedback_entry = request.model_dump()
        feedback_data.append(feedback_entry)

        FEEDBACK_FILE.parent.mkdir(exist_ok=True)
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    feedback_entry,
                    ensure_ascii=False
                ) + "\n"
            )

        logging.info(f"Сохранён фидбэк: {feedback_entry}")
        return {
            "status": "success",
            "message": "Обратная связь сохранена"
        }

    except Exception as e:
        logging.error(f"Ошибка при сохранении фидбэка: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при сохранении: {str(e)}"
        )


@app.post(
    path="/retrain",
    dependencies=[Depends(verify_credentials)]
)
def retrain_api():
    """
    Дообучает модель на основе собранных фидбэков.

    Процесс:
        1. Загрузка фидбэков
        2. Предобработка
        3. Дообучение ансамбля
        4. Сохранение

    Returns:
        dict: Результат дообучения
    """
    try:
        result = retrain_model_from_feedback()
        logging.info(
            f"Модель дообучена. Точность на фидбэках: "
            f"{result['accuracy_on_feedback']:.3f}"
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при дообучении: {str(e)}"
        )


@app.get(
    path="/compare",
    dependencies=[Depends(verify_credentials)]
)
def compare_models_api():
    """
    Сравнивает производительность моделей.

    Обучает несколько моделей (RF, XGBoost, CatBoost, Ensemble)
    и возвращает их точность.

    Returns:
        dict: Результаты сравнения
    """
    X, y = preprocess_data(df.copy())
    result = compare_models(X, y)
    return {"models": result["results"]}


@app.post(
    path="/generate-comparison-report",
    dependencies=[Depends(verify_credentials)]
)
def generate_comparison_report():
    """
    Генерирует PDF-отчёт с сравнением моделей.

    Включает:
        - Таблицу метрик
        - ROC-AUC график
        - Информацию о моделях

    Returns:
        dict: Путь к PDF-файлу
    """
    try:
        X, y = preprocess_data(df.copy())
        result = compare_models(X, y)

        roc_path = generate_roc_auc_plot(
            result["X_test"],
            result["y_test"],
            result["trained_models"]
        )

        pdf_path = generate_model_comparison_pdf(
            result["results"],
            roc_path
        )

        logging.info(
            f"Отчёт сравнения моделей сгенерирован: {pdf_path}"
        )
        return {"report_path": pdf_path}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при генерации отчёта: {str(e)}"
        )


# --- ▶️ Запуск приложения ---
if __name__ == "__main__":
    """
    Точка входа приложения.

    Запускает Uvicorn-сервер с FastAPI.
    Хост и порт задаются в shared/config.py
    """
    uvicorn.run(app, host=HOST, port=PORT)

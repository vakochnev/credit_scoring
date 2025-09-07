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
import os.path
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sqlalchemy.orm import Session

# Импорт компонентов системы
from shared.database import engine, Base, SessionLocal
from shared.auth import verify_credentials
from shared.data_processing import preprocess_data
from shared.config import DATA_SOURCE, HOST, PORT
from shared.models import (
    LoanRequest, FeedbackRequest, FeedbackDB
)
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
try:
    df = pd.read_csv(DATA_SOURCE)
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 📡 Эндпоинты API ---
@app.get(path="/")
def read_root():
    """
    Корневой эндпоинт.

    Возвращает приветственное сообщение.
    Не требует тела запроса.

    Returns:
        dict: Приветственное сообщение
    """
    return {"message": "Добро пожаловать в Credit Scoring API"}


@app.post(path="/train-final")
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


@app.post(path="/predict")
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


@app.post(path="/explain")
def explain_api(request: LoanRequest):
    """
    Генерирует объяснение решения с помощью SHAP.

    Использует универсальный Explainer для ансамблевой модели.

    Args:
        request (LoanRequest): Данные заемщика

    Returns:
        dict: Объяснение с SHAP-значениями и base_value
    """
    try:
        result = explain_prediction(request.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.post(path="/report")
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


@app.post(path='/feedback')
def feedback_api(
        request: FeedbackRequest,
        db: SessionLocal = Depends(get_db)
):
#def feedback_api(request: FeedbackRequest):
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
        feedback = FeedbackDB(**request.model_dump())
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return {"status": "success", "id": feedback.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения в БД: {str(e)}")


@app.post(path="/retrain")
def retrain_api(db: Session = Depends(get_db)):
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
        result = retrain_model_from_feedback(db)
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


@app.get(path="/compare")
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


@app.post(path="/generate-comparison-report")
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

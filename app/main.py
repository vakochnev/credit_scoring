from sklearn.model_selection import train_test_split

from app.services.utils import explain_prediction, predict_loan_status
from services.model_comparison import compare_models #, generate_comparison_plot
from services.reporting import generate_model_comparison_pdf

import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from shared.auth import verify_credentials
from shared.data_processing import (
    preprocess_data
)
from services.model_training import (
    train_ensemble_model
)
from services.utils import explain_prediction
from services.reporting import generate_explanation_pdf
from shared.config import DATA_SOURCE, HOST, PORT
from app.services.retrain import retrain_model_from_feedback
from shared.models import LoanRequest, FeedbackRequest  # ✅ Импортируем обе модели


# Настройка логгирования
logging.basicConfig(
    filename='credit_scoring.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Загрузка данных
data_path = DATA_SOURCE
df = pd.read_csv(data_path)

# Инициализация FastAPI
app = FastAPI(
    dependencies=[Depends(verify_credentials)],
    description='API кредитного скоринга',
    title='Credit Scoring API',
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 📦 Глобальный список фидбэков
feedback_data = []

# 📁 Путь к файлу с фидбэками
FEEDBACK_FILE = Path("data/feedback.jsonl")


# 🔁 Загрузка фидбэков при старте (если есть)
def load_feedback():
    global feedback_data
    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        feedback_data.append(json.loads(line))
            logging.info(f"Загружено {len(feedback_data)} записей из feedback.jsonl")
        except Exception as e:
            logging.error(f"Ошибка при загрузке feedback: {e}")

# Вызываем при старте
load_feedback()


@app.get(path="/", dependencies=[Depends(verify_credentials)])
def read_root():
    return {"message": "Добро пожаловать в Credit Scoring API"}


@app.post(path="/train-final", dependencies=[Depends(verify_credentials)])
def train_final_api():
    X, y = preprocess_data(df.copy())
    result = train_ensemble_model(X, y)
    return result


@app.post(path="/predict", dependencies=[Depends(verify_credentials)])
def predict_api(request: LoanRequest):
    input_df = pd.DataFrame([request.model_dump()])
    result = predict_loan_status(input_df)
    return {
        "prediction": result["prediction"],
        "status": "repaid" if result["prediction"] == 0 else "default",
        "decision": "approve" if result["prediction"] == 0 else "reject",
        "probability_repaid": result["probability_repaid"],
        "probability_default": result["probability_default"]
    }


@app.post(path="/explain", dependencies=[Depends(verify_credentials)])
def explain_api(request: LoanRequest):
    result = explain_prediction(request.model_dump())
    return result


@app.post(path="/report", dependencies=[Depends(verify_credentials)])
def generate_report(request: LoanRequest):
    try:
        result = explain_prediction(request.model_dump())
        pdf_path = generate_explanation_pdf(request.model_dump(), result)
        return {"report_path": pdf_path}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при генерации отчёта: {str(e)}"
        )


@app.post(path='/feedback', dependencies=[Depends(verify_credentials)])
def feedback_api(request: FeedbackRequest):
    """
    Принимает обратную связь о реальном статусе кредита.
    Сохраняет в список и в файл в формате JSONL.
    """
    try:
        # Конвертируем в словарь
        feedback_entry = request.model_dump()

        # Добавляем во внутренний список
        feedback_data.append(feedback_entry)

        # Сохраняем в файл (append mode)
        FEEDBACK_FILE.parent.mkdir(exist_ok=True)
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry, ensure_ascii=False) + "\n")

        logging.info(f"Сохранён фидбэк: {feedback_entry}")
        return {"status": "success", "message": "Обратная связь сохранена"}

    except Exception as e:
        logging.error(f"Ошибка при сохранении фидбэка: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при сохранении: {str(e)}"
        )


# ✅ Добавьте здесь:
@app.post(path="/retrain", dependencies=[Depends(verify_credentials)])
def retrain_api():
    """
    Переобучает модель на основе собранных фидбэков.
    """
    try:
        result = retrain_model_from_feedback()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при дообучении: {str(e)}"
        )


@app.get(path="/compare", dependencies=[Depends(verify_credentials)])
def compare_models_api():
    """
    Сравнивает модели: обучает, оценивает, возвращает результаты.
    """
    from shared.data_processing import preprocess_data
    from services.model_comparison import compare_models

    X, y = preprocess_data(df.copy())
    result = compare_models(X, y)
    return {"models": result["results"]}

@app.post(path="/generate-comparison-report", dependencies=[Depends(verify_credentials)])
def generate_comparison_report():
    """
    Генерирует PDF-отчёт с сравнением моделей и ROC-AUC графиком.
    """
    try:
        from shared.data_processing import preprocess_data
        from services.model_comparison import compare_models, generate_roc_auc_plot
        from services.reporting import generate_model_comparison_pdf

        X, y = preprocess_data(df.copy())
        result = compare_models(X, y)

        roc_path = generate_roc_auc_plot(
            result["X_test"],
            result["y_test"],
            result["trained_models"]
        )

        pdf_path = generate_model_comparison_pdf(result["results"], roc_path)
        return {"report_path": pdf_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации отчёта: {str(e)}")



if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
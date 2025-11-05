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
from datetime import datetime
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sqlalchemy.orm import Session

# Импорт компонентов системы
from shared.database import engine, Base, SessionLocal
from shared.auth import (
    get_current_user, require_role, create_access_token,
    create_refresh_token, verify_token, get_password_hash,
    verify_password
)
from shared.data_processing import preprocess_data
from shared.config import DATA_SOURCE, HOST, PORT
from shared.models import (
    LoanRequest, FeedbackRequest, FeedbackDB, User,
    LoginRequest as AuthLoginRequest, Token, TokenRefresh, UserInfo
)
from app.services.model_comparison import (
    compare_models, generate_roc_auc_plot
)
from app.services.reporting import (
    generate_model_comparison_pdf, generate_explanation_pdf
)
from app.services.model_training import train_ensemble_model
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
    description='API кредитного скоринга',
    title='Credit Scoring API',
    version="2.0.0",
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


# --- 🔐 Эндпоинты авторизации ---
@app.post("/login", response_model=Token)
def login(
    login_data: AuthLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Авторизация пользователя и выдача JWT токенов.

    Args:
        login_data (AuthLoginRequest): Логин и пароль
        db: Сессия БД

    Returns:
        Token: Access и refresh токены

    Raises:
        HTTPException: Если логин или пароль неверны
    """
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )
    
    # Обновление даты последнего входа
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Создание токенов
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "username": user.username}
    )
    
    logging.info(f"Пользователь {user.username} (роль: {user.role}) авторизован")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@app.post("/refresh", response_model=Token)
def refresh_token_endpoint(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Обновление access токена используя refresh токен.

    Args:
        token_data (TokenRefresh): Refresh токен
        db: Сессия БД

    Returns:
        Token: Новые access и refresh токены

    Raises:
        HTTPException: Если refresh токен невалиден
    """
    try:
        payload = verify_token(token_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный токен"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден или деактивирован"
            )
        
        # Создание новых токенов
        access_token = create_access_token(
            data={"sub": user.id, "username": user.username, "role": user.role}
        )
        refresh_token = create_refresh_token(
            data={"sub": user.id, "username": user.username}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Ошибка обновления токена: {str(e)}"
        )


@app.get("/me", response_model=UserInfo)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.

    Args:
        current_user: Текущий пользователь из токена

    Returns:
        UserInfo: Информация о пользователе
    """
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active
    )


@app.post(path="/train-final")
def train_final_api(
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Обучает ансамблевую модель на основе текущих данных.
    Требует роль: admin

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
        f"Ансамбль обучен пользователем {current_user.username}. "
        f"Точность: {result['accuracy']:.3f}"
    )
    return result


@app.post(path="/predict")
def predict_api(
    request: LoanRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Выполняет прогноз статуса кредита.
    Требует авторизацию: любая роль

    Args:
        request (LoanRequest): Данные заемщика
        current_user: Текущий пользователь

    Returns:
        dict: Прогноз, вероятности, решение
    """
    input_df = pd.DataFrame([request.model_dump()])
    result = predict_loan_status(input_df)
    logging.info(
        f"Прогноз выполнен пользователем {current_user.username} "
        f"(роль: {current_user.role})"
    )
    return {
        "prediction": result["prediction"],
        "status": "repaid" if result["prediction"] == 0 else "default",
        "decision": "approve" if result["prediction"] == 0 else "reject",
        "probability_repaid": result["probability_repaid"],
        "probability_default": result["probability_default"]
    }


@app.post(path="/explain")
def explain_api(
    request: LoanRequest,
    current_user: User = Depends(require_role(["analyst", "admin", "user"]))
):
    """
    Генерирует объяснение решения с помощью SHAP.
    Требует роль: analyst, admin, user

    Использует универсальный Explainer для ансамблевой модели.

    Args:
        request (LoanRequest): Данные заемщика
        current_user: Текущий пользователь

    Returns:
        dict: Объяснение с SHAP-значениями и base_value
    """
    try:
        result = explain_prediction(request.model_dump())
        logging.info(
            f"Объяснение сгенерировано пользователем {current_user.username}"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.post(path="/report")
def generate_report(
    request: LoanRequest,
    current_user: User = Depends(require_role(["analyst", "admin"]))
):
    """
    Генерирует PDF-отчёт с полным объяснением решения.
    Требует роль: analyst, admin

    Отчёт включает:
        - Данные заемщика
        - Решение и вероятности
        - Текстовое объяснение
        - График SHAP waterfall

    Args:
        request (LoanRequest): Данные заемщика
        current_user: Текущий пользователь

    Returns:
        dict: Путь к PDF-файлу
    """
    try:
        result = explain_prediction(request.model_dump())
        pdf_path = generate_explanation_pdf(
            request.model_dump(),
            result
        )
        logging.info(
            f"PDF-отчёт сгенерирован пользователем {current_user.username}: "
            f"{pdf_path}"
        )
        return {"report_path": pdf_path}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при генерации отчёта: {str(e)}"
        )


@app.post(path='/feedback')
def feedback_api(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Сохраняет обратную связь о реальном статусе кредита.
    Требует авторизацию: любая роль

    Используется для последующего дообучения модели.

    Args:
        request (FeedbackRequest): Данные + predicted_status + actual_status
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        dict: Статус сохранения
    """
    try:
        feedback = FeedbackDB(**request.model_dump())
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        logging.info(
            f"Фидбэк сохранён пользователем {current_user.username} "
            f"(ID: {feedback.id})"
        )
        return {"status": "success", "id": feedback.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка сохранения в БД: {str(e)}"
        )


@app.post(path="/retrain")
def retrain_api(
    current_user: User = Depends(require_role(["admin", "analyst"])),
    db: Session = Depends(get_db)
):
    """
    Дообучает модель на основе собранных фидбэков.
    Требует роль: admin, analyst

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
            f"Модель дообучена пользователем {current_user.username}. "
            f"Точность на фидбэках: {result['accuracy_on_feedback']:.3f}"
        )
        return result
    except ValueError as e:
        # Ошибки валидации данных (нет данных, недостаточно данных и т.д.)
        error_msg = str(e)
        if "Нет данных в таблице feedback" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недостаточно данных для дообучения. Сначала соберите обратную связь (feedback) через эндпоинт /feedback."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка валидации данных: {error_msg}"
        )
    except Exception as e:
        logging.error(f"Ошибка при дообучении модели: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при дообучении: {str(e)}"
        )


@app.get(path="/compare")
def compare_models_api(
    current_user: User = Depends(require_role(["analyst", "admin"]))
):
    """
    Сравнивает производительность моделей.
    Требует роль: analyst, admin

    Обучает несколько моделей (RF, XGBoost, CatBoost, Ensemble)
    и возвращает их точность.

    Returns:
        dict: Результаты сравнения
    """
    X, y = preprocess_data(df.copy())
    result = compare_models(X, y)
    logging.info(
        f"Сравнение моделей выполнено пользователем {current_user.username}"
    )
    return {"models": result["results"]}


@app.post(path="/generate-comparison-report")
def generate_comparison_report(
    current_user: User = Depends(require_role(["analyst", "admin"]))
):
    """
    Генерирует PDF-отчёт с сравнением моделей.
    Требует роль: analyst, admin

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
            f"Отчёт сравнения моделей сгенерирован пользователем "
            f"{current_user.username}: {pdf_path}"
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

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
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

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


# --- 📝 Настройка структурированного логирования ---
"""
Структурированное логирование в JSON формате для:
- Улучшенной обработки логов системами мониторинга
- Структурированного формата для анализа
- Логирования ошибок в файл с детальной информацией
"""
from shared.logging_config import setup_logging, get_logger
from shared.config import ROOT_DIR, LOGS_DIR

# Настройка логирования
# Имя файла лога можно настроить через .env (по умолчанию credit_scoring.log)
LOG_FILE_NAME = os.getenv("LOG_FILE_NAME", "credit_scoring.log")
logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=str(LOGS_DIR / LOG_FILE_NAME),
    use_json=os.getenv("USE_JSON_LOGS", "true").lower() == "true",
    console_output=True
)

# Метрики производительности
app_metrics: Dict[str, Any] = {
    "start_time": datetime.utcnow(),
    "requests_total": 0,
    "requests_by_endpoint": {},
    "errors_total": 0,
    "errors_by_endpoint": {},
    "response_times": []
}


# --- 📥 Загрузка данных ---
"""
Данные загружаются при старте приложения.
Ожидается CSV-файл с историческими данными по кредитам.
Путь задаётся в shared/config.py
"""
try:
    df = pd.read_csv(DATA_SOURCE)
    logger.info(
        "Данные загружены",
        extra={
            "rows": df.shape[0],
            "columns": df.shape[1],
            "data_source": str(DATA_SOURCE)
        }
    )
except Exception as e:
    logger.critical(
        "Не удалось загрузить данные",
        extra={"error": str(e), "data_source": str(DATA_SOURCE)},
        exc_info=True
    )
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events для FastAPI"""
    # Startup
    logger.info("Приложение запускается", extra={"version": "2.0.0"})
    yield
    # Shutdown
    logger.info("Приложение останавливается")


app = FastAPI(
    title='Credit Scoring API',
    description="""
    ## API кредитного скоринга с ансамблевыми моделями
    
    Система предоставляет RESTful API для:
    - 📈 Прогнозирования риска дефолта заемщика
    - 📊 Объяснения решений с помощью SHAP
    - 📄 Генерации PDF-отчётов
    - 🔁 Дообучения модели на обратной связи
    - 🔐 JWT авторизации с ролями (admin, analyst, user)
    
    ### Авторизация
    
    Для доступа к защищенным endpoints необходимо:
    1. Получить токены через `/login`
    2. Использовать `access_token` в заголовке: `Authorization: Bearer <token>`
    3. Обновить токен через `/refresh` при истечении
    
    ### Роли
    
    - **admin**: Полный доступ ко всем endpoints
    - **analyst**: Доступ к прогнозам, отчётам, фидбэкам
    - **user**: Базовый доступ к прогнозам
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "Credit Scoring API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Локальный сервер разработки"
        },
        {
            "url": "https://api.example.com",
            "description": "Production сервер"
        }
    ]
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


# --- 📊 Middleware для метрик и логирования ---
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """
    Middleware для сбора метрик производительности и логирования запросов.
    
    Функции:
    - Собирает статистику по запросам (общее количество, по эндпоинтам)
    - Измеряет время обработки запросов
    - Логирует все HTTP запросы в структурированном формате
    - Отслеживает ошибки
    - Добавляет заголовок X-Process-Time с временем обработки
    
    Args:
        request: HTTP запрос
        call_next: Следующий обработчик в цепочке middleware
    
    Returns:
        Response: HTTP ответ с добавленным заголовком X-Process-Time
    """
    start_time = time.time()
    
    # Собираем метрики: увеличиваем счетчик общего количества запросов
    app_metrics["requests_total"] += 1
    # Формируем ключ эндпоинта (метод + путь)
    endpoint = f"{request.method} {request.url.path}"
    # Увеличиваем счетчик запросов для данного эндпоинта
    app_metrics["requests_by_endpoint"][endpoint] = \
        app_metrics["requests_by_endpoint"].get(endpoint, 0) + 1
    
    try:
        # Выполняем следующий обработчик в цепочке
        response = await call_next(request)
        # Вычисляем время обработки запроса
        process_time = time.time() - start_time
        
        # Логируем успешный запрос в структурированном формате
        logger.info(
            "HTTP запрос обработан",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": round(process_time, 3),
                "client_ip": request.client.host if request.client else None
            }
        )
        
        # Сохраняем время ответа для статистики (ограничиваем до 1000 последних)
        app_metrics["response_times"].append(process_time)
        if len(app_metrics["response_times"]) > 1000:
            app_metrics["response_times"] = app_metrics["response_times"][-1000:]
        
        # Добавляем заголовок с временем обработки для клиента
        response.headers["X-Process-Time"] = str(round(process_time, 3))
        
        return response
    except Exception as e:
        # Обработка ошибок: логируем и увеличиваем счетчики ошибок
        process_time = time.time() - start_time
        app_metrics["errors_total"] += 1
        app_metrics["errors_by_endpoint"][endpoint] = \
            app_metrics["errors_by_endpoint"].get(endpoint, 0) + 1
        
        # Логируем ошибку с полным traceback
        logger.error(
            "Ошибка при обработке запроса",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "process_time": round(process_time, 3)
            },
            exc_info=True
        )
        raise


# --- 📥 Хранение обратной связи ---

def get_db():
    """
    Dependency для получения сессии базы данных.
    
    Используется FastAPI Depends для автоматического управления жизненным циклом
    сессии БД. Гарантирует закрытие сессии после завершения запроса.
    
    Yields:
        Session: SQLAlchemy сессия базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # Закрываем сессию в любом случае (даже при ошибке)
        db.close()


# --- 📡 Эндпоинты API ---
@app.get(path="/", tags=["Общие"])
def read_root():
    """
    Корневой эндпоинт.

    Возвращает приветственное сообщение и базовую информацию об API.
    Не требует авторизации.

    Returns:
        dict: Приветственное сообщение и информация об API
    """
    return {
        "message": "Добро пожаловать в Credit Scoring API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "status": "operational"
    }


# --- 🏥 Health Check Endpoints ---
@app.get("/health", tags=["Мониторинг"])
def health_check():
    """
    Базовый health check endpoint.
    
    Используется для проверки доступности API (например, для load balancer,
    мониторинга, Docker healthcheck).
    Не требует авторизации.
    
    Returns:
        dict: Статус здоровья API с временем работы
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }


@app.get("/health/detailed", tags=["Мониторинг"])
def detailed_health_check(db: Session = Depends(get_db)):
    """
    Расширенный health check с проверкой всех компонентов системы.
    
    Проверяет:
    - Доступность базы данных (подключение и запрос)
    - Наличие обученных моделей (ensemble_model.pkl, feature_names.pkl, background_data.pkl)
    - Доступность файловой системы (директории data, models, reports)
    - Наличие исходных данных (credit_risk_dataset.csv)
    
    Не требует авторизации (для мониторинга).
    
    Args:
        db: Сессия базы данных
    
    Returns:
        dict: Детальный статус всех компонентов системы
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "checks": {}
    }
    
    # Проверка базы данных
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "База данных доступна"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Ошибка БД: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Проверка моделей
    try:
        from shared.config import ENSEMBLE_MODEL_PATH, FEATURE_NAMES_PATH
        model_exists = ENSEMBLE_MODEL_PATH.exists()
        features_exists = FEATURE_NAMES_PATH.exists()
        
        health_status["checks"]["models"] = {
            "status": "healthy" if (model_exists and features_exists) else "unhealthy",
            "ensemble_model": model_exists,
            "feature_names": features_exists,
            "message": "Модели найдены" if (model_exists and features_exists) else "Модели не найдены"
        }
        
        if not (model_exists and features_exists):
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["models"] = {
            "status": "unhealthy",
            "message": f"Ошибка проверки моделей: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Проверка файловой системы
    try:
        from shared.config import DATA_DIR, MODELS_DIR, REPORTS_DIR
        dirs_ok = all(d.exists() and d.is_dir() for d in [DATA_DIR, MODELS_DIR, REPORTS_DIR])
        
        health_status["checks"]["filesystem"] = {
            "status": "healthy" if dirs_ok else "unhealthy",
            "directories": {
                "data": DATA_DIR.exists(),
                "models": MODELS_DIR.exists(),
                "reports": REPORTS_DIR.exists()
            },
            "message": "Директории доступны" if dirs_ok else "Некоторые директории недоступны"
        }
        
        if not dirs_ok:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["filesystem"] = {
            "status": "unhealthy",
            "message": f"Ошибка проверки файловой системы: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Проверка данных
    try:
        data_exists = df is not None and not df.empty
        health_status["checks"]["data"] = {
            "status": "healthy" if data_exists else "unhealthy",
            "rows": len(df) if data_exists else 0,
            "columns": len(df.columns) if data_exists else 0,
            "message": "Данные загружены" if data_exists else "Данные не загружены"
        }
        
        if not data_exists:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["data"] = {
            "status": "unhealthy",
            "message": f"Ошибка проверки данных: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/metrics", tags=["Мониторинг"])
def get_metrics(current_user: User = Depends(require_role(["admin"]))):
    """
    Получение метрик производительности приложения.
    
    Возвращает статистику:
    - Общее количество запросов
    - Количество запросов по эндпоинтам
    - Количество ошибок
    - Среднее время ответа
    - Время работы приложения
    
    Требует роль: admin
    
    Args:
        current_user: Текущий пользователь (должен быть admin)
    
    Returns:
        dict: Метрики производительности
    """
    avg_response_time = (
        sum(app_metrics["response_times"]) / len(app_metrics["response_times"])
        if app_metrics["response_times"] else 0
    )
    
    uptime = (datetime.utcnow() - app_metrics["start_time"]).total_seconds()
    
    return {
        "uptime_seconds": round(uptime, 2),
        "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
        "requests_total": app_metrics["requests_total"],
        "requests_by_endpoint": app_metrics["requests_by_endpoint"],
        "errors_total": app_metrics["errors_total"],
        "errors_by_endpoint": app_metrics["errors_by_endpoint"],
        "response_time_avg": round(avg_response_time, 3),
        "response_time_min": round(min(app_metrics["response_times"]), 3) if app_metrics["response_times"] else 0,
        "response_time_max": round(max(app_metrics["response_times"]), 3) if app_metrics["response_times"] else 0,
        "timestamp": datetime.utcnow().isoformat()
    }


# --- 🔐 Эндпоинты авторизации ---
@app.post("/login", response_model=Token, tags=["Авторизация"])
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
    
    logger.info(
        "Пользователь авторизован",
        extra={"username": user.username, "role": user.role, "user_id": user.id}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@app.post("/refresh", response_model=Token, tags=["Авторизация"])
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


@app.get("/me", response_model=UserInfo, tags=["Авторизация"])
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


@app.post(path="/train-final", tags=["ML Модели"])
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
    logger.info(
        "Ансамбль обучен",
        extra={
            "username": current_user.username,
            "user_id": current_user.id,
            "accuracy": result['accuracy']
        }
    )
    return result


@app.post(path="/predict", tags=["Прогнозирование"])
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
    logger.info(
        "Прогноз выполнен",
        extra={
            "username": current_user.username,
            "user_id": current_user.id,
            "role": current_user.role,
            "prediction": result["prediction"]
        }
    )
    return {
        "prediction": result["prediction"],
        "status": "repaid" if result["prediction"] == 0 else "default",
        "decision": "approve" if result["prediction"] == 0 else "reject",
        "probability_repaid": result["probability_repaid"],
        "probability_default": result["probability_default"]
    }


@app.post(path="/explain", tags=["Прогнозирование"])
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
        logger.info(
            "Объяснение сгенерировано",
            extra={
                "username": current_user.username,
                "user_id": current_user.id
            }
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.post(path="/report", tags=["Отчёты"])
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
        
        # Используем абсолютный путь для файла отчёта
        from shared.config import REPORTS_DIR
        report_filename = str(REPORTS_DIR / "explanation_report.pdf")
        
        pdf_path = generate_explanation_pdf(
            request.model_dump(),
            result,
            filename=report_filename
        )
        logger.info(
            "PDF-отчёт сгенерирован",
            extra={
                "username": current_user.username,
                "user_id": current_user.id,
                "pdf_path": pdf_path
            }
        )
        return {"report_path": pdf_path}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при генерации отчёта: {str(e)}"
        )


@app.post(path='/feedback', tags=["Обратная связь"])
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
        logger.info(
            "Фидбэк сохранён",
            extra={
                "username": current_user.username,
                "user_id": current_user.id,
                "feedback_id": feedback.id
            }
        )
        return {"status": "success", "id": feedback.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка сохранения в БД: {str(e)}"
        )


@app.get(path='/feedback', tags=["Обратная связь"])
def get_feedback_list(
    current_user: User = Depends(require_role(["admin", "analyst"])),
    db: Session = Depends(get_db)
):
    """
    Получает список всех обратных связей (feedback).
    Требует роль: admin, analyst

    Args:
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        list: Список всех feedback записей
    """
    try:
        from sqlalchemy import select
        stmt = select(FeedbackDB)
        result = db.execute(stmt)
        rows = result.scalars().all()
        
        feedback_list = [{
            "id": fb.id,
            "person_age": fb.person_age,
            "person_income": fb.person_income,
            "person_home_ownership": fb.person_home_ownership,
            "person_emp_length": fb.person_emp_length,
            "loan_intent": fb.loan_intent,
            "loan_grade": fb.loan_grade,
            "loan_amnt": fb.loan_amnt,
            "loan_int_rate": fb.loan_int_rate,
            "loan_percent_income": fb.loan_percent_income,
            "cb_person_default_on_file": fb.cb_person_default_on_file,
            "cb_person_cred_hist_length": fb.cb_person_cred_hist_length,
            "predicted_status": fb.predicted_status,
            "actual_status": fb.actual_status,
            "probability_repaid": fb.probability_repaid,
            "probability_default": fb.probability_default,
            "created_at": fb.created_at.isoformat() if fb.created_at else None
        } for fb in rows]
        
        logger.info(
            "Список feedback получен",
            extra={
                "username": current_user.username,
                "user_id": current_user.id,
                "count": len(feedback_list)
            }
        )
        
        return {"feedback": feedback_list, "count": len(feedback_list)}
    except Exception as e:
        logger.error(
            "Ошибка при получении списка feedback",
            extra={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении данных: {str(e)}"
        )


@app.post(path="/retrain", tags=["ML Модели"])
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
        logger.info(
            "Модель дообучена",
            extra={
                "username": current_user.username,
                "user_id": current_user.id,
                "accuracy_on_feedback": result['accuracy_on_feedback']
            }
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
        logger.error(
            "Ошибка при дообучении модели",
            extra={
                "username": current_user.username,
                "user_id": current_user.id,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при дообучении: {str(e)}"
        )


@app.get(path="/compare", tags=["ML Модели"])
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
    logger.info(
        "Сравнение моделей выполнено",
        extra={
            "username": current_user.username,
            "user_id": current_user.id
        }
    )
    return {"models": result["results"]}


@app.post(path="/generate-comparison-report", tags=["Отчёты"])
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

        # Используем абсолютный путь для файла отчёта
        from shared.config import REPORTS_DIR
        report_filename = str(REPORTS_DIR / "model_comparison_report.pdf")
        
        pdf_path = generate_model_comparison_pdf(
            result["results"],
            roc_path,
            filename=report_filename
        )

        logger.info(
            "Отчёт сравнения моделей сгенерирован",
            extra={
                "username": current_user.username,
                "user_id": current_user.id,
                "pdf_path": pdf_path
            }
        )
        return {"report_path": pdf_path}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при генерации отчёта: {str(e)}"
        )


@app.get("/download/{filename}", tags=["Отчёты"])
def download_file(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Скачивание сгенерированных отчётов.
    
    Поддерживаемые файлы:
    - explanation_report.pdf
    - model_comparison_report.pdf
    
    Требует авторизацию: любая роль
    
    Args:
        filename: Имя файла для скачивания
        current_user: Текущий пользователь
    
    Returns:
        FileResponse: Файл PDF
    
    Raises:
        HTTPException: Если файл не найден
    """
    from shared.config import REPORTS_DIR
    
    # Безопасность: проверяем, что файл находится в директории reports
    allowed_files = ["explanation_report.pdf", "model_comparison_report.pdf"]
    
    if filename not in allowed_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимое имя файла. Разрешены: {', '.join(allowed_files)}"
        )
    
    file_path = REPORTS_DIR / filename
    
    # Логируем путь для отладки
    logger.debug(
        "Попытка скачать файл",
        extra={
            "file_name": filename,  # Переименовано из filename, чтобы избежать конфликта с LogRecord.filename
            "file_path": str(file_path),
            "reports_dir": str(REPORTS_DIR),
            "file_exists": file_path.exists()
        }
    )
    
    if not file_path.exists():
        # Проверяем, возможно файл есть в другой директории
        possible_paths = [
            file_path,
            Path(filename),
            REPORTS_DIR / Path(filename).name,
            Path(filename).resolve(),  # Абсолютный путь от filename
            REPORTS_DIR / filename,  # Если filename уже содержит только имя файла
        ]
        
        # Проверяем все возможные пути
        found_path = None
        for possible_path in possible_paths:
            try:
                if possible_path.exists():
                    found_path = possible_path
                    logger.info(
                        "Файл найден по альтернативному пути",
                        extra={"file_path": str(found_path), "original_path": str(file_path)}
                    )
                    break
            except Exception as e:
                logger.debug(f"Ошибка при проверке пути {possible_path}: {e}")
        
        if found_path:
            file_path = found_path
        else:
            # Логируем все проверенные пути для отладки
            logger.error(
                "Файл не найден",
                extra={
                    "file_name": filename,
                    "expected_path": str(file_path),
                    "reports_dir": str(REPORTS_DIR),
                    "reports_dir_exists": REPORTS_DIR.exists(),
                    "files_in_reports": list(REPORTS_DIR.glob("*.pdf")) if REPORTS_DIR.exists() else []
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Файл {filename} не найден в {REPORTS_DIR}. Убедитесь, что отчёт был сгенерирован. Доступные файлы: {list(REPORTS_DIR.glob('*.pdf')) if REPORTS_DIR.exists() else 'директория не существует'}"
            )
    
    logger.info(
        "Файл скачан",
        extra={
            "username": current_user.username,
            "user_id": current_user.id,
            "file_name": filename  # Переименовано из filename, чтобы избежать конфликта с LogRecord.filename
        }
    )
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/pdf"
    )


# --- ▶️ Запуск приложения ---
if __name__ == "__main__":
    """
    Точка входа приложения.

    Запускает Uvicorn-сервер с FastAPI.
    Хост и порт задаются в shared/config.py
    """
    uvicorn.run(app, host=HOST, port=PORT)

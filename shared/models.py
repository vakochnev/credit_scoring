# shared/models.py
"""
Модели данных для API кредитного скоринга

Модуль содержит:
- Pydantic-модели для валидации входных данных (LoanRequest, FeedbackRequest)
- ORM-модель SQLAlchemy для хранения пользователей (User)

Используется в:
- FastAPI: валидация запросов
- SQLAlchemy: работа с базой данных
- Streamlit: типизация данных

Автор: [Кочнева Арина]
Год: 2025
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


Base = declarative_base()


# --- 📥 Pydantic-модель: LoanRequest ---
class LoanRequest(BaseModel):
    """
    Модель для валидации входных данных заемщика.

    Используется в эндпоинтах:
        - /predict
        - /explain
        - /report

    Поля соответствуют признакам из датасета credit_risk_dataset.csv.

    Attributes:
        person_age (int): Возраст заемщика (18–100)
        person_income (int): Годовой доход (в рублях)
        person_home_ownership (str): Тип собственности ['RENT', 'OWN', 'MORTGAGE', 'OTHER']
        person_emp_length (float): Стаж работы в годах (0.0–50.0)
        loan_intent (str): Цель кредита ['DEBTCONSOLIDATION', 'EDUCATION', 'HOMEIMPROVEMENT', 'MEDICAL', 'PERSONAL', 'VENTURE']
        loan_grade (str): Кредитный рейтинг ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        loan_amnt (int): Сумма кредита (1000–100000)
        loan_int_rate (float): Процентная ставка (0.0–100.0)
        loan_percent_income (float): Доля дохода, идущая на погашение (0.0–1.0)
        cb_person_default_on_file (str): Был ли дефолт ['Y', 'N']
        cb_person_cred_hist_length (int): Длина кредитной истории (0–50 лет)

    Пример использования:
        >>> data = {
        ...     "person_age": 35,
        ...     "person_income": 75000,
        ...     "person_home_ownership": "RENT",
        ...     ...
        ... }
        >>> request = LoanRequest(**data)

    Валидация:
        - Все поля обязательные
        - Типы данных строго определены
        - Нет значений по умолчанию (все должны быть переданы)

    Примечания:
        - Используется Pydantic V2 (model_dump() вместо dict())
        - Автоматически проверяет типы и наличие полей
    """
    person_age: int
    person_income: int
    person_home_ownership: str
    person_emp_length: float
    loan_intent: str
    loan_grade: str
    loan_amnt: int
    loan_int_rate: float
    loan_percent_income: float
    cb_person_default_on_file: str
    cb_person_cred_hist_length: int


# --- 🔐 ORM-модель: User (для аутентификации) ---
class User(Base):
    """
    ORM-модель пользователя для хранения учётных данных.

    Используется SQLAlchemy для работы с базой данных.
    Предназначена для хранения логинов, хешей паролей и ролей.

    Атрибуты:
        id (int): Первичный ключ
        username (str): Логин (уникальный)
        password_hash (str): Хеш пароля (не пароль в открытом виде!)
        role (str): Роль пользователя (admin, analyst, user)
        is_active (bool): Активен ли пользователь
        created_at (DateTime): Дата создания
        last_login (DateTime): Дата последнего входа

    Роли:
        - admin: полный доступ ко всем функциям
        - analyst: доступ к прогнозированию, отчётам, просмотру фидбэков
        - user: только базовый доступ к прогнозированию

    Пример:
        user = User(
            username="admin",
            password_hash="sha256:...",
            role="admin",
            is_active=True
        )

    Примечания:
        - Таблица: "users"
        - Индекс на username для ускорения поиска
        - Не хранит пароли в открытом виде
        - Поддержка ролей для разграничения доступа
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="user", nullable=False)  # admin, analyst, user
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


# --- 🔹 ORM-модель: Feedback (для хранения в БД) ---
class FeedbackDB(Base):
    """
    ORM-модель для хранения обратной связи в базе данных.

    Используется SQLAlchemy для сохранения фидбэков с метаданными.
    """
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    person_age = Column(Integer)
    person_income = Column(Integer)
    person_home_ownership = Column(String)
    person_emp_length = Column(Float)
    loan_intent = Column(String)
    loan_grade = Column(String)
    loan_amnt = Column(Integer)
    loan_int_rate = Column(Float)
    loan_percent_income = Column(Float)
    cb_person_default_on_file = Column(String)
    cb_person_cred_hist_length = Column(Integer)

    predicted_status = Column(Integer)  # 0 — repaid, 1 — default
    actual_status = Column(Integer)     # 0 — repaid, 1 — default

    probability_repaid = Column(Float)
    probability_default = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# --- 🔄 Pydantic-модель: FeedbackRequest ---
class FeedbackRequest(LoanRequest):
    """
    Модель для обратной связи о реальном статусе кредита.

    Расширяет LoanRequest, добавляя поля:
        - predicted_status: что предсказала модель
        - actual_status: что произошло на самом деле
        - probability_repaid: вероятность возврата кредита
        - probability_default: вероятность дефолта

    Используется в эндпоинте /feedback для дообучения модели.

    Attributes:
        predicted_status (int): Предсказание модели (0 — repaid, 1 — default)
        actual_status (int): Реальный статус (0 — repaid, 1 — default)
        probability_repaid (float): Вероятность возврата кредита (0.0-1.0)
        probability_default (float): Вероятность дефолта (0.0-1.0)

    Пример:
        >>> feedback = FeedbackRequest(
        ...     person_age=35,
        ...     person_income=75000,
        ...     ...
        ...     predicted_status=0,
        ...     actual_status=1,
        ...     probability_repaid=0.92,
        ...     probability_default=0.08
        ... )

    Логика:
        - Если actual_status != predicted_status — модель ошиблась
        - Эти данные используются для дообучения (retrain)

    Примечания:
        - Целочисленные значения используются для совместимости с ML
        - repaid = 0, default = 1 — соответствует целевой переменной loan_status
        - Вероятности хранятся для анализа качества предсказаний
    """
    predicted_status: int  # 0 — repaid, 1 — default
    actual_status: int     # 0 — repaid, 1 — default
    probability_repaid: Optional[float] = None  # Вероятность возврата
    probability_default: Optional[float] = None  # Вероятность дефолта


# --- 🔐 Pydantic-модели для авторизации ---
class LoginRequest(BaseModel):
    """
    Модель для запроса логина.

    Attributes:
        username (str): Логин пользователя
        password (str): Пароль пользователя
    """
    username: str
    password: str


class Token(BaseModel):
    """
    Модель JWT токена.

    Attributes:
        access_token (str): Access JWT токен
        refresh_token (str): Refresh JWT токен
        token_type (str): Тип токена (обычно "bearer")
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """
    Модель для обновления токена.

    Attributes:
        refresh_token (str): Refresh JWT токен
    """
    refresh_token: str


class TokenData(BaseModel):
    """
    Данные из JWT токена.

    Attributes:
        user_id (Optional[int]): ID пользователя
        username (Optional[str]): Логин пользователя
        role (Optional[str]): Роль пользователя
    """
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None


class UserInfo(BaseModel):
    """
    Информация о пользователе для ответа API.

    Attributes:
        id (int): ID пользователя
        username (str): Логин
        role (str): Роль
        is_active (bool): Активен ли пользователь
    """
    id: int
    username: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

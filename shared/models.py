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

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel
from typing import List, Optional
from .database import Base


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
    Предназначена для хранения логинов и хешей паролей.

    Атрибуты:
        id (int): Первичный ключ
        username (str): Логин (уникальный)
        password_hash (str): Хеш пароля (не пароль в открытом виде!)

    Пример:
        user = User(username="admin", password_hash="sha256:...")

    Примечания:
        - Таблица: "users"
        - Индекс на username для ускорения поиска
        - Не хранит пароли в открытом виде
        - Может быть расширена для ролей (admin, analyst)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)


# --- 🔄 Pydantic-модель: FeedbackRequest ---
class FeedbackRequest(LoanRequest):
    """
    Модель для обратной связи о реальном статусе кредита.

    Расширяет LoanRequest, добавляя два поля:
        - predicted_status: что предсказала модель
        - actual_status: что произошло на самом деле

    Используется в эндпоинте /feedback для дообучения модели.

    Attributes:
        predicted_status (int): Предсказание модели (0 — repaid, 1 — default)
        actual_status (int): Реальный статус (0 — repaid, 1 — default)

    Пример:
        >>> feedback = FeedbackRequest(
        ...     person_age=35,
        ...     person_income=75000,
        ...     ...
        ...     predicted_status=0,
        ...     actual_status=1
        ... )

    Логика:
        - Если actual_status != predicted_status — модель ошиблась
        - Эти данные используются для дообучения (retrain)

    Примечания:
        - Целочисленные значения используются для совместимости с ML
        - repaid = 0, default = 1 — соответствует целевой переменной loan_status
        - Может быть расширена для хранения даты, комментариев и т.д.
    """
    predicted_status: int  # 0 — repaid, 1 — default
    actual_status: int     # 0 — repaid, 1 — default

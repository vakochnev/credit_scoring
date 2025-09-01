from sqlalchemy import Column, Integer, String
from pydantic import BaseModel
from typing import List

from .database import Base


class LoanRequest(BaseModel):
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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)


class FeedbackRequest(LoanRequest):
    """
    Модель для обратной связи.
    Расширяет LoanRequest, добавляя поля predicted_status и actual_status.
    """
    predicted_status: int  # 0 — repaid, 1 — default
    actual_status: int     # 0 — repaid, 1 — default
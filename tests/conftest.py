# tests/conftest.py
"""
Конфигурация pytest и фикстуры для тестов
"""

import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

# Импорт компонентов системы
from shared.database import Base as DBBase
from shared.models import Base as ModelsBase, User, FeedbackDB
from shared.auth import get_password_hash, create_access_token
from app.main import app, get_db as app_get_db


# --- Фикстуры для базы данных ---
@pytest.fixture(scope="function")
def db_session():
    """
    Фикстура для создания тестовой сессии БД.
    Использует временную SQLite базу данных в памяти.
    Каждый тест получает свою изолированную БД.
    """
    # Создаём временную БД в памяти для каждого теста
    # Используем уникальный URL для каждого теста, чтобы избежать конфликтов
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Создаём все таблицы перед использованием
    # На всякий случай сбрасываем существующие таблицы
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS feedback")
        conn.exec_driver_sql("DROP TABLE IF EXISTS users")
    # Создаём таблицы по метаданным моделей
    ModelsBase.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Создаём сессию
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        # Очищаем таблицы после использования
        ModelsBase.metadata.drop_all(bind=engine)
        engine.dispose()


# --- Переопределение зависимости get_db приложения на тестовую сессию ---
@pytest.fixture(autouse=True)
def override_get_db(db_session):
    """
    Автоматически переопределяет зависимость get_db в FastAPI приложении,
    чтобы использовать тестовую in-memory БД во всех тестах.
    Также переопределяет get_db в shared.auth для get_current_user.
    """
    def _get_db():
        try:
            yield db_session
        finally:
            pass

    # Переопределяем get_db в app/main.py
    app.dependency_overrides[app_get_db] = _get_db
    
    # Переопределяем get_db в shared.auth для get_current_user
    from shared import auth
    original_get_db = auth.get_db
    
    def test_get_db():
        """Тестовая версия get_db для shared.auth"""
        try:
            yield db_session
        finally:
            pass
    
    # Переопределяем функцию get_db в модуле
    auth.get_db = test_get_db
    
    # Также переопределяем через dependency_overrides для FastAPI
    # Это нужно для того, чтобы FastAPI использовал переопределенную версию
    app.dependency_overrides[auth.get_db] = _get_db
    
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        # Восстанавливаем оригинальный get_db
        auth.get_db = original_get_db
        # Очищаем заголовки клиентов
        if hasattr(app, 'test_clients'):
            for client in app.test_clients:
                if hasattr(client, 'headers'):
                    client.headers.clear()


@pytest.fixture(scope="function")
def test_user(db_session):
    """
    Фикстура для создания тестового пользователя.
    Создаётся первым, чтобы гарантировать правильный порядок ID.
    """
    # Убеждаемся, что таблица пуста перед созданием
    db_session.query(User).delete()
    db_session.commit()
    
    user = User(
        username="testuser",
        password_hash=get_password_hash("testpass123"),
        role="user",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin(db_session, test_user):
    """
    Фикстура для создания тестового администратора.
    Зависит от test_user, чтобы гарантировать правильный порядок создания.
    """
    # Проверяем, не существует ли уже admin
    existing_admin = db_session.query(User).filter(User.username == "admin").first()
    if existing_admin:
        db_session.refresh(existing_admin)
        return existing_admin
    
    admin = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        role="admin",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def test_analyst(db_session, test_user):
    """
    Фикстура для создания тестового аналитика.
    Зависит от test_user, чтобы гарантировать правильный порядок создания.
    """
    # Проверяем, не существует ли уже analyst
    existing_analyst = db_session.query(User).filter(User.username == "analyst").first()
    if existing_analyst:
        db_session.refresh(existing_analyst)
        return existing_analyst
    
    analyst = User(
        username="analyst",
        password_hash=get_password_hash("analyst123"),
        role="analyst",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(analyst)
    db_session.commit()
    db_session.refresh(analyst)
    return analyst


# --- Фикстуры для JWT токенов ---
@pytest.fixture
def access_token(test_user, db_session):
    """
    Фикстура для создания access токена для тестового пользователя.
    Убеждаемся, что используем правильный пользователь из БД.
    """
    # Обновляем пользователя из БД, чтобы убедиться, что используем актуальные данные
    db_session.refresh(test_user)
    
    # Проверяем, что пользователь действительно имеет правильную роль
    assert test_user.role == "user", f"test_user должен иметь роль 'user', но имеет '{test_user.role}'"
    assert test_user.username == "testuser", f"test_user должен иметь username 'testuser', но имеет '{test_user.username}'"
    
    data = {
        "sub": test_user.id,
        "username": test_user.username,
        "role": test_user.role
    }
    token = create_access_token(data)
    
    # Проверяем, что токен создан правильно
    from jose import jwt
    from shared.config import SECRET_KEY, ALGORITHM
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == str(test_user.id) or int(payload["sub"]) == test_user.id
    assert payload["username"] == test_user.username
    assert payload["role"] == test_user.role
    
    # Проверяем, что в БД пользователь с этим ID имеет правильную роль
    user_from_db = db_session.query(User).filter(User.id == test_user.id).first()
    assert user_from_db is not None, f"Пользователь с ID {test_user.id} не найден в БД"
    assert user_from_db.role == "user", \
        f"Пользователь с ID {test_user.id} должен иметь роль 'user', но имеет '{user_from_db.role}'"
    assert user_from_db.username == "testuser", \
        f"Пользователь с ID {test_user.id} должен иметь username 'testuser', но имеет '{user_from_db.username}'"
    
    return token


@pytest.fixture
def admin_token(test_admin, db_session):
    """
    Фикстура для создания access токена для администратора.
    """
    # Обновляем пользователя из БД
    db_session.refresh(test_admin)
    data = {
        "sub": test_admin.id,
        "username": test_admin.username,
        "role": test_admin.role
    }
    return create_access_token(data)


@pytest.fixture
def analyst_token(test_analyst, db_session):
    """
    Фикстура для создания access токена для аналитика.
    """
    # Обновляем пользователя из БД
    db_session.refresh(test_analyst)
    data = {
        "sub": test_analyst.id,
        "username": test_analyst.username,
        "role": test_analyst.role
    }
    return create_access_token(data)


# --- Фикстуры для FastAPI клиента ---
@pytest.fixture
def client():
    """
    Фикстура для создания тестового клиента FastAPI.
    """
    return TestClient(app)


@pytest.fixture
def authenticated_client(client, access_token):
    """
    Фикстура для создания аутентифицированного клиента.
    """
    # Создаём новый клиент для каждого теста, чтобы избежать конфликтов
    test_client = TestClient(app)
    test_client.headers = {"Authorization": f"Bearer {access_token}"}
    return test_client


@pytest.fixture
def admin_client(client, admin_token):
    """
    Фикстура для создания клиента с правами администратора.
    """
    # Создаём новый клиент для каждого теста, чтобы избежать конфликтов
    test_client = TestClient(app)
    test_client.headers = {"Authorization": f"Bearer {admin_token}"}
    return test_client


@pytest.fixture
def analyst_client(client, analyst_token):
    """
    Фикстура для создания клиента с правами аналитика.
    """
    # Создаём новый клиент для каждого теста, чтобы избежать конфликтов
    test_client = TestClient(app)
    test_client.headers = {"Authorization": f"Bearer {analyst_token}"}
    return test_client


# --- Фикстуры для тестовых данных ---
@pytest.fixture
def sample_loan_request():
    """
    Фикстура для создания тестового запроса на кредит.
    """
    return {
        "person_age": 35,
        "person_income": 75000,
        "person_home_ownership": "RENT",
        "person_emp_length": 5.0,
        "loan_intent": "DEBTCONSOLIDATION",
        "loan_grade": "B",
        "loan_amnt": 20000,
        "loan_int_rate": 9.5,
        "loan_percent_income": 0.27,
        "cb_person_default_on_file": "N",
        "cb_person_cred_hist_length": 4
    }


@pytest.fixture
def sample_feedback_request(sample_loan_request):
    """
    Фикстура для создания тестового фидбэка.
    """
    data = sample_loan_request.copy()
    data.update({
        "predicted_status": 0,
        "actual_status": 1,
        "probability_repaid": 0.92,
        "probability_default": 0.08
    })
    return data


@pytest.fixture
def sample_login_request():
    """
    Фикстура для создания тестового запроса на логин.
    """
    return {
        "username": "testuser",
        "password": "testpass123"
    }


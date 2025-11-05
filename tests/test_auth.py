# tests/test_auth.py
"""
Unit тесты для модуля аутентификации (shared/auth.py)
"""

import pytest
from datetime import timedelta
from fastapi import HTTPException
from jose import jwt

from shared.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
    get_current_user,
    require_role
)
from shared.models import User
from shared.config import SECRET_KEY, ALGORITHM


class TestPasswordHashing:
    """Тесты для хеширования паролей"""
    
    def test_get_password_hash(self):
        """Тест создания хеша пароля"""
        password = "testpass123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Хеши должны быть разными (из-за соли)
        assert hash1 != hash2
        # Хеши должны быть строками
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)
    
    def test_verify_password(self):
        """Тест проверки пароля"""
        password = "testpass123"
        password_hash = get_password_hash(password)
        
        # Правильный пароль
        assert verify_password(password, password_hash) is True
        
        # Неправильный пароль
        assert verify_password("wrongpass", password_hash) is False


class TestTokenCreation:
    """Тесты для создания JWT токенов"""
    
    def test_create_access_token(self):
        """Тест создания access токена"""
        data = {"sub": 1, "username": "testuser", "role": "user"}
        token = create_access_token(data)
        
        # Токен должен быть строкой
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Декодируем токен и проверяем содержимое
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"
        assert payload["role"] == "user"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_create_access_token_with_expires_delta(self):
        """Тест создания access токена с кастомным временем жизни"""
        data = {"sub": 1, "username": "testuser", "role": "user"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=expires_delta)
        
        # Декодируем токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self):
        """Тест создания refresh токена"""
        data = {"sub": 1, "username": "testuser"}
        token = create_refresh_token(data)
        
        # Токен должен быть строкой
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Декодируем токен и проверяем содержимое
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"
        assert payload["type"] == "refresh"
        assert "exp" in payload


class TestTokenVerification:
    """Тесты для проверки JWT токенов"""
    
    def test_verify_token_valid(self):
        """Тест проверки валидного токена"""
        data = {"sub": 1, "username": "testuser", "role": "user"}
        token = create_access_token(data)
        
        payload = verify_token(token, "access")
        # JWT всегда возвращает sub как строку после декодирования
        assert payload["sub"] == "1" or int(payload["sub"]) == 1
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"
    
    def test_verify_token_invalid(self):
        """Тест проверки невалидного токена"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token, "access")
        
        assert exc_info.value.status_code == 401
    
    def test_verify_token_wrong_type(self):
        """Тест проверки токена с неправильным типом"""
        data = {"sub": 1, "username": "testuser"}
        refresh_token = create_refresh_token(data)
        
        # Попытка использовать refresh токен как access токен
        with pytest.raises(HTTPException) as exc_info:
            verify_token(refresh_token, "access")
        
        assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    """Тесты для получения текущего пользователя"""
    
    def test_get_current_user_valid(self, test_user, db_session):
        """Тест получения текущего пользователя с валидным токеном"""
        # Создаём токен
        data = {"sub": test_user.id, "username": test_user.username, "role": test_user.role}
        token = create_access_token(data)
        
        # Создаём mock credentials
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Получаем пользователя
        user = get_current_user(credentials, db_session)
        
        assert user.id == test_user.id
        assert user.username == test_user.username
        assert user.role == test_user.role
    
    def test_get_current_user_inactive(self, db_session):
        """Тест получения неактивного пользователя"""
        # Создаём неактивного пользователя
        inactive_user = User(
            username="inactive",
            password_hash=get_password_hash("pass123"),
            role="user",
            is_active=False
        )
        db_session.add(inactive_user)
        db_session.commit()
        db_session.refresh(inactive_user)
        
        # Создаём токен
        data = {"sub": inactive_user.id, "username": inactive_user.username, "role": inactive_user.role}
        token = create_access_token(data)
        
        # Создаём mock credentials
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Попытка получить неактивного пользователя должна вызвать исключение
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials, db_session)
        
        assert exc_info.value.status_code == 403


class TestRequireRole:
    """Тесты для проверки ролей"""
    
    def test_require_role_success(self, test_admin, db_session):
        """Тест успешной проверки роли"""
        # Создаём токен для администратора
        data = {"sub": test_admin.id, "username": test_admin.username, "role": test_admin.role}
        token = create_access_token(data)
        
        # Создаём mock credentials
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Проверяем роль администратора
        role_checker = require_role(["admin"])
        user = role_checker(get_current_user(credentials, db_session))
        
        assert user.role == "admin"
    
    def test_require_role_failure(self, test_user, db_session):
        """Тест неуспешной проверки роли"""
        # Создаём токен для обычного пользователя
        data = {"sub": test_user.id, "username": test_user.username, "role": test_user.role}
        token = create_access_token(data)
        
        # Создаём mock credentials
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Попытка доступа к эндпоинту, требующему роль admin
        with pytest.raises(HTTPException) as exc_info:
            role_checker = require_role(["admin"])
            role_checker(get_current_user(credentials, db_session))
        
        assert exc_info.value.status_code == 403


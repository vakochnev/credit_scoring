# shared/auth.py
"""
Модуль аутентификации и авторизации для FastAPI

Модуль реализует:
- JWT токены (access и refresh)
- Систему ролей (admin, analyst, user)
- Проверку доступа по ролям
- Валидацию токенов

Основные функции:
- create_access_token: создание JWT токена
- create_refresh_token: создание refresh токена
- verify_token: проверка токена
- get_current_user: получение текущего пользователя из токена
- require_role: декоратор для проверки роли

Автор: [Кочнева Арина]
Год: 2025
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import bcrypt

from shared.models import User
from shared.database import SessionLocal
from shared.config import (
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)


# --- 🔐 Настройка HTTP Bearer для JWT ---
security = HTTPBearer()


def get_db():
    """Зависимость для получения сессии БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создаёт JWT access токен.

    Args:
        data (dict): Данные для токена (user_id, username, role)
        expires_delta (Optional[timedelta]): Время жизни токена

    Returns:
        str: Закодированный JWT токен
    """
    to_encode = data.copy()
    # Приводим subject к строке согласно RFC7519
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Создаёт JWT refresh токен.

    Args:
        data (dict): Данные для токена (user_id, username)

    Returns:
        str: Закодированный JWT refresh токен
    """
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Проверяет и декодирует JWT токен.

    Args:
        token (str): JWT токен
        token_type (str): Тип токена ("access" или "refresh")

    Returns:
        dict: Декодированные данные токена

    Raises:
        HTTPException: Если токен невалиден или истёк
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Проверка типа токена
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный тип токена"
            )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Получает текущего пользователя из JWT токена.

    Args:
        credentials: HTTP Bearer токен из заголовка
        db: Сессия БД

    Returns:
        User: Объект пользователя

    Raises:
        HTTPException: Если токен невалиден или пользователь не найден
    """
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    sub = payload.get("sub")
    try:
        user_id = int(sub) if sub is not None else None
    except (TypeError, ValueError):
        user_id = None
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )
    
    return user


def require_role(allowed_roles: List[str]):
    """
    Декоратор для проверки роли пользователя.

    Args:
        allowed_roles (List[str]): Список разрешённых ролей

    Returns:
        Зависимость FastAPI для проверки роли

    Пример использования:
        @app.post("/admin-only")
        def admin_endpoint(
            current_user: User = Depends(require_role(["admin"]))
        ):
            ...
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав. Требуется одна из ролей: {allowed_roles}"
            )
        return current_user
    
    return role_checker


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет пароль против хеша.

    Args:
        plain_password (str): Пароль в открытом виде
        hashed_password (str): Хеш пароля

    Returns:
        bool: True если пароль верен, False иначе
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """
    Хеширует пароль используя bcrypt.

    Args:
        password (str): Пароль в открытом виде

    Returns:
        str: Хеш пароля
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

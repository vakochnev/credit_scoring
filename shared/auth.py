# shared/auth.py
"""
Модуль аутентификации для FastAPI

Модуль реализует базовую HTTP-авторизацию (HTTP Basic Auth) для защиты эндпоинтов API.
Используется как зависимость в FastAPI через `Depends()`.

Основные функции:
- verify_credentials: проверка логина и пароля
- Интеграция с конфигурацией API_AUTH

Автор: [Кочнева Арина]
Год: 2025
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# Импорт данных аутентификации из централизованной конфигурации
from shared.config import API_AUTH


# --- 🔐 Система HTTP Basic Auth ---
"""
HTTPBasic — встроенный инструмент FastAPI для реализации 
HTTP Basic Authentication.
Ожидает заголовок Authorization: Basic <base64(логин:пароль)>
"""
security = HTTPBasic()


def verify_credentials(
        credentials: HTTPBasicCredentials = Depends(security)
) -> str:
    """
    Проверяет учётные данные пользователя при доступе к защищённым эндпоинтам.

    Функция используется как зависимость в FastAPI:
        @app.get("/protected", dependencies=[Depends(verify_credentials)])

    Процесс:
        1. Получает логин и пароль из HTTP-заголовка
        2. Сравнивает с ожидаемыми значениями из config.API_AUTH
        3. При несовпадении — возвращает 401 Unauthorized
        4. При успехе — возвращает имя пользователя

    Args:
        credentials (HTTPBasicCredentials): Данные авторизации (логин и пароль)

    Returns:
        str: Имя пользователя (логин) при успешной аутентификации

    Raises:
        HTTPException: Если логин или пароль неверны

    Пример использования:
        В эндпоинте:
            @app.get("/predict", dependencies=[Depends(verify_credentials)])
            def predict(...): ...

    Безопасность:
        - Учётные данные передаются в base64 (не шифруется!)
        - Рекомендуется использовать только по HTTPS
        - В production можно заменить на JWT или OAuth2

    Примечания:
        - Использует стандартный механизм HTTP Basic Auth
        - Сообщение об ошибке не раскрывает, что именно неверно (логин или пароль)
        - Поддерживает только одного пользователя (для простоты)
    """
    # Получаем правильные учётные данные из конфигурации
    correct_username = API_AUTH[0]
    correct_password = API_AUTH[1]

    # Проверяем логин и пароль
    if (
        credentials.username != correct_username or
            credentials.password != correct_password
    ):
        # Возвращаем 401 Unauthorized с заголовком для повторного запроса
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учётные данные",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Аутентификация успешна — возвращаем имя пользователя
    return credentials.username

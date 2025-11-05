# scripts/create_users.py
"""
Скрипт для создания пользователей с ролями

Создаёт пользователей:
- admin: администратор с полным доступом
- analyst: аналитик с доступом к отчётам и фидбэкам
- user: обычный пользователь с базовым доступом
"""
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from shared.database import engine
from shared.models import User
from shared.auth import get_password_hash

# Создаём сессию
session = Session(bind=engine)

# Список пользователей для создания
users_to_create = [
    {
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "is_active": True
    },
    {
        "username": "analyst",
        "password": "analyst123",
        "role": "analyst",
        "is_active": True
    },
    {
        "username": "user",
        "password": "user123",
        "role": "user",
        "is_active": True
    }
]

# Создание пользователей
for user_data in users_to_create:
    existing_user = session.query(User).filter(
        User.username == user_data["username"]
    ).first()
    
    if not existing_user:
        password_hash = get_password_hash(user_data["password"])
        new_user = User(
            username=user_data["username"],
            password_hash=password_hash,
            role=user_data["role"],
            is_active=user_data["is_active"]
        )
        session.add(new_user)
        print(
            f"✅ Пользователь '{user_data['username']}' "
            f"(роль: {user_data['role']}) создан"
        )
    else:
        # Обновляем пароль и роль существующего пользователя
        password_hash = get_password_hash(user_data["password"])
        updated = False
        
        if existing_user.password_hash != password_hash:
            existing_user.password_hash = password_hash
            updated = True
            print(
                f"🔄 Пароль пользователя '{user_data['username']}' обновлён"
            )
        
        if existing_user.role != user_data["role"]:
            existing_user.role = user_data["role"]
            updated = True
            print(
                f"🔄 Роль пользователя '{user_data['username']}' "
                f"обновлена на '{user_data['role']}'"
            )
        
        if not updated:
            print(
                f"ℹ️ Пользователь '{user_data['username']}' уже существует и актуален"
            )

session.commit()
session.close()

print("\n📋 Созданные пользователи:")
print("  - admin / admin123 (роль: admin)")
print("  - analyst / analyst123 (роль: analyst)")
print("  - user / user123 (роль: user)")
# scripts/create_users.py
from sqlalchemy.orm import Session
import bcrypt
from shared.database import engine
from shared.models import User

# Создаём таблицы
#Base.metadata.create_all(bind=engine)

# Создаём сессию
session = Session(bind=engine)

# Хешируем пароль
password = "password123"
salt = bcrypt.gensalt()
password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# Создаём пользователя
admin = session.query(User).filter(User.username == "admin").first()
if not admin:
    admin = User(username="admin", password_hash=password_hash)
    session.add(admin)
    session.commit()
    print("✅ Пользователь 'admin' создан")
else:
    print("ℹ️ Пользователь 'admin' уже существует")

session.close()
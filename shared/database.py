# shared/database.py
"""
Модуль базы данных для FastAPI

Модуль реализует подключение к SQLite-базе данных с использованием SQLAlchemy.
Предназначен для хранения пользователей, фидбэков или других сущностей.

Основные компоненты:
- engine: подключение к БД
- SessionLocal: фабрика сессий
- Base: базовый класс для ORM-моделей

Автор: [Кочнева Арина]
Год: 2025
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# --- 🗄️ Настройка подключения к базе данных ---
"""
Используется SQLite для простоты и автономности.
Файл базы данных: ./users.db (в корне проекта)

Примечания:
    - connect_args={"check_same_thread": False} — необходимо для SQLite при использовании в FastAPI
    - Для production рекомендуется PostgreSQL или MySQL
"""
SQLALCHEMY_DATABASE_URL = "sqlite:///./users.db"


# --- 🔌 Создание движка (engine) ---
"""
Движок управляет пулом соединений с базой данных.
Параметры:
    - connect_args: отключает проверку потока для SQLite
    - future=True: включает режим SQLAlchemy 2.0 (опционально)
"""
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Требуется для SQLite
)


# --- 🔄 Фабрика сессий ---
"""
SessionLocal — это "фабрика" сессий, которая создаёт новые сессии для каждого запроса.

Параметры:
    - autocommit=False: отключает автокоммит (все изменения требуют явного commit())
    - autoflush=False: отключает авто-выгрузку изменений в БД
    - bind=engine: привязывает сессию к движку

Используется в FastAPI через зависимость:
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
"""
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# --- 🧩 Базовый класс для моделей ---
"""
Base — базовый класс для всех ORM-моделей.
Наследуя от Base, модели автоматически регистрируются в метаданных SQLAlchemy.

Пример использования:
    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        name = Column(String)
"""
Base = declarative_base()


# --- 💡 Как использовать в FastAPI ---
"""
Пример зависимости для инъекции БД в эндпоинты:

from fastapi import Depends
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/")
def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()
"""

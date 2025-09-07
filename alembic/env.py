# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from pathlib import Path

# Добавляем путь к проекту
root_dir = Path(__file__).parent.parent
if str(root_dir) not in os.sys.path:
    os.sys.path.insert(0, str(root_dir))

# Импортируем Base и модели
#from shared.database import Base
from shared.models import Base, FeedbackDB, User 

# Настройка логгирования
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Указываем метаданные
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True  # Для SQLite
        )

        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
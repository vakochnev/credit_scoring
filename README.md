# 📊 Credit Scoring API — Дипломный проект

**Автор:** Кочнева Арина  
**Год:** 2025  
**Тема:** Кредитный скоринг с ансамблевыми моделями и интерпретируемостью (SHAP)

---

## 🔧 Описание

Система кредитного скоринга на основе **ансамблевой модели** (RandomForest + XGBoost + CatBoost) с поддержкой:

- 📈 Прогнозирования риска дефолта
- 📊 Интерпретируемости (SHAP)
- 📄 Генерации PDF-отчётов
- 🔁 Дообучения на обратной связи
- 🔐 Авторизации через базу данных
- 🗄️ Хранения фидбэков в SQLite
- 🔄 Миграций с помощью Alembic

---

## 📁 Структура проекта
credit_scoring/
├── app/
│ └── main.py # FastAPI backend
├── frontend/
│ ├── app.py # Основной интерфейс (Streamlit)
│ └── admin.py # Админ-панель
├── shared/
│ ├── config.py # Конфигурация
│ ├── database.py # ORM-модели (SQLAlchemy)
│ ├── models.py # Pydantic-модели
│ └── data_processing.py # Предобработка
├── services/
│ ├── model_training.py # Обучение
│ ├── reporting.py # Отчёты
│ ├── utils.py # Прогноз и объяснение
│ └── retrain.py # Дообучение
├── alembic/
│ ├── env.py
│ └── versions/ # Миграции
├── models/ # Сохранённые модели
├── reports/ # PDF-отчёты
├── data/ # Данные
├── credit_scoring.db # База данных
└── credit_risk_dataset.csv # Исходный датасет


---
## ⚙️ Установка и настройка
### 1. Клонирование репозитория

```bash
git clone https://github.com/username/credit_scoring.git
cd credit_scoring

2. Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

3. Установка зависимостей
pip install --upgrade pip
pip install fastapi uvicorn streamlit pandas scikit-learn xgboost catboost lightgbm joblib shap weasyprint jinja2 sqlalchemy bcrypt alembic

🗄️ Настройка базы данных и Alembic
1. Инициализация Alembic
bash
alembic init alembic

2. Настройка alembic.ini
Замените строку:
sqlalchemy.url = driver://user:pass@localhost/databasename
на:
sqlalchemy.url = sqlite:///./credit_scoring.db

3. Обновите alembic/env.py
Замените содержимое на этот код .

4. Создайте миграцию
bash
alembic revision --autogenerate -m "Create users and feedback tables"

5. Примените миграцию
bash
alembic upgrade head

➡️ Будет создан файл credit_scoring.db с таблицами:

users — для авторизации
feedback — для хранения обратной связи
6. Добавьте администратора
python
# scripts/create_admin.py
from sqlalchemy.orm import Session
import bcrypt
from shared.database import User, engine

db = Session(bind=engine)
password = "password123"
salt = bcrypt.gensalt()
password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

admin = User(username="admin", password_hash=password_hash)
db.add(admin)
db.commit()
db.close()
Запустите:

bash
python scripts/create_admin.py

📡 API Эндпоинты
🔐 Авторизация
Все эндпоинты (кроме /) требуют HTTP Basic Auth.

GET /
Описание: Приветственное сообщение
Авторизация: Нет
Ответ:

json
{
  "message": "Добро пожаловать в Credit Scoring API"
}
POST /train-final
Описание: Обучает ансамблевую модель
Ответ:

json
{
  "model": "Ensemble (RF + XGBoost + CatBoost)",
  "accuracy": 0.925
}
POST /explain
Описание: Прогноз и объяснение с SHAP
Тело запроса:

json
{
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
Ответ:

json
{
  "prediction": 0,
  "status": "repaid",
  "decision": "approve",
  "probability_repaid": 0.927,
  "explanation": {
    "base_value": 0.48,
    "shap_values": [...],
    "summary": [
      "loan_grade_B: ↓ риск (-0.250)",
      "person_income: ↓ риск (-0.180)",
      ...
    ],
    "shap_image_base64": "iVBORw0KGgoAAAANSUhEUg..."
  }
}
POST /report
Описание: Генерирует PDF-отчёт
Ответ:

json
{
  "report_path": "/home/user/credit_scoring/reports/explanation_report.pdf"
}
POST /feedback
Описание: Сохраняет обратную связь
Тело запроса:

json
{
  "person_age": 35,
  "person_income": 75000,
  ...
  "predicted_status": 0,
  "actual_status": 1
}
Ответ:

json
{
  "status": "success",
  "id": 1
}
POST /retrain
Описание: Дообучает модель на фидбэках
Ответ:

json
{
  "status": "retrained",
  "samples_used": 12,
  "accuracy_on_feedback": 0.917,
  "class_balance": { "0": 0.55, "1": 0.45 }
}
GET /compare
Описание: Сравнивает модели
Ответ:

json
{
  "models": [
    { "model": "RandomForest", "accuracy": 0.91, "auc": 0.93 },
    { "model": "XGBoost", "accuracy": 0.92, "auc": 0.94 },
    ...
  ]
}

🖥️ Frontend (Streamlit)
1. Основной интерфейс (frontend/app.py)
🔍 Ввод данных заемщика
🔮 Прогноз и объяснение
📄 Генерация PDF-отчёта
📩 Обратная связь
🔄 Дообучение

2. Админ-панель (frontend/admin.py)
    🛡️ Просмотр фидбэков
    📊 Фильтры и статистика
    📥 Экспорт в CSV
Запуск:

bash
cd frontend && streamlit run admin.py
▶️ Запуск системы

1. Запуск backend (FastAPI)
bash
cd app && uvicorn main:app --reload --host 0.0.0.0 --port 8000

2. Запуск frontend (Streamlit)
bash
cd frontend && streamlit run app.py

📚 Документация API
После запуска backend:

Swagger (интерактивная документация)
http://localhost:8000/docs

ReDoc (альтернативная документация)
http://localhost:8000/redoc

Обе документации:

Автоматически генерируются
Позволяют тестировать эндпоинты
Отображают схемы запросов и ответов

🧠 Алгоритм работы системы

1. Прогнозирование 
Пользователь вводит данные
Frontend → POST /explain
Backend: предобработка → ансамбль → SHAP
Ответ: решение + объяснение
Пользователь может сформировать PDF

2. Дообучение
Пользователь оставляет фидбэк
Данные сохраняются в credit_scoring.db
При /retrain:
Загрузка из БД
Предобработка
Дообучение ансамбля
Сохранение модели

3. Безопасность
🔐 Авторизация через users в БД
🔒 Пароли хешируются (bcrypt)
🔄 Миграции через Alembic
📎 Полезные ссылки

FastAPI Documentation
Streamlit Documentation
SHAP Documentation
Alembic Documentation
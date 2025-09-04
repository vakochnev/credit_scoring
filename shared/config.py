# shared/config.py
"""
Центральная конфигурация проекта

Модуль определяет пути к файлам, директориям и настройкам API.
Используется всеми компонентами системы (FastAPI, Streamlit, сервисы).

Основные функции:
- Определение путей к моделям, данным, отчётам
- Настройка API (хост, порт, авторизация)
- Автоматическое создание необходимых директорий

Автор: [Кочнева Арина]
Год: 2025
"""

from pathlib import Path


# --- 🧭 Определение корня проекта ---
"""
Путь к корню проекта (например, /home/user/credit_scoring).
Определяется как родитель родителя текущего файла:
    shared/ → credit_scoring/
"""
ROOT_DIR = Path(__file__).parent.parent


# --- 📁 Основные директории проекта ---
"""
Определяем структуру папок:
- models/ — обученные модели и метаданные
- data/ — сырые и фидбэки
- reports/ — PDF-отчёты
- reports/images/ — графики для встраивания в PDF
"""
MODELS_DIR = ROOT_DIR / "models"
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
IMAGES_DIR = REPORTS_DIR / "images"  # Для хранения графиков (SHAP, ROC-AUC)


# --- 📄 Пути к ключевым файлам ---
"""
Файлы сериализованы через joblib/pickle.
Используются для:
- Загрузки модели и её компонентов
- Генерации объяснений (SHAP)
- Дообучения на фидбэках
"""
FEATURE_NAMES_PATH = MODELS_DIR / "feature_names.pkl"       # Список фичей после OHE
BACKGROUND_DATA_PATH = MODELS_DIR / "background_data.pkl"   # Фоновые данные для SHAP
ENSEMBLE_MODEL_PATH = MODELS_DIR / "ensemble_model.pkl"     # Ансамблевая модель (VotingClassifier)
REPORT_PATH = REPORTS_DIR / "explanation_report.pdf"        # Стандартный отчёт по заемщику
FEEDBACK_PATH = DATA_DIR / "feedback.jsonl"                 # Фидбэки в формате JSONL (один JSON на строку)
DATA_SOURCE = DATA_DIR / "credit_risk_dataset.csv"          # Исходный датасет для обучения


# --- 🌐 Настройки API ---
"""
Конфигурация FastAPI-сервера.
Используется в:
- FastAPI (host, port)
- Streamlit (API_BASE_URL, auth)
"""
API_BASE_URL = "http://localhost:8000"  # Базовый URL для запросов из фронтенда
HOST = "localhost"                      # Хост для запуска API
PORT = 8000                             # Порт для запуска API
API_AUTH = ("admin", "password123")     # Учётные данные для HTTP Basic Auth


# --- 🛠 Создание директорий при импорте ---
"""
Автоматически создаём все необходимые папки при импорте модуля.
Параметр exist_ok=True — не вызывает ошибку, если папка уже существует.
"""
for path in [MODELS_DIR, DATA_DIR, REPORTS_DIR, IMAGES_DIR]:
    path.mkdir(exist_ok=True)


# --- 🔍 Пример использования ---
"""
Примеры использования в других модулях:

# В services/utils.py
from shared.config import ENSEMBLE_MODEL_PATH, FEATURE_NAMES_PATH
model = joblib.load(ENSEMBLE_MODEL_PATH)

# В app/main.py
from shared.config import DATA_SOURCE
df = pd.read_csv(DATA_SOURCE)

# В frontend/app.py
from shared.config import API_BASE_URL, API_AUTH
response = requests.get(f"{API_BASE_URL}/compare", auth=API_AUTH)
"""

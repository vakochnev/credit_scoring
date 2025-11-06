# 📊 Credit Scoring API — Дипломный проект

**Автор:** Кочнева Арина  
**Год:** 2025  
**Тема:** Кредитный скоринг с ансамблевыми моделями и интерпретируемостью (SHAP)

---

## 📋 Содержание

- [Описание](#-описание)
- [Возможности](#-возможности)
- [Технологический стек](#-технологический-стек)
- [Быстрый старт](#-быстрый-старт)
  - [Локальная установка](#локальная-установка)
  - [Docker](#docker)
- [Структура проекта](#-структура-проекта)
- [API документация](#-api-документация)
- [Безопасность](#-безопасность)
- [Тестирование](#-тестирование)
- [CI/CD и деплой](#cicd-и-деплой)
- [Полезные ссылки](#-полезные-ссылки)

---

## 🔧 Описание

Система кредитного скоринга на основе **ансамблевой модели** (RandomForest + XGBoost + CatBoost) с поддержкой:

- 📈 Прогнозирования риска дефолта
- 📊 Интерпретируемости (SHAP)
- 📄 Генерации PDF-отчётов
- 🔁 Дообучения на обратной связи
- 🔐 JWT авторизации с ролями
- 🗄️ Хранения фидбэков в SQLite
- 🔄 Миграций с помощью Alembic
- 🐳 Docker контейнеризация
- 🚀 CI/CD с GitHub Actions

---

## ✨ Возможности

### Прогнозирование
- Прогноз вероятности дефолта заемщика
- Объяснение решения с помощью SHAP
- Визуализация вклада признаков

### Отчёты
- Генерация PDF-отчётов с объяснением
- Сравнение производительности моделей
- ROC-AUC графики

### Дообучение
- Сбор обратной связи от пользователей
- Автоматическое дообучение модели
- Улучшение качества предсказаний

### Безопасность
- JWT токены (access и refresh)
- Система ролей (admin, analyst, user)
- Разграничение доступа по ролям

---

## 🛠️ Технологический стек

### Backend
- **FastAPI** — веб-фреймворк
- **SQLAlchemy** — ORM
- **Alembic** — миграции БД
- **JWT** (python-jose) — авторизация
- **bcrypt** — хеширование паролей

### Machine Learning
- **scikit-learn** — базовые модели
- **XGBoost** — градиентный бустинг
- **CatBoost** — градиентный бустинг
- **LightGBM** — градиентный бустинг
- **SHAP** — интерпретируемость

### Frontend
- **Streamlit** — веб-интерфейс

### Утилиты
- **WeasyPrint** — генерация PDF
- **pandas** — обработка данных
- **matplotlib** — визуализация

### Тестирование
- **pytest** — тестирование
- **pytest-cov** — покрытие кода

---

## 🚀 Быстрый старт

### Локальная установка

#### 1. Клонирование репозитория

```bash
git clone https://github.com/username/credit_scoring.git
cd credit_scoring
```

#### 2. Создание виртуального окружения

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

#### 3. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Настройка базы данных

```bash
# Применение миграций
alembic upgrade head

# Создание пользователей
python scripts/create_users.py
```

Создаются пользователи:
- `admin` / `admin123` (роль: admin)
- `analyst` / `analyst123` (роль: analyst)
- `user` / `user123` (роль: user)

#### 5. Запуск приложения

**Backend (FastAPI):**
```bash
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend (Streamlit):**
```bash
cd frontend
streamlit run app.py
```

#### 6. Доступ к приложению

- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:8501
- **API документация (Swagger)**: http://localhost:8000/docs
- **API документация (ReDoc)**: http://localhost:8000/redoc

---

### Docker

#### Предварительные требования

- Docker 20.10+
- Docker Compose 1.29+

#### 1. Создание и настройка .env файла

```bash
# Создать .env из примера
cp env.example .env

# Сгенерировать безопасный SECRET_KEY
python scripts/generate_secret_key.py

# Отредактировать .env файл
nano .env  # или любой другой редактор
```

**Обязательные настройки:**
- `SECRET_KEY` - сгенерируйте новый ключ через скрипт или:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

**Основные переменные в .env:**
- `SECRET_KEY` - секретный ключ для JWT (обязательно изменить!)
- `API_BASE_URL` - URL API (по умолчанию: http://localhost:8000)
- `HOST`, `PORT` - настройки FastAPI сервера
- `STREAMLIT_SERVER_PORT` - порт для Streamlit
- `LOGS_DIR` - директория для логов (по умолчанию: logs/)
- `LOG_FILE_NAME` - имя файла лога backend (по умолчанию: credit_scoring.log)
- `LOG_LEVEL` - уровень логирования (INFO, DEBUG, WARNING, ERROR)
- `USE_JSON_LOGS` - использовать JSON формат логов (true/false)

#### 2. Сборка и запуск

```bash
# Сборка и запуск всех сервисов
docker compose up --build

# Или в фоновом режиме
docker compose up -d --build
```

#### 3. Доступ к приложению

- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:8501
- **API документация**: http://localhost:8000/docs

---

## 🐳 Команды Docker

### Основные команды

```bash
# Сборка и запуск
docker compose up --build

# Запуск в фоновом режиме
docker compose up -d

# Остановка контейнеров
docker compose stop

# Остановка и удаление контейнеров
docker compose down

# Остановка, удаление контейнеров и volumes
docker compose down -v
```

### Просмотр логов

```bash
# Логи всех сервисов
docker compose logs

# Логи конкретного сервиса
docker compose logs backend
docker compose logs frontend

# Логи в реальном времени
docker compose logs -f

# Логи последних 100 строк
docker compose logs --tail=100
```

### Управление контейнерами

```bash
# Статус контейнеров
docker compose ps

# Перезапуск контейнеров
docker compose restart

# Перезапуск конкретного сервиса
docker compose restart backend

# Пересборка без кэша
docker compose build --no-cache

# Пересборка и перезапуск
docker compose up --build -d
```

### Работа с контейнерами

```bash
# Вход в backend контейнер
docker compose exec backend bash

# Вход в frontend контейнер
docker compose exec frontend bash

# Выполнение команды в контейнере
docker compose exec backend python scripts/create_users.py
docker compose exec backend alembic upgrade head

# Просмотр переменных окружения
docker compose exec backend env
```

### Volumes и данные

```bash
# Просмотр volumes
docker volume ls

# Просмотр данных в volume
docker compose exec backend ls -la /app/data

# Копирование файлов из контейнера
docker cp credit_scoring_backend:/app/models/ensemble_model.pkl ./models/

# Копирование файлов в контейнер
docker cp ./data/credit_risk_dataset.csv credit_scoring_backend:/app/data/
```

### Очистка

```bash
# Удаление неиспользуемых образов
docker image prune

# Удаление всех неиспользуемых ресурсов
docker system prune -a

# Удаление volumes
docker volume prune
```

### Проверка здоровья

```bash
# Проверка статуса healthcheck
docker compose ps

# Проверка вручную
curl http://localhost:8000/  # Backend
curl http://localhost:8501/_stcore/health  # Frontend
```

---

## 📁 Структура проекта

```
credit_scoring/
├── app/                          # Backend приложение
│   ├── main.py                   # FastAPI приложение
│   └── services/                 # Сервисы
│       ├── model_training.py     # Обучение моделей
│       ├── utils.py              # Прогноз и объяснение
│       ├── retrain.py            # Дообучение
│       ├── reporting.py          # Генерация PDF
│       └── model_comparison.py   # Сравнение моделей
├── frontend/                      # Frontend приложение
│   ├── app.py                    # Основной интерфейс
│   └── admin.py                  # Админ-панель
├── shared/                        # Общие модули
│   ├── config.py                 # Конфигурация
│   ├── database.py               # Подключение к БД
│   ├── models.py                 # Pydantic и ORM модели
│   ├── auth.py                   # JWT авторизация
│   └── data_processing.py        # Предобработка данных
├── tests/                         # Unit тесты
│   ├── conftest.py               # Фикстуры pytest
│   ├── test_auth.py              # Тесты авторизации
│   ├── test_models.py            # Тесты моделей
│   ├── test_data_processing.py  # Тесты предобработки
│   └── test_api.py               # Тесты API
├── alembic/                       # Миграции БД
│   └── versions/                 # Файлы миграций
├── scripts/                       # Вспомогательные скрипты
│   ├── create_users.py          # Создание пользователей
│   ├── deploy_pythonanywhere.sh  # Скрипт деплоя
│   └── run_tests.sh              # Скрипт запуска тестов
├── models/                        # Обученные модели
├── data/                          # Данные
├── reports/                       # PDF отчёты
├── .github/                       # GitHub Actions
│   └── workflows/
│       ├── ci.yml                # CI workflow
│       └── deploy.yml             # Deploy workflow
├── Dockerfile.backend             # Dockerfile для backend
├── Dockerfile.frontend            # Dockerfile для frontend
├── docker-compose.yml             # Docker Compose конфигурация
├── pytest.ini                     # Конфигурация pytest
├── requirements.txt               # Зависимости Python
└── README.md                      # Эта документация
```

---

## 📡 API документация

### 🔐 Авторизация

Все эндпоинты (кроме `/`) требуют JWT токен в заголовке:
```
Authorization: Bearer <access_token>
```

#### Получение токена

**POST `/login`**

Запрос:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

Ответ:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Пример curl:**
```bash
# Получение токена для admin
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Сохранение токена в переменную (Linux/Mac)
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Использование сохранённого токена
echo "Токен: $TOKEN"
```

#### Обновление токена

**POST `/refresh`**

Запрос:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Пример curl:**
```bash
# Обновление токена
curl -X POST http://localhost:8000/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"YOUR_REFRESH_TOKEN_HERE"}'
```

#### Получение информации о пользователе

**GET `/me`**

Ответ:
```json
{
  "id": 1,
  "username": "admin",
  "role": "admin",
  "is_active": true
}
```

**Пример curl:**
```bash
# Получение информации о текущем пользователе
curl -X GET http://localhost:8000/me \
  -H "Authorization: Bearer $TOKEN"

# Или с токеном напрямую
curl -X GET http://localhost:8000/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### 📊 Эндпоинты прогнозирования

#### Прогноз статуса кредита

**POST `/predict`**  
Требует авторизацию: любая роль

Запрос:
```json
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
```

Ответ:
```json
{
  "prediction": 0,
  "status": "repaid",
  "decision": "approve",
  "probability_repaid": 0.927,
  "probability_default": 0.073
}
```

**Пример curl:**
```bash
# Получение прогноза (требуется токен любой роли)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
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
  }'
```

#### Объяснение решения (SHAP)

**POST `/explain`**  
Требует роль: analyst, admin, user

Запрос: (тот же, что для `/predict`)

Ответ:
```json
{
  "prediction": 0,
  "status": "repaid",
  "decision": "approve",
  "probability_repaid": 0.927,
  "explanation": {
    "base_value": 0.48,
    "shap_values": [
      {"feature": "loan_grade_B", "value": -0.250},
      {"feature": "person_income", "value": -0.180}
    ],
    "summary": [
      "loan_grade_B: ↓ риск (-0.250)",
      "person_income: ↓ риск (-0.180)"
    ],
    "shap_image_base64": "iVBORw0KGgoAAAANSUhEUg..."
  }
}
```

**Пример curl:**
```bash
# Получение объяснения с SHAP (требуется роль: analyst, admin, user)
curl -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
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
  }' | python3 -m json.tool
```

#### Генерация PDF-отчёта

**POST `/report`**  
Требует роль: analyst, admin

Запрос: (тот же, что для `/predict`)

Ответ:
```json
{
  "report_path": "/app/reports/explanation_report.pdf"
}
```

**Пример curl:**
```bash
# Генерация PDF-отчёта (требуется роль: analyst, admin)
curl -X POST http://localhost:8000/report \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
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
  }'
```

---

### 🔄 Эндпоинты обучения

#### Обучение модели

**POST `/train-final`**  
Требует роль: admin

Ответ:
```json
{
  "model": "Ensemble (RF + XGBoost + CatBoost)",
  "accuracy": 0.925
}
```

**Пример curl:**
```bash
# Обучение модели (требуется роль: admin)
curl -X POST http://localhost:8000/train-final \
  -H "Authorization: Bearer $TOKEN"

# С подробным выводом
curl -X POST http://localhost:8000/train-final \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nHTTP Status: %{http_code}\n"
```

#### Дообучение модели

**POST `/retrain`**  
Требует роль: admin, analyst

Ответ:
```json
{
  "status": "retrained",
  "samples_used": 12,
  "accuracy_on_feedback": 0.917,
  "class_balance": {"0": 0.55, "1": 0.45}
}
```

**Пример curl:**
```bash
# Дообучение модели (требуется роль: admin, analyst)
curl -X POST http://localhost:8000/retrain \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

#### Сравнение моделей

**GET `/compare`**  
Требует роль: analyst, admin

Ответ:
```json
{
  "models": [
    {"model": "RandomForest", "accuracy": 0.91, "auc": 0.93},
    {"model": "XGBoost", "accuracy": 0.92, "auc": 0.94},
    {"model": "CatBoost", "accuracy": 0.90, "auc": 0.92},
    {"model": "Ensemble", "accuracy": 0.93, "auc": 0.95}
  ]
}
```

**Пример curl:**
```bash
# Сравнение моделей (требуется роль: analyst, admin)
curl -X GET http://localhost:8000/compare \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Генерация PDF-отчёта сравнения моделей
curl -X POST http://localhost:8000/generate-comparison-report \
  -H "Authorization: Bearer $TOKEN"
```

---

### 📩 Эндпоинты обратной связи

#### Сохранение фидбэка

**POST `/feedback`**  
Требует авторизацию: любая роль

Запрос:
```json
{
  "person_age": 35,
  "person_income": 75000,
  ...
  "predicted_status": 0,
  "actual_status": 1,
  "probability_repaid": 0.92,
  "probability_default": 0.08
}
```

Ответ:
```json
{
  "status": "success",
  "id": 1
}
```

**Пример curl:**
```bash
# Сохранение обратной связи (требуется токен любой роли)
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
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
    "cb_person_cred_hist_length": 4,
    "predicted_status": 0,
    "actual_status": 1,
    "probability_repaid": 0.92,
    "probability_default": 0.08
  }'
```

---

## 🧪 Тестирование API с curl

### Полный пример тестирования

```bash
# 1. Получение токена для admin
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Токен получен: ${TOKEN:0:50}..."

# 2. Проверка информации о пользователе
echo -e "\n=== Информация о пользователе ==="
curl -s -X GET http://localhost:8000/me \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 3. Прогноз
echo -e "\n=== Прогноз ==="
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
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
  }' | python3 -m json.tool

# 4. Объяснение (только для admin, analyst, user)
echo -e "\n=== Объяснение ==="
curl -s -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
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
  }' | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Решение: {data['decision']}\"); print(f\"Вероятность: {data['probability_repaid']:.2%}\"); print(f\"Объяснение: {len(data['explanation']['summary'])} признаков\")"

# 5. Обучение модели (только для admin)
echo -e "\n=== Обучение модели ==="
curl -s -X POST http://localhost:8000/train-final \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 6. Сравнение моделей (только для admin, analyst)
echo -e "\n=== Сравнение моделей ==="
curl -s -X GET http://localhost:8000/compare \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 7. Сохранение обратной связи
echo -e "\n=== Сохранение обратной связи ==="
curl -s -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
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
    "cb_person_cred_hist_length": 4,
    "predicted_status": 0,
    "actual_status": 0,
    "probability_repaid": 0.92,
    "probability_default": 0.08
  }' | python3 -m json.tool
```

### Тестирование с разными ролями

```bash
# Получение токена для analyst
ANALYST_TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst","password":"analyst123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Попытка обучить модель (должна вернуть 403)
echo "=== Попытка обучить модель с ролью analyst ==="
curl -s -X POST http://localhost:8000/train-final \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  -w "\nHTTP Status: %{http_code}\n"

# Получение токена для user
USER_TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"user123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Попытка получить отчёт (должна вернуть 403)
echo -e "\n=== Попытка получить отчёт с ролью user ==="
curl -s -X POST http://localhost:8000/report \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"person_age": 35, "person_income": 75000, "person_home_ownership": "RENT", "person_emp_length": 5.0, "loan_intent": "DEBTCONSOLIDATION", "loan_grade": "B", "loan_amnt": 20000, "loan_int_rate": 9.5, "loan_percent_income": 0.27, "cb_person_default_on_file": "N", "cb_person_cred_hist_length": 4}' \
  -w "\nHTTP Status: %{http_code}\n"
```

---

## 🔐 Безопасность

### Система ролей

#### Роль: `admin`
- ✅ Полный доступ ко всем функциям
- ✅ Обучение моделей (`/train-final`)
- ✅ Дообучение моделей (`/retrain`)
- ✅ Сравнение моделей (`/compare`)
- ✅ Генерация отчётов (`/report`)
- ✅ Просмотр фидбэков

#### Роль: `analyst`
- ✅ Прогнозирование (`/predict`, `/explain`)
- ✅ Генерация PDF-отчётов (`/report`)
- ✅ Сравнение моделей (`/compare`)
- ✅ Дообучение моделей (`/retrain`)
- ✅ Просмотр фидбэков

#### Роль: `user`
- ✅ Базовое прогнозирование (`/predict`)
- ✅ Объяснение решений (`/explain`)
- ✅ Сохранение фидбэков (`/feedback`)
- ❌ Нет доступа к обучению, отчётам, сравнению моделей

### JWT токены

- **Access токен**: время жизни 30 минут
- **Refresh токен**: время жизни 7 дней
- Токены передаются в заголовке: `Authorization: Bearer <token>`

### Рекомендации для production

1. **Измените SECRET_KEY** в `.env` файле
2. **Используйте HTTPS** для передачи токенов
3. **Храните SECRET_KEY** в переменных окружения
4. **Настройте rate limiting**
5. **Регулярно обновляйте зависимости**

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Запуск всех тестов
pytest

# Запуск с подробным выводом
pytest -v

# Запуск с покрытием кода
pytest --cov=app --cov=shared --cov-report=html

# Запуск конкретного файла
pytest tests/test_auth.py

# Запуск через скрипт
./scripts/run_tests.sh
```

### Покрытие кода

Текущее покрытие: **55%+**

Просмотр отчёта:
```bash
pytest --cov=app --cov=shared --cov-report=html
open htmlcov/index.html
```

### Структура тестов

- `tests/test_auth.py` — тесты авторизации
- `tests/test_models.py` — тесты моделей данных
- `tests/test_data_processing.py` — тесты предобработки
- `tests/test_api.py` — тесты API эндпоинтов

Подробнее: [docs/TESTING.md](docs/TESTING.md)

---

## 🚀 CI/CD и деплой

### GitHub Actions

#### CI (Continuous Integration)

**Файл**: `.github/workflows/ci.yml`

**Задачи**:
- ✅ Линтинг (Black, Flake8, Pylint)
- ✅ Проверка формата кода
- ✅ Запуск тестов (pytest с покрытием)
- ✅ Проверка импортов
- ✅ Проверка миграций Alembic
- ✅ Сборка Docker образов (backend и frontend)
- ✅ Проверка Docker образов

**Запуск**: При push в `main`/`develop` или создании Pull Request

#### CD (Continuous Deployment)

**Файл**: `.github/workflows/deploy.yml`

**Задачи Pre-Deploy** (выполняются перед деплоем):
- ✅ Линтинг кода (Black, Flake8, Pylint)
- ✅ Проверка формата кода
- ✅ Запуск тестов (pytest с покрытием)
- ✅ Проверка импортов
- ✅ Проверка миграций Alembic
- ✅ Сборка Docker образов (backend и frontend)
- ✅ Проверка Docker образов

**Задачи Deploy** (выполняются только после успешных проверок):
- ✅ Подключение к PythonAnywhere через SSH
- ✅ Обновление кода из git
- ✅ Установка зависимостей
- ✅ Применение миграций
- ✅ Создание пользователей
- ✅ Перезагрузка приложения
- ✅ Проверка успешности деплоя

**Запуск**: При push в `main` ветку (только после успешного прохождения всех проверок)

**Условия**: Деплой запускается **только если** все тесты, линтеры и Docker сборка прошли успешно

### Настройка

1. Перейдите в **Settings → Secrets and variables → Actions**
2. Добавьте секреты:
   - `PYTHONANYWHERE_SSH_KEY`
   - `PYTHONANYWHERE_USER`
   - `PYTHONANYWHERE_HOST`
   - `PYTHONANYWHERE_PATH`

Подробнее: [docs/CI_CD_SETUP.md](docs/CI_CD_SETUP.md), [docs/DEPLOY.md](docs/DEPLOY.md)

---

## 📊 Работа с данными

### Обучение модели

```bash
# Через API
curl -X POST http://localhost:8000/train-final \
  -H "Authorization: Bearer <token>"

# Или через Docker
docker compose exec backend python -c "
from app.main import train_final_api
train_final_api()
"
```

### Применение миграций

```bash
# Локально
alembic upgrade head

# В Docker
docker compose exec backend alembic upgrade head
```

### Создание пользователей

```bash
# Локально
python scripts/create_users.py

# В Docker
docker compose exec backend python scripts/create_users.py
```

---

## 🔍 Отладка

### Логи

```bash
# Логи приложения
tail -f credit_scoring.log

# Логи Docker
docker compose logs -f backend
docker compose logs -f frontend
```

### Проверка БД

```bash
# SQLite через командную строку
sqlite3 credit_scoring.db

# Просмотр таблиц
.tables

# Просмотр пользователей
SELECT * FROM users;

# Просмотр фидбэков
SELECT * FROM feedback LIMIT 10;
```

### Проверка API

```bash
# Проверка доступности API
curl http://localhost:8000/

# Получение токена
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Проверка информации о пользователе
curl -X GET http://localhost:8000/me \
  -H "Authorization: Bearer $TOKEN"

# Быстрый тест прогноза
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
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
  }'
```

**Подробные примеры curl команд для всех эндпоинтов см. в разделе [🧪 Тестирование API с curl](#-тестирование-api-с-curl)**

---

## 🛠️ Разработка

### Добавление новых эндпоинтов

1. Добавьте функцию в `app/main.py`
2. Добавьте проверку ролей через `require_role()` если нужно
3. Добавьте тесты в `tests/test_api.py`
4. Обновите документацию

### Добавление новых моделей

1. Добавьте ORM модель в `shared/models.py`
2. Создайте миграцию: `alembic revision --autogenerate -m "description"`
3. Примените миграцию: `alembic upgrade head`

### Работа с миграциями

```bash
# Создание миграции
alembic revision --autogenerate -m "description"

# Применение миграции
alembic upgrade head

# Откат миграции
alembic downgrade -1

# Просмотр истории
alembic history
```

---

## 📚 Дополнительная документация

- **[docs/DEPLOY.md](docs/DEPLOY.md)** — подробное руководство по деплою на PythonAnywhere
- **[docs/DOCKER.md](docs/DOCKER.md)** — подробная документация по Docker
- **[docs/SECURITY_IMPROVEMENTS.md](docs/SECURITY_IMPROVEMENTS.md)** — улучшения безопасности
- **[docs/TESTING.md](docs/TESTING.md)** — руководство по тестированию
- **[docs/CI_CD_SETUP.md](docs/CI_CD_SETUP.md)** — быстрый старт CI/CD

---

## 📎 Полезные ссылки

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [SHAP Documentation](https://shap.readthedocs.io/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

## 📝 Лицензия

Дипломный проект. 2025.

---

**Версия**: 2.0.0  
**Последнее обновление**: 2025-01-27

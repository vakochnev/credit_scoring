# 🚀 Руководство по развертыванию Credit Scoring API

Полное руководство по развертыванию системы кредитного скоринга в различных окружениях.

---

## 📋 Содержание

1. [Предварительные требования](#предварительные-требования)
2. [Локальное развертывание](#локальное-развертывание)
3. [Docker развертывание](#docker-развертывание)
4. [Развертывание на PythonAnywhere](#развертывание-на-pythonanywhere)
5. [Production развертывание](#production-развертывание)
6. [Backup и восстановление](#backup-и-восстановление)
7. [Масштабирование](#масштабирование)
8. [Мониторинг и логирование](#мониторинг-и-логирование)
9. [Troubleshooting](#troubleshooting)

---

## 🔧 Предварительные требования

### Системные требования

- **Python**: 3.10 или выше
- **ОС**: Linux, macOS, Windows (для Docker)
- **Память**: минимум 2GB RAM, рекомендуется 4GB+
- **Диск**: минимум 5GB свободного места

### Необходимое ПО

- **Docker** (версия 20.10+) и **Docker Compose** (версия 1.29+)
- **Git** для клонирования репозитория
- **PostgreSQL** (опционально, для production)

---

## 🏠 Локальное развертывание

### Шаг 1: Клонирование репозитория

```bash
git clone <repository-url>
cd credit_scoring
```

### Шаг 2: Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows
```

### Шаг 3: Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 4: Настройка переменных окружения

```bash
cp env.example .env
# Отредактируйте .env и установите:
# - SECRET_KEY (сгенерируйте случайный ключ)
# - ACCESS_TOKEN_EXPIRE_MINUTES
# - REFRESH_TOKEN_EXPIRE_DAYS
```

### Шаг 5: Инициализация базы данных

```bash
# Применение миграций
alembic upgrade head

# Создание пользователей
python scripts/create_users.py
```

### Шаг 6: Обучение модели

```bash
# Запустите backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# В другом терминале обучите модель (требуется авторизация admin)
curl -X POST http://localhost:8000/train-final \
  -H "Authorization: Bearer <access_token>"
```

### Шаг 7: Запуск frontend

```bash
streamlit run frontend/app.py
```

---

## 🐳 Docker развертывание

### Быстрый старт

```bash
# Клонирование и настройка
git clone <repository-url>
cd credit_scoring
cp env.example .env
# Отредактируйте .env

# Сборка и запуск
docker-compose up --build -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f
```

### Команды управления

```bash
# Остановка
docker-compose stop

# Перезапуск
docker-compose restart

# Остановка и удаление контейнеров
docker-compose down

# Пересборка после изменений
docker-compose up --build -d

# Очистка volumes (удалит данные!)
docker-compose down -v
```

### Переменные окружения для Docker

Создайте `.env` файл в корне проекта:

```env
# JWT настройки
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# API настройки
API_BASE_URL=http://localhost:8000
HOST=0.0.0.0
PORT=8000

# Логирование
LOG_LEVEL=INFO
USE_JSON_LOGS=true
```

---

## ☁️ Развертывание на PythonAnywhere

### Шаг 1: Подготовка

1. Создайте аккаунт на [PythonAnywhere](https://www.pythonanywhere.com)
2. Подключитесь по SSH к вашему серверу

### Шаг 2: Клонирование репозитория

```bash
cd ~
git clone <repository-url> credit_scoring
cd credit_scoring
```

### Шаг 3: Настройка окружения

```bash
# Создание виртуального окружения
python3.10 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 4: Настройка переменных окружения

```bash
cp env.example .env
nano .env  # Отредактируйте SECRET_KEY и другие настройки
```

### Шаг 5: Инициализация базы данных

```bash
# Применение миграций
alembic upgrade head

# Создание пользователей
python scripts/create_users.py
```

### Шаг 6: Настройка WSGI

1. Зайдите в раздел **Web** на PythonAnywhere
2. Создайте новое приложение
3. Укажите путь к `wsgi.py` в вашем проекте
4. Настройте статические файлы (если нужно)

### Шаг 7: Автоматическое развертывание

Используйте скрипт `scripts/setup_pythonanywhere.sh`:

```bash
chmod +x scripts/setup_pythonanywhere.sh
./scripts/setup_pythonanywhere.sh
```

---

## 🏭 Production развертывание

### Рекомендации для Production

#### 1. Безопасность

- **SECRET_KEY**: Используйте криптографически стойкий случайный ключ
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- **HTTPS**: Используйте SSL/TLS сертификаты (Let's Encrypt)

- **CORS**: Ограничьте разрешенные домены
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://yourdomain.com"],
      allow_credentials=True,
      allow_methods=["GET", "POST"],
      allow_headers=["*"],
  )
  ```

#### 2. База данных

Для production рекомендуется использовать PostgreSQL:

```python
# В shared/config.py
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost/credit_scoring"
)
```

#### 3. Reverse Proxy (Nginx)

Пример конфигурации Nginx:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 4. Process Manager (systemd)

Создайте сервис `/etc/systemd/system/credit-scoring.service`:

```ini
[Unit]
Description=Credit Scoring API
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/credit_scoring
Environment="PATH=/path/to/credit_scoring/venv/bin"
ExecStart=/path/to/credit_scoring/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl enable credit-scoring
sudo systemctl start credit-scoring
sudo systemctl status credit-scoring
```

#### 5. Мониторинг

- Настройте логирование в централизованную систему (ELK, Splunk)
- Используйте health check endpoints: `/health` и `/health/detailed`
- Настройте алерты на ошибки

---

## 💾 Backup и восстановление

### Автоматический backup

Используйте скрипты из `scripts/`:

```bash
# Backup базы данных
./scripts/backup_db.sh

# Backup с указанием пути
./scripts/backup_db.sh /path/to/backup/directory

# Восстановление из backup
./scripts/restore_db.sh /path/to/backup/file.db
```

### Ручной backup

#### SQLite

```bash
# Простое копирование файла
cp credit_scoring.db backups/credit_scoring_$(date +%Y%m%d_%H%M%S).db

# С использованием SQLite dump
sqlite3 credit_scoring.db .dump > backups/credit_scoring_$(date +%Y%m%d_%H%M%S).sql
```

#### PostgreSQL

```bash
# Создание dump
pg_dump -U user -d credit_scoring > backups/credit_scoring_$(date +%Y%m%d_%H%M%S).sql

# Восстановление
psql -U user -d credit_scoring < backups/credit_scoring_20250101_120000.sql
```

### Backup моделей и данных

```bash
# Создание архива
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  models/ \
  data/ \
  reports/ \
  credit_scoring.db \
  credit_scoring.log

# Восстановление
tar -xzf backup_20250101_120000.tar.gz
```

---

## 📈 Масштабирование

### Горизонтальное масштабирование

#### 1. Docker Swarm

```yaml
# docker-compose.swarm.yml
version: '3.8'

services:
  backend:
    image: credit_scoring_backend:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/credit_scoring
```

#### 2. Kubernetes

Пример `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: credit-scoring-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: credit-scoring-backend
  template:
    metadata:
      labels:
        app: credit-scoring-backend
    spec:
      containers:
      - name: backend
        image: credit_scoring_backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

### Вертикальное масштабирование

- Увеличьте ресурсы сервера (CPU, RAM)
- Используйте более мощные инстансы в облаке
- Настройте кэширование (Redis)

### Оптимизация производительности

1. **Кэширование**:
   ```python
   from fastapi_cache import FastAPICache
   from fastapi_cache.backends.redis import RedisBackend
   
   @app.get("/predict")
   @cache(expire=300)  # Кэш на 5 минут
   def predict_api(...):
       ...
   ```

2. **Async обработка**:
   - Используйте async endpoints для долгих операций
   - Настройте Celery для фоновых задач

3. **База данных**:
   - Используйте connection pooling
   - Настройте индексы для часто запрашиваемых полей

---

## 📊 Мониторинг и логирование

### Health Checks

API предоставляет два health check endpoint:

1. **Базовый**: `GET /health`
   ```json
   {
     "status": "healthy",
     "timestamp": "2025-01-01T12:00:00",
     "version": "2.0.0"
   }
   ```

2. **Детальный**: `GET /health/detailed`
   - Проверяет БД, модели, файловую систему, данные

### Метрики

Endpoint `/metrics` (требует роль admin):

```json
{
  "uptime_seconds": 3600,
  "uptime_human": "1h 0m 0s",
  "requests_total": 1000,
  "requests_by_endpoint": {
    "POST /predict": 500,
    "GET /health": 200
  },
  "errors_total": 5,
  "response_time_avg": 0.123,
  "response_time_min": 0.050,
  "response_time_max": 2.500
}
```

### Логирование

Логи сохраняются в:
- `credit_scoring.log` - все логи
- `errors_credit_scoring.log` - только ошибки

Формат: JSON (если `USE_JSON_LOGS=true`) или обычный текст

### Интеграция с системами мониторинга

#### Prometheus (опционально)

```python
from prometheus_client import Counter, Histogram, generate_latest

requests_total = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')

@app.get("/metrics/prometheus")
def prometheus_metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## 🔧 Troubleshooting

### Проблема: Приложение не запускается

**Решение:**
1. Проверьте логи: `docker-compose logs backend`
2. Убедитесь, что порт 8000 свободен
3. Проверьте переменные окружения
4. Проверьте наличие всех зависимостей

### Проблема: Ошибка "Модель не найдена"

**Решение:**
1. Обучите модель через `/train-final`
2. Проверьте наличие файлов в `models/`
3. Проверьте права доступа к файлам

### Проблема: Ошибка подключения к БД

**Решение:**
1. Проверьте наличие файла БД: `ls -la credit_scoring.db`
2. Примените миграции: `alembic upgrade head`
3. Проверьте права доступа

### Проблема: WeasyPrint не работает в Docker

**Решение:**
1. Убедитесь, что в Dockerfile установлены все зависимости:
   ```dockerfile
   RUN apt-get install -y libcairo2 libpango-1.0-0 ...
   ```
2. Пересоберите образ: `docker-compose build --no-cache backend`

### Проблема: Высокая нагрузка

**Решение:**
1. Увеличьте количество реплик
2. Настройте кэширование
3. Оптимизируйте запросы к БД
4. Используйте load balancer

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте документацию в `README.md`
2. Изучите логи приложения
3. Проверьте health check endpoints
4. Обратитесь к разработчикам

---

## 📝 Чеклист развертывания

- [ ] Установлены все зависимости
- [ ] Настроены переменные окружения
- [ ] Применены миграции БД
- [ ] Созданы пользователи
- [ ] Обучена модель
- [ ] Настроен мониторинг
- [ ] Настроен backup
- [ ] Протестированы все endpoints
- [ ] Настроена безопасность (HTTPS, CORS)
- [ ] Настроен процесс автоматического развертывания

---

**Последнее обновление**: 2025-01-01


# 🚀 Быстрый старт CI/CD

## 📋 Настройка GitHub Actions

### 1. Настройка Secrets

Перейдите в **Settings → Secrets and variables → Actions** вашего репозитория GitHub и добавьте:

#### Для деплоя на PythonAnywhere:

- **`PYTHONANYWHERE_SSH_KEY`**: Приватный SSH ключ
  ```bash
  # Генерация ключа
  ssh-keygen -t ed25519 -C "github-actions@pythonanywhere" -f ~/.ssh/pythonanywhere_key
  
  # Добавьте публичный ключ на PythonAnywhere (Account → SSH keys)
  cat ~/.ssh/pythonanywhere_key.pub
  
  # Добавьте приватный ключ в GitHub Secrets
  cat ~/.ssh/pythonanywhere_key
  ```

- **`PYTHONANYWHERE_USER`**: Ваш username на PythonAnywhere
- **`PYTHONANYWHERE_HOST`**: `ssh.pythonanywhere.com`
- **`PYTHONANYWHERE_PATH`**: `~/credit_scoring` (или ваш путь)

### 2. Проверка работы CI

После настройки:

1. **Создайте Pull Request** или **сделайте push** в `main` или `develop`
2. Проверьте статус в **Actions** вкладке репозитория
3. CI должен запуститься автоматически

### 3. Проверка работы деплоя

После настройки Secrets:

1. **Сделайте push** в `main` ветку
2. Деплой запустится автоматически
3. Проверьте статус в **Actions** вкладке

---

## 🔧 Первоначальная настройка на PythonAnywhere

### 1. Подготовка

```bash
# Установите переменные окружения
export PYTHONANYWHERE_USER="your_username"
export PYTHONANYWHERE_HOST="ssh.pythonanywhere.com"
export PYTHONANYWHERE_PATH="~/credit_scoring"

# Запустите скрипт настройки
chmod +x scripts/setup_pythonanywhere.sh
./scripts/setup_pythonanywhere.sh
```

### 2. Настройка WSGI файла

На PythonAnywhere:

1. **Web → WSGI configuration file**
2. Замените содержимое на:

```python
import sys
import os

project_home = os.path.expanduser('~/credit_scoring')
if project_home not in sys.path:
    sys.path.insert(0, project_home)

activate_this = os.path.expanduser('~/credit_scoring/venv/bin/activate_this.py')
if os.path.exists(activate_this):
    with open(activate_this) as f:
        exec(f.read(), {'__file__': activate_this})

from app.main import app

application = app
```

### 3. Настройка .env файла

На PythonAnywhere создайте `.env` файл:

```bash
cd ~/credit_scoring
nano .env
```

Содержимое:

```env
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
API_BASE_URL=https://your_username.pythonanywhere.com
HOST=0.0.0.0
PORT=8000
```

### 4. Перезагрузка приложения

На PythonAnywhere:

1. **Web → Reload**
2. Нажмите **Reload**

---

## 📊 Структура CI/CD

### CI (Continuous Integration)

**Файл**: `.github/workflows/ci.yml`

**Задачи**:
- ✅ Линтинг (Black, Flake8, Pylint)
- ✅ Проверка формата кода
- ✅ Проверка импортов
- ✅ Проверка миграций Alembic

**Запуск**: При push в `main`/`develop` или создании Pull Request

### CD (Continuous Deployment)

**Файл**: `.github/workflows/deploy.yml`

**Задачи**:
- ✅ Подключение к PythonAnywhere через SSH
- ✅ Обновление кода из git
- ✅ Установка зависимостей
- ✅ Применение миграций
- ✅ Создание пользователей
- ✅ Перезагрузка приложения

**Запуск**: При push в `main` ветку

---

## 🔍 Отладка

### Проблемы с CI

1. Проверьте логи в **Actions** вкладке
2. Убедитесь, что все зависимости в `requirements.txt`
3. Проверьте синтаксис Python файлов

### Проблемы с деплоем

1. Проверьте правильность Secrets
2. Проверьте SSH доступ к PythonAnywhere
3. Проверьте путь к проекту
4. Проверьте логи на PythonAnywhere

---

## 📚 Дополнительная информация

- Подробная документация: [DEPLOY.md](DEPLOY.md)
- Docker документация: [DOCKER.md](DOCKER.md)

---

**Дата обновления**: 2025-01-27


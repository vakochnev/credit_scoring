#!/bin/bash
# Скрипт для первоначальной настройки проекта на PythonAnywhere
# 
# Использование:
#   export PYTHONANYWHERE_USER="your_username"
#   export PYTHONANYWHERE_HOST="ssh.pythonanywhere.com"
#   export PYTHONANYWHERE_PATH="~/credit_scoring"
#   ./scripts/setup_pythonanywhere.sh
#
# Что делает скрипт:
#   1. Клонирует репозиторий (опционально)
#   2. Создает виртуальное окружение
#   3. Устанавливает зависимости
#   4. Инициализирует базу данных
#   5. Создает пользователей
#   6. Создает .env файл

set -e  # Остановка скрипта при любой ошибке

# Цвета для красивого вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # No Color

echo -e "${GREEN}🚀 Настройка проекта на PythonAnywhere${NC}"

# Проверка наличия обязательных переменных окружения
if [ -z "$PYTHONANYWHERE_USER" ]; then
    echo -e "${RED}❌ Ошибка: PYTHONANYWHERE_USER не установлен${NC}"
    echo "Установите переменную: export PYTHONANYWHERE_USER=\"your_username\""
    exit 1
fi

if [ -z "$PYTHONANYWHERE_HOST" ]; then
    echo -e "${RED}❌ Ошибка: PYTHONANYWHERE_HOST не установлен${NC}"
    echo "Установите переменную: export PYTHONANYWHERE_HOST=\"ssh.pythonanywhere.com\""
    exit 1
fi

if [ -z "$PYTHONANYWHERE_PATH" ]; then
    echo -e "${RED}❌ Ошибка: PYTHONANYWHERE_PATH не установлен${NC}"
    echo "Установите переменную: export PYTHONANYWHERE_PATH=\"~/credit_scoring\""
    exit 1
fi

# Путь к проекту на сервере
PROJECT_PATH="$PYTHONANYWHERE_PATH"

# Шаг 1: Клонирование репозитория (опционально)
echo -e "${YELLOW}📦 Клонирование репозитория...${NC}"
echo -e "${YELLOW}⚠️ Укажите URL репозитория (нажмите Enter для пропуска):${NC}"
read -r REPO_URL

if [ -n "$REPO_URL" ]; then
    # Клонирование репозитория, если директория не существует
    ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ~
if [ -d "${PROJECT_PATH}" ]; then
    echo "⚠️ Директория уже существует, пропускаем клонирование"
else
    git clone ${REPO_URL} ${PROJECT_PATH}
    echo "✅ Репозиторий склонирован"
fi
EOF
else
    echo -e "${YELLOW}⚠️ Пропускаем клонирование (используйте существующую директорию)${NC}"
fi

# Шаг 2: Создание виртуального окружения Python
echo -e "${YELLOW}🐍 Создание виртуального окружения...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
if [ -d "venv" ]; then
    echo "⚠️ Виртуальное окружение уже существует"
else
    # Создание виртуального окружения с Python 3.10
    python3.10 -m venv venv
    echo "✅ Виртуальное окружение создано"
fi
EOF

# Шаг 3: Установка Python зависимостей
echo -e "${YELLOW}📥 Установка зависимостей...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
source venv/bin/activate  # Активация виртуального окружения
pip install --upgrade pip  # Обновление pip
pip install -r requirements.txt  # Установка всех зависимостей
echo "✅ Зависимости установлены"
EOF

# Шаг 4: Инициализация базы данных через Alembic миграции
echo -e "${YELLOW}🗄️ Инициализация базы данных...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
source venv/bin/activate
# Применение всех миграций для создания структуры БД
alembic upgrade head
echo "✅ База данных инициализирована"
EOF

# Шаг 5: Создание пользователей системы (admin, analyst, user)
echo -e "${YELLOW}👤 Создание пользователей...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
source venv/bin/activate
# Создание пользователей с разными ролями
python scripts/create_users.py
echo "✅ Пользователи созданы"
EOF

# Шаг 6: Создание .env файла с настройками (если не существует)
echo -e "${YELLOW}📝 Создание .env файла...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
if [ ! -f ".env" ]; then
    # Создание базового .env файла с настройками
    cat > .env << 'ENVEOF'
SECRET_KEY=change-me-in-production  # ВАЖНО: измените на production!
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
API_BASE_URL=https://${PYTHONANYWHERE_USER}.pythonanywhere.com
HOST=0.0.0.0
PORT=8000
ENVEOF
    echo "✅ .env файл создан"
else
    echo "⚠️ .env файл уже существует"
fi
EOF

echo -e "${GREEN}✅ Настройка завершена!${NC}"
echo -e "${YELLOW}📋 Следующие шаги:${NC}"
echo -e "1. Настройте WSGI файл на PythonAnywhere"
echo -e "2. Обновите SECRET_KEY в .env файле"
echo -e "3. Настройте статические файлы (если нужно)"
echo -e "4. Перезагрузите веб-приложение"


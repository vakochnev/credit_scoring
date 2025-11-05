#!/bin/bash
# Скрипт для первоначальной настройки проекта на PythonAnywhere

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Настройка проекта на PythonAnywhere${NC}"

# Проверка переменных окружения
if [ -z "$PYTHONANYWHERE_USER" ]; then
    echo -e "${RED}❌ Ошибка: PYTHONANYWHERE_USER не установлен${NC}"
    exit 1
fi

if [ -z "$PYTHONANYWHERE_HOST" ]; then
    echo -e "${RED}❌ Ошибка: PYTHONANYWHERE_HOST не установлен${NC}"
    exit 1
fi

if [ -z "$PYTHONANYWHERE_PATH" ]; then
    echo -e "${RED}❌ Ошибка: PYTHONANYWHERE_PATH не установлен${NC}"
    exit 1
fi

PROJECT_PATH="$PYTHONANYWHERE_PATH"

echo -e "${YELLOW}📦 Клонирование репозитория...${NC}"
echo -e "${YELLOW}⚠️ Укажите URL репозитория (нажмите Enter для пропуска):${NC}"
read -r REPO_URL

if [ -n "$REPO_URL" ]; then
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

echo -e "${YELLOW}🐍 Создание виртуального окружения...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
if [ -d "venv" ]; then
    echo "⚠️ Виртуальное окружение уже существует"
else
    python3.10 -m venv venv
    echo "✅ Виртуальное окружение создано"
fi
EOF

echo -e "${YELLOW}📥 Установка зависимостей...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Зависимости установлены"
EOF

echo -e "${YELLOW}🗄️ Инициализация базы данных...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
source venv/bin/activate
alembic upgrade head
echo "✅ База данных инициализирована"
EOF

echo -e "${YELLOW}👤 Создание пользователей...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
source venv/bin/activate
python scripts/create_users.py
echo "✅ Пользователи созданы"
EOF

echo -e "${YELLOW}📝 Создание .env файла...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
if [ ! -f ".env" ]; then
    cat > .env << 'ENVEOF'
SECRET_KEY=change-me-in-production
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


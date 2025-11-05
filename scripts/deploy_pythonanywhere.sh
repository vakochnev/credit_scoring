#!/bin/bash
# Скрипт для ручного деплоя на PythonAnywhere

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Начало деплоя на PythonAnywhere${NC}"

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

# Путь к проекту на PythonAnywhere
PROJECT_PATH="$PYTHONANYWHERE_PATH"

echo -e "${YELLOW}📦 Обновление кода из репозитория...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
git fetch origin
git reset --hard origin/main
echo "✅ Код обновлён"
EOF

echo -e "${YELLOW}📥 Установка/обновление зависимостей...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Зависимости установлены"
EOF

echo -e "${YELLOW}🗄️ Применение миграций базы данных...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
source venv/bin/activate
alembic upgrade head || echo "⚠️ Ошибка миграции (может быть ожидаемой)"
EOF

echo -e "${YELLOW}👤 Создание/обновление пользователей...${NC}"
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
cd ${PROJECT_PATH}
source venv/bin/activate
python scripts/create_users.py || echo "⚠️ Ошибка создания пользователей (может быть ожидаемой)"
EOF

echo -e "${YELLOW}🔄 Перезагрузка веб-приложения...${NC}"
# Перезагрузка через touch файла wsgi.py
ssh ${PYTHONANYWHERE_USER}@${PYTHONANYWHERE_HOST} << EOF
touch /var/www/${PYTHONANYWHERE_USER}_pythonanywhere_com_wsgi.py
echo "✅ Приложение перезагружено"
EOF

echo -e "${GREEN}✅ Деплой завершён успешно!${NC}"
echo -e "${GREEN}🌐 Приложение доступно по адресу: https://${PYTHONANYWHERE_USER}.pythonanywhere.com${NC}"


#!/bin/bash
# Скрипт для восстановления базы данных из backup

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Получаем директорию скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Настройки
DB_FILE="${PROJECT_ROOT}/credit_scoring.db"
BACKUP_FILE="${1}"

# Проверка аргументов
if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Ошибка: Укажите путь к backup файлу${NC}"
    echo "Использование: $0 <путь_к_backup>"
    echo "Пример: $0 backups/credit_scoring_20250101_120000.db"
    exit 1
fi

# Проверка существования backup файла
if [ ! -f "$BACKUP_FILE" ]; then
    # Попробуем найти в директории backups
    BACKUP_DIR="${PROJECT_ROOT}/backups"
    if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
        BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
    else
        echo -e "${RED}❌ Ошибка: Backup файл не найден: $BACKUP_FILE${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Это действие перезапишет текущую базу данных!${NC}"
read -p "Вы уверены? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}❌ Восстановление отменено${NC}"
    exit 0
fi

echo -e "${GREEN}🔄 Восстановление базы данных...${NC}"

# Создание backup текущей БД перед восстановлением
if [ -f "$DB_FILE" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="${PROJECT_ROOT}/backups"
    mkdir -p "$BACKUP_DIR"
    PRE_RESTORE_BACKUP="${BACKUP_DIR}/credit_scoring_pre_restore_${TIMESTAMP}.db"
    cp "$DB_FILE" "$PRE_RESTORE_BACKUP"
    echo -e "${GREEN}✅ Создан backup текущей БД: ${PRE_RESTORE_BACKUP}${NC}"
fi

# Распаковка если файл сжат
RESTORE_FILE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${YELLOW}📦 Распаковка backup...${NC}"
    RESTORE_FILE="${BACKUP_FILE%.gz}"
    gunzip -c "$BACKUP_FILE" > "$RESTORE_FILE"
fi

# Восстановление
if cp "$RESTORE_FILE" "$DB_FILE"; then
    echo -e "${GREEN}✅ База данных восстановлена из: ${BACKUP_FILE}${NC}"
    
    # Удаление временного файла
    if [ "$RESTORE_FILE" != "$BACKUP_FILE" ]; then
        rm -f "$RESTORE_FILE"
    fi
    
    # Показываем информацию о восстановленной БД
    if [ -f "$DB_FILE" ]; then
        FILE_SIZE=$(du -h "$DB_FILE" | cut -f1)
        echo -e "${GREEN}📊 Размер восстановленной БД: ${FILE_SIZE}${NC}"
    fi
    
    echo -e "${YELLOW}💡 Рекомендуется:${NC}"
    echo "   1. Проверить приложение: curl http://localhost:8000/health"
    echo "   2. Применить миграции (если нужно): alembic upgrade head"
    echo "   3. Проверить пользователей: python scripts/create_users.py"
    
    exit 0
else
    echo -e "${RED}❌ Ошибка при восстановлении базы данных${NC}"
    exit 1
fi


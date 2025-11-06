#!/bin/bash
# Скрипт для создания backup базы данных

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
BACKUP_DIR="${1:-${PROJECT_ROOT}/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/credit_scoring_${TIMESTAMP}.db"

echo -e "${GREEN}🔄 Создание backup базы данных...${NC}"

# Проверка существования файла БД
if [ ! -f "$DB_FILE" ]; then
    echo -e "${RED}❌ Ошибка: Файл базы данных не найден: $DB_FILE${NC}"
    exit 1
fi

# Создание директории для backup
mkdir -p "$BACKUP_DIR"

# Создание backup
if cp "$DB_FILE" "$BACKUP_FILE"; then
    # Сжатие backup (опционально)
    if command -v gzip &> /dev/null; then
        echo -e "${YELLOW}📦 Сжатие backup...${NC}"
        gzip "$BACKUP_FILE"
        BACKUP_FILE="${BACKUP_FILE}.gz"
        echo -e "${GREEN}✅ Backup создан и сжат: ${BACKUP_FILE}${NC}"
    else
        echo -e "${GREEN}✅ Backup создан: ${BACKUP_FILE}${NC}"
    fi
    
    # Показываем размер файла
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}📊 Размер backup: ${FILE_SIZE}${NC}"
    
    # Удаление старых backup (старше 30 дней)
    echo -e "${YELLOW}🧹 Очистка старых backup (старше 30 дней)...${NC}"
    find "$BACKUP_DIR" -name "credit_scoring_*.db*" -type f -mtime +30 -delete
    echo -e "${GREEN}✅ Очистка завершена${NC}"
    
    exit 0
else
    echo -e "${RED}❌ Ошибка при создании backup${NC}"
    exit 1
fi


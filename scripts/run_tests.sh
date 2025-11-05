#!/bin/bash
# Скрипт для запуска тестов

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Запуск тестов для Credit Scoring API${NC}"

# Проверка установки pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}⚠️ pytest не установлен. Установка...${NC}"
    pip install pytest pytest-cov pytest-asyncio httpx
fi

# Параметры по умолчанию
COVERAGE=true
VERBOSE=false
MARKERS=""

# Обработка аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--marker)
            MARKERS="$2"
            shift 2
            ;;
        *)
            echo "Неизвестный параметр: $1"
            echo "Использование: $0 [--no-coverage] [-v|--verbose] [-m|--marker MARKER]"
            exit 1
            ;;
    esac
done

# Построение команды pytest
CMD="pytest"

if [ "$VERBOSE" = true ]; then
    CMD="$CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    CMD="$CMD --cov=app --cov=shared --cov-report=term-missing --cov-report=html"
fi

if [ -n "$MARKERS" ]; then
    CMD="$CMD -m $MARKERS"
fi

# Запуск тестов
echo -e "${YELLOW}Запуск команды: $CMD${NC}"
eval $CMD

# Вывод результатов
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Тесты пройдены успешно!${NC}"
    if [ "$COVERAGE" = true ]; then
        echo -e "${YELLOW}📊 Отчёт покрытия: htmlcov/index.html${NC}"
    fi
else
    echo -e "${YELLOW}❌ Некоторые тесты не прошли${NC}"
    exit 1
fi


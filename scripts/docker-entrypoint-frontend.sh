#!/bin/bash
# Entrypoint скрипт для frontend контейнера

set -e

echo "🚀 Запуск frontend контейнера..."

# Ожидание готовности backend API
echo "⏳ Ожидание готовности backend API..."
until curl -f http://backend:8000/ > /dev/null 2>&1; do
    echo "⏳ Backend API недоступен, ожидание..."
    sleep 2
done

echo "✅ Backend API готов!"

# Запуск Streamlit
echo "✅ Запуск Streamlit приложения..."
exec streamlit run frontend/app.py --server.port=8501 --server.address=0.0.0.0


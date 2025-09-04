Рекомендации: 

Не ЗАБУДЬ уладить следующее:
https://chat.qwen.ai/c/3875011f-8a1c-4df3-a0b7-841a609cd968
code.txt

Конец для удаления
===

# Ансамблевая система кредитного скоринга с интерпретацией решений (SHAP) и генерацией PDF-отчётов

## Возможности
- Обучение ансамбля: RF + XGBoost + CatBoost
- AutoML с PyCaret
- Интерпретация с SHAP
- Генерация PDF-отчёта

## Запуск
```bash

uvicorn app.main:app --reload
streamlit run frontend/app.py

Как использовать:

    Запусти FastAPI:
    bash
    cd app && uvicorn main:app --reload
    
    Запусти Streamlit:
    bash
    cd frontend && streamlit run app.py
    
    Введи данные → нажми:

🔮 Прогнозировать и объяснить → увидишь SHAP

📥 Скачать отчёт в PDF → файл сохранится в reports/


===
Backend (FastAPI):

    cd app
    #uvicorn main:app --reload
    uvicorn main:app --host 127.0.0.1 --port 8000
    
    Для отладки снять коментарий с 2-х последних строк в main.py:
    if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=False # Параметр необходим для отладки, потом убрать
    )

    script: (свой путь)/home/wka/code/диплом/code/credit_scoring/app/myapp.py !!!
    Script parametrs - пусто
    Working directory: (свой путь)/home/wka/code/диплом/code/credit_scoring/app/ !!!

Frontend (Streamlit):

    cd frontend
    streamlit run app.py


Безопасность приложения:
Работа с учетными записями пользователя.

    В терминале запустим команду:
    python init_db.py

    Появиться файл users.db с таблицей users
    Пользователь admin с паролем password123

    Пользователи теперь хранятся в SQLite
    Авторизация реализована через HTTP Basic Auth
    Пароли хранятся в хэшированном виде
    Можно легко добавлять новых пользователей через код или внешний интерфейс

✅ Что ты получишь:
    
    REST API для всех этапов предобработки и моделирования.
    Интеграция с ансамблевыми методами: Bagging, Boosting, Stacking, Blending.
    Автоматическое машинное обучение через PyCaret.
    Интерактивный UI для прогнозирования.

📌 Дополнительно (для диплома):

    Можно добавить графики важности признаков (SHAP, feature_importances_).
    Сохранять лучшие модели (joblib) и загружать их в API.
    Построить отчеты (classification_report, ROC AUC, confusion matrix).

Визуализации результатов

    1️⃣ 📚 Документация Swagger
    FastAPI автоматически генерирует документацию через Swagger и ReDoc.

    После запуска сервера:

    Swagger: http://localhost:8000/docs
    ReDoc: http://localhost:8000/redoc
    
    Ничего дополнительно писать не нужно , она уже доступна по умолчанию!

▶️ Запуск тестов:

    pytest tests/


🚀 Предположим:
    
    Сервер запущен на: http://localhost:8000
    Все данные находятся в файле data/credit_risk_dataset.csv
    Переменная df загружена и доступна глобально

📌 1. Root — Проверка работы сервера

    curl -u admin:password123 -X GET "http://localhost:8000"

    Ожидаемый ответ: json
    {"message": "Добро пожаловать в Credit Scoring API"}

🧹 2. Обработка выбросов — /outliers
    
    curl -u admin:password123 -X POST "http://localhost:8000/outliers"
    
    Ожидаемый ответ: json
    {
      "message": "Обработанные выбросы",
      "count_before": 32581,
      "count_after": 29381
    }

🔧 3. Разработка фичей (Feature Engineering) — /feature-engineering

    curl -u admin:password123 -X POST "http://localhost:8000/feature-engineering"
    
    Ожидаемый ответ: json
    {
      "message": "Разработка фичей выполнена",
      "features": ["person_age", "person_income", ...]
    }

📊 4. Предобработка данных — /preprocessing

    curl -u admin:password123 -X POST "http://localhost:8000/preprocessing"
    
    Ожидаемый ответ: json
    {
      "message": "Предварительная обработка данных",
      "shape": [950, 22]
    }

🤖 5. Обучение моделей — /train-models

    curl -u admin:password123 -X POST "http://localhost:8000/train-models"
    
    Ожидаемый ответ (пример): json
    {
      "results": {
        "RandomForest": 0.89,
        "XGBoost": 0.91,
        "LightGBM": 0.92,
        "CatBoost": 0.93,
        "Stacking": 0.94,
        "Blending": 0.93
      }
    }

⚙️ 6. Подбор гиперпараметров — /tune-hyperparameters
    
    curl -u admin:password123 -X POST "http://localhost:8000/tune-hyperparameters"
    
    Ожидаемый ответ: json
    {
      "best_params": {
        "n_estimators": 100,
        "max_depth": 5
      }
    }

✅ 7. Обучение финальной модели — /train-final

    curl -u admin:password123 -X POST "http://localhost:8000/train-final"
    
    Ожидаемый ответ: json
    {
      "model": "RandomForest",
      "accuracy": 0.94
    }

🧠 8. AutoML с PyCaret — /run-automl

    curl -u admin:password123 -X POST "http://localhost:8000/run-automl"

    Ожидаемый ответ: json
    {
      "automl_result": {
        "best_model": "XGBoost"
      }
    }

📈 9. Прогнозирование — /predict
    
    Пример запроса:
    curl -u admin:password123 -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
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

    Ожидаемый ответ: json
    {
      "prediction": 0
    }
    
    0 = клиент вероятно погасит кредит
    1 = высокий риск дефолта 

    Примеры ошибок (автоматически от FastAPI)
    Если отправить:

    json
    {
        "person_age": 15,
        ...
    }

    Получишь:
    json
    {
      "detail": [
        {
          "loc": ["body", "person_age"],
          "msg": "Возраст должен быть от 18 до 100 лет",
          "type": "value_error"
        }
      ]
    }

    Ошибочный запрос (недопустимый loan_grade):
    bash
    curl -u admin:password123 -X POST http://localhost:8000/predict \
         -H "Content-Type: application/json" \
        -d '{
               "person_age": 135,
               "person_income": 75000,
               "person_home_ownership": "RENT",
               "person_emp_length": 5.0,
               "loan_intent": "DEBTCONSOLIDATION",
               "loan_grade": "X",
               "loan_amnt": 20000,
               "loan_int_rate": 9.5,
               "loan_percent_income": 0.27,
               "cb_person_default_on_file": "N",
               "cb_person_cred_hist_length": 4
             }'
    Получишь:
    json
    {
      "detail": [
        {
          "loc": ["body", "loan_grade"],
          "msg": "value is not a valid enumeration member; permitted: 'A', 'B', 'C', 'D', 'E', 'F', 'G'",
          "type": "type_error.enum"
        }
      ]
    }

📄 10. Генерация PDF-отчета (если реализован) — /report

    curl -u admin:password123 -X POST "http://localhost:8000/report" \
        -H "Content-Type: application/json" \
        -d '{
               "person_age": 35,
               "person_income": 75000,
               "person_home_ownership": "RENT",
               "person_emp_length": 5.0,
               "loan_intent": "DEBTCONSOLIDATION",
               "loan_grade": "X",
               "loan_amnt": 20000,
               "loan_int_rate": 9.5,
               "loan_percent_income": 0.27,
               "cb_person_default_on_file": "N",
               "cb_person_cred_hist_length": 4
             }'

    Ожидаемый ответ: json
    {
      "report_path": "reports/model_comparison_report.pdf"
    }

    11. Интерпретация ответа - /explain

  
    curl -u admin:password123 -X POST http://localhost:8000/explain \
         -H "Content-Type: application/json" \
         -d '{
               "person_age": 45,
               "person_income": 120000,
               "person_home_ownership": "OWN",
               "person_emp_length": 15.0,
               "loan_intent": "HOMEIMPROVEMENT",
               "loan_grade": "A",
               "loan_amnt": 15000,
               "loan_int_rate": 6.0,
               "loan_percent_income": 0.1,
               "cb_person_default_on_file": "N",
               "cb_person_cred_hist_length": 10
             }'

    Ожидаемый ответ:
    json
    {
      "prediction": 0,
      "status": "repaid",
      "decision": "approve",
      "probability_default": 0.12,
      "probability_repaid": 0.88,
      "explanation": {
        "base_value": 0.45,
        "shap_values": [
          {"feature": "person_income", "value": -0.31},
          {"feature": "loan_grade_A", "value": -0.25},
          {"feature": "loan_percent_income", "value": 0.18},
          {"feature": "cb_person_default_on_file_N", "value": -0.15},
          {"feature": "person_home_ownership_OWN", "value": -0.12}
        ],
        "summary": [
          "person_income: ↓ риск (-0.310)",
          "loan_grade_A: ↓ риск (-0.250)",
          "loan_percent_income: ↑ риск (+0.180)",
          "cb_person_default_on_file_N: ↓ риск (-0.150)",
          "person_home_ownership_OWN: ↓ риск (-0.120)"
        ]
    }

    12. Обратная связь (feedback)
    
    curl -u admin:password123 -X POST http://localhost:8000/feedback \
         -H "Content-Type: application/json" \
         -d '{
               "person_age": 45,
               "person_income": 120000,
               "person_home_ownership": "OWN",
               "person_emp_length": 15.0,
               "loan_intent": "HOMEIMPROVEMENT",
               "loan_grade": "A",
               "loan_amnt": 15000,
               "loan_int_rate": 6.0,
               "loan_percent_income": 0.1,
               "cb_person_default_on_file": "N",
               "cb_person_cred_hist_length": 10
             }', "actual_status": "default"

✅ Как тестировать?
    
    Запусти сервер:
    
    cd app && uvicorn main:app --reload
    Открой терминал и вставь нужный curl-запрос выше
    Убедись, что все шаги выполняются по порядку (например, предобработка после очистки от выбросов)

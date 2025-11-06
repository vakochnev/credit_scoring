# frontend/app.py
"""
Frontend-интерфейс для системы кредитного скоринга

Модуль реализует веб-интерфейс на основе Streamlit для:
- Ввода данных заемщика
- Прогнозирования и объяснения решения
- Генерации PDF-отчётов
- Сравнения моделей
- Сбора обратной связи
- Дообучения модели

Архитектура:
- Frontend: Streamlit
- Backend: FastAPI (через HTTP-запросы)
- Интерпретируемость: SHAP
- Отчёты: WeasyPrint + Jinja2

Автор: [Кочнева Арина]
Год: 2025
"""

import os
import sys
from pathlib import Path
import streamlit as st
import requests
import pandas as pd
import joblib

# --- 🧭 Настройка пути к корню проекта ---
# Добавляет корень проекта в sys.path, чтобы можно было импортировать модули
# из app/, shared/, services/ без ошибок.

# frontend/.. → credit_scoring/
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


# --- 🔗 Импорт компонентов системы ---
from shared.config import (
    API_BASE_URL, REPORT_PATH, BACKGROUND_DATA_PATH, ENSEMBLE_MODEL_PATH
)


# --- 🖼️ Настройка страницы Streamlit ---
# Конфигурация интерфейса:
# - Заголовок: "Кредитный скоринг"
# - Макет: широкий (wide)
# - Иконка: 💳
st.set_page_config(
    page_title="Кредитный скоринг",
    layout="wide",
    page_icon="💳"
)


# --- 🔐 Механизм авторизации с JWT ---
def check_password():
    """
    Реализует форму входа с получением JWT токена.

    Использует st.session_state для хранения статуса аутентификации и токена.
    При успешном входе получает JWT токен через /login и сохраняет его.

    Returns:
        bool: True — пользователь авторизован, False — нет
    """

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.subheader("🔐 Вход в систему")
        username = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        if st.button("Войти"):
            # Получаем JWT токен через /login
            try:
                response = requests.post(
                    f"{API_BASE_URL}/login",
                    json={"username": username, "password": password}
                )
                if response.status_code == 200:
                    token_data = response.json()
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.access_token = token_data["access_token"]
                    st.session_state.refresh_token = token_data["refresh_token"]
                    st.rerun()
                else:
                    error_detail = response.json().get("detail", "Неизвестная ошибка")
                    st.error(f"Неверный логин или пароль: {error_detail}")
            except Exception as e:
                st.error("Не удалось подключиться к API")
                st.exception(e)
        return False
    return True


def get_auth_headers():
    """
    Возвращает заголовки с JWT токеном для авторизации.

    Returns:
        dict: Заголовки с Authorization Bearer токеном
    """
    if "access_token" in st.session_state:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}


def refresh_access_token():
    """
    Обновляет access токен используя refresh токен.

    Returns:
        bool: True если токен успешно обновлён, False иначе
    """
    if "refresh_token" not in st.session_state:
        return False
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/refresh",
            json={"refresh_token": st.session_state.refresh_token}
        )
        if response.status_code == 200:
            token_data = response.json()
            st.session_state.access_token = token_data["access_token"]
            st.session_state.refresh_token = token_data["refresh_token"]
            return True
    except Exception:
        pass
    
    # Если обновление не удалось, требуется повторный вход
    st.session_state.authenticated = False
    if "access_token" in st.session_state:
        del st.session_state.access_token
    if "refresh_token" in st.session_state:
        del st.session_state.refresh_token
    return False

# Проверка перед отображением интерфейса
if not check_password():
    st.stop()


# --- 🌐 API-хелперы (вспомогательные функции для запросов) ---
def explain_request(data):
    """
    Отправляет POST-запрос к /explain для получения прогноза и
    объяснения.

    Args:
        data (dict): Данные заемщика

    Returns:
        requests.Response: Ответ от FastAPI
    """
    response = requests.post(
        url=f"{API_BASE_URL}/explain",
        json=data,
        headers=get_auth_headers()
    )
    # Если получили 401, пытаемся обновить токен
    if response.status_code == 401:
        if refresh_access_token():
            response = requests.post(
                url=f"{API_BASE_URL}/explain",
                json=data,
                headers=get_auth_headers()
            )
    return response


def generate_report(data):
    """
    Генерирует PDF-отчёт через /report.

    Args:
        data (dict): Данные заемщика

    Returns:
        requests.Response: Ответ с путём к PDF
    """
    response = requests.post(
        url=f"{API_BASE_URL}/report",
        json=data,
        headers=get_auth_headers()
    )
    if response.status_code == 401:
        if refresh_access_token():
            response = requests.post(
                url=f"{API_BASE_URL}/report",
                json=data,
                headers=get_auth_headers()
            )
    return response


def save_feedback(feedback_data):
    response = requests.post(
        url=f"{API_BASE_URL}/feedback",
        json=feedback_data,
        headers=get_auth_headers()
    )
    if response.status_code == 401:
        if refresh_access_token():
            response = requests.post(
                url=f"{API_BASE_URL}/feedback",
                json=feedback_data,
                headers=get_auth_headers()
            )
    return response


def compare_models():
    """
    Запрашивает сравнение моделей через /compare.

    Returns:
        requests.Response: Список моделей и их метрик
    """
    response = requests.get(
        url=f"{API_BASE_URL}/compare",
        headers=get_auth_headers()
    )
    if response.status_code == 401:
        if refresh_access_token():
            response = requests.get(
                url=f"{API_BASE_URL}/compare",
                headers=get_auth_headers()
            )
    return response


def generate_comparison_report():
    """
    Генерирует PDF-отчёт по сравнению моделей.

    Returns:
        requests.Response: Путь к PDF
    """
    response = requests.post(
        url=f"{API_BASE_URL}/generate-comparison-report",
        headers=get_auth_headers()
    )
    if response.status_code == 401:
        if refresh_access_token():
            response = requests.post(
                url=f"{API_BASE_URL}/generate-comparison-report",
                headers=get_auth_headers()
            )
    return response


def retrain_model():
    """
    Запрашивает дообучение модели на собранных фидбэках через /retrain.
    
    Дообучение выполняется на основе обратной связи, собранной через
    эндпоинт /feedback. Требует роль admin или analyst.
    
    Returns:
        requests.Response: Результат дообучения (точность на фидбэках)
    """
    response = requests.post(
        url=f"{API_BASE_URL}/retrain",
        headers=get_auth_headers()
    )
    if response.status_code == 401:
        if refresh_access_token():
            response = requests.post(
                url=f"{API_BASE_URL}/retrain",
                headers=get_auth_headers()
            )
    return response


def train_ensemble():
    """
    Запрашивает обучение ансамблевой модели с нуля через /train-final.
    
    Обучает VotingClassifier (RandomForest + XGBoost + CatBoost) на полном
    датасете. Требует роль admin.
    
    Returns:
        requests.Response: Результат обучения (модель, точность)
    """
    response = requests.post(
        url=f"{API_BASE_URL}/train-final",
        headers=get_auth_headers()
    )
    if response.status_code == 401:
        if refresh_access_token():
            response = requests.post(
                url=f"{API_BASE_URL}/train-final",
                headers=get_auth_headers()
            )
    return response


# --- 🧠 Загрузка background_data для SHAP ---
@st.cache_resource
def load_background_data():
    """
    Загружает background_data.pkl для построения SHAP-графиков.

    Кэшируется, чтобы не загружать повторно при каждом действии.

    Returns:
        pd.DataFrame or None: Фоновые данные или None при ошибке
    """
    try:
        return joblib.load(BACKGROUND_DATA_PATH)
    except Exception as e:
        st.warning("Не удалось загрузить background_data.pkl")
        return None


background_data = load_background_data()


# --- 📑 Основной интерфейс: вкладки ---
# Определяем доступные вкладки в зависимости от роли пользователя
tabs_labels = [
    "🔍 Прогноз и объяснение",
    "📊 Сравнение моделей",
    "🔄 Дообучение"
]

# Получаем роль пользователя для определения доступности админ-панели
user_role = None
try:
    response = requests.get(
        f"{API_BASE_URL}/me",
        headers=get_auth_headers()
    )
    if response.status_code == 200:
        user_info = response.json()
        user_role = user_info.get("role")
        # Добавляем админ-панель для администраторов
        if user_role == "admin":
            tabs_labels.append("🛡️ Админ-панель")
except Exception:
    pass  # Если не удалось получить роль, просто не показываем админ-панель

tabs = st.tabs(tabs_labels)

tab1 = tabs[0]
tab2 = tabs[1]
tab3 = tabs[2]
tab4 = tabs[3] if len(tabs) > 3 else None

# === ВКЛАДКА 1: Прогноз и объяснение ===
# Основная вкладка для ввода данных заемщика и получения прогноза
with tab1:
    st.subheader("Введите данные заемщика")

    # Разделение формы на две колонки для удобства
    col1, col2 = st.columns(2)
    
    # Левая колонка: персональные данные заемщика
    with col1:
        person_age = st.number_input("Возраст", 18, 100, 35)  # Минимум 18, максимум 100, по умолчанию 35
        person_income = st.number_input(
            "Доход", 10_000, 1_000_000, 75_000  # Доход в рублях
        )
        person_home_ownership = st.selectbox(
            "Собственность",
            ["RENT", "OWN", "MORTGAGE", "OTHER"]  # Аренда, Собственность, Ипотека, Другое
        )
        person_emp_length = st.number_input(
            "Стаж (лет)", 0.0, 50.0, 5.0  # Трудовой стаж
        )
        loan_intent = st.selectbox("Цель кредита", [
            "DEBTCONSOLIDATION", "EDUCATION", "HOMEIMPROVEMENT",
            "MEDICAL", "PERSONAL", "VENTURE"
        ])  # Консолидация долгов, Образование, Ремонт, Медицина, Личное, Бизнес

    # Правая колонка: параметры кредита
    with col2:
        loan_grade = st.selectbox(
            "Кредитный рейтинг",
            ["A", "B", "C", "D", "E", "F", "G"]  # От лучшего (A) до худшего (G)
        )
        loan_amnt = st.number_input(
            "Сумма кредита", 1_000, 100_000, 20_000  # Сумма в рублях
        )
        loan_int_rate = st.number_input(
            "Процентная ставка", 0.0, 100.0, 9.5  # Годовая процентная ставка
        )
        loan_percent_income = st.slider(
            "Процент дохода", 0.0, 1.0, 0.27  # Доля дохода на погашение кредита (0-100%)
        )
        cb_person_default_on_file = st.selectbox(
            "Был ли дефолт", ["Y", "N"]  # Y - был дефолт, N - не было
        )
        cb_person_cred_hist_length = st.number_input(
            "Длина кредитной истории", 0, 50, 4  # Количество лет кредитной истории
        )

    # Формирование словаря с данными для отправки в API
    data = {
        "person_age": person_age,
        "person_income": person_income,
        "person_home_ownership": person_home_ownership,
        "person_emp_length": person_emp_length,
        "loan_intent": loan_intent,
        "loan_grade": loan_grade,
        "loan_amnt": loan_amnt,
        "loan_int_rate": loan_int_rate,
        "loan_percent_income": loan_percent_income,
        "cb_person_default_on_file": cb_person_default_on_file,
        "cb_person_cred_hist_length": cb_person_cred_hist_length
    }

    # --- 🔮 Прогноз и объяснение ---
    # Кнопка для запуска прогноза и получения объяснения решения
    # key="predict_button" предотвращает конфликты при переключении вкладок
    if st.button("🔮 Прогнозировать и объяснить", key="predict_button"):
        with st.spinner("Выполняется анализ..."):
            try:
                response = explain_request(data)
                if response.status_code == 200:
                    result = response.json()

                    # Сохраняем результат в session_state для использования в других секциях
                    # (например, для генерации PDF или сохранения feedback)
                    st.session_state['prediction_result'] = result
                    st.session_state['input_data'] = data

                    # Сбрасываем предыдущий PDF, если он был сгенерирован
                    # Это нужно, чтобы при новом прогнозе старый PDF не отображался
                    if 'pdf_generated' in st.session_state:
                        del st.session_state['pdf_generated']
                    if 'report_path' in st.session_state:
                        del st.session_state['report_path']

                    # Отображение результата прогноза
                    # Преобразуем коды решения в читаемый формат
                    decision = "✅ ОДОБРЕНО" if result["decision"] == "approve" else "❌ ОТКАЗ"
                    status = "Клиент вернёт кредит" if result["status"] == "repaid" else "Риск дефолта"
                    prob = result["probability_repaid"]

                    # Вывод решения, статуса и вероятности
                    st.success(f"📌 Решение: **{decision}**")
                    st.info(f"📊 Статус: {status}")
                    st.metric("Вероятность возврата", f"{prob:.1%}")

                    # Текстовое объяснение решения на основе SHAP значений
                    st.subheader("📝 Объяснение решения")
                    # Заменяем стрелки на эмодзи для лучшей читаемости
                    for line in result["explanation"]["summary"]:
                        st.markdown(f"- {line.replace('↑ риск', '⬆️ повышает риск').replace('↓ риск', '⬇️ понижает риск')}")

                    # График SHAP waterfall (если есть)
                    # Показывает вклад каждого признака в итоговое решение
                    if "shap_image_base64" in result["explanation"]:
                        st.image(
                            f"data:image/png;base64,{result['explanation']['shap_image_base64']}",
                            caption="Вклад признаков (SHAP)",
                            width=1300
                        )

                else:
                    st.error(
                        f"❌ Ошибка API: {response.json().get('detail', 'Неизвестная ошибка')}"
                    )

            except Exception as e:
                st.error("⚠️ Не удалось подключиться к API")
                st.exception(e)

    # --- 📄 Генерация PDF-отчёта ---
    # Секция для генерации и скачивания PDF отчёта с полным объяснением решения
    st.subheader("📄 Скачать PDF-отчёт")
    # Проверяем, что прогноз был выполнен (результат есть в session_state)
    if 'prediction_result' in st.session_state:
        # Кнопка для генерации PDF отчёта на сервере
        if st.button("📥 Сформировать PDF", key="generate_pdf_button"):
            with st.spinner("Генерация PDF..."):
                try:
                    # Используем сохраненные данные для генерации отчёта
                    input_data = st.session_state['input_data']
                    # Отправляем запрос на генерацию PDF
                    response = generate_report(input_data)
                    if response.status_code == 200:
                        report_path = response.json()["report_path"]
                        # Сохраняем флаг и путь для последующего скачивания
                        st.session_state['pdf_generated'] = True
                        st.session_state['report_path'] = report_path
                        st.success(f"✅ Отчёт сформирован: `{report_path}`")
                    else:
                        st.error(f"❌ Ошибка: {response.json().get('detail')}")
                except Exception as e:
                    st.error("⚠️ Не удалось сгенерировать отчёт")
                    st.exception(e)

        # Кнопка скачивания (отображается только если отчёт был сформирован)
        if 'pdf_generated' in st.session_state and 'report_path' in st.session_state:
            report_path = st.session_state['report_path']
            # Скачивание файла через API endpoint /download/{filename}
            # Это безопаснее, чем прямой доступ к файловой системе
            try:
                download_response = requests.get(
                    f"{API_BASE_URL}/download/explanation_report.pdf",
                    headers=get_auth_headers()
                )
                if download_response.status_code == 200:
                    st.download_button(
                        "⬇️ Скачать PDF",
                        download_response.content,
                        file_name="credit_report.pdf",
                        mime="application/pdf",
                        key="download_pdf_button"
                    )
                elif download_response.status_code == 401:
                    # Попробуем обновить токен и повторить запрос
                    if refresh_access_token():
                        download_response = requests.get(
                            f"{API_BASE_URL}/download/explanation_report.pdf",
                            headers=get_auth_headers()
                        )
                        if download_response.status_code == 200:
                            st.download_button(
                                "⬇️ Скачать PDF",
                                download_response.content,
                                file_name="credit_report.pdf",
                                mime="application/pdf",
                                key="download_pdf_button"
                            )
                        else:
                            error_detail = download_response.json().get("detail", "Неизвестная ошибка")
                            st.error(f"❌ Ошибка скачивания: {error_detail}")
                    else:
                        st.error("❌ Не удалось авторизоваться. Перезайдите в систему.")
                else:
                    error_detail = download_response.json().get("detail", "Неизвестная ошибка") if download_response.headers.get("content-type", "").startswith("application/json") else download_response.text
                    st.error(f"❌ Ошибка скачивания (код {download_response.status_code}): {error_detail}")
            except requests.exceptions.RequestException as download_error:
                st.error(f"❌ Ошибка подключения к API: {str(download_error)}")
            except Exception as download_error:
                st.error(f"❌ Не удалось скачать файл: {str(download_error)}")
                st.exception(download_error)
    else:
        st.info("Сначала выполните прогноз, чтобы сформировать PDF.")

    # --- 📩 Обратная связь ---
    # Секция для сохранения фактического результата кредита
    # Используется для последующего дообучения модели на реальных данных
    st.markdown("---")
    st.subheader("📩 Обратная связь")

    # Проверяем, что прогноз был выполнен
    if 'prediction_result' in st.session_state:
        # Радио-кнопки для выбора фактического статуса кредита
        # 0 - клиент вернул кредит, 1 - клиент не вернул (дефолт)
        actual_status = st.radio(
            "Фактический статус кредита (по итогам выплаты):",
            options=[("Клиент вернул", 0), ("Клиент не вернул", 1)],
            format_func=lambda x: x[0]  # Отображаем только текст, но сохраняем код
        )

        # Кнопка для сохранения обратной связи
        if st.button("✅ Сохранить обратную связь", key="save_feedback_button"):
            # Получаем сохраненные результаты прогноза и входные данные
            result = st.session_state['prediction_result']
            input_data = st.session_state['input_data']

            # Формируем данные для отправки: входные данные + предсказание + факт
            feedback_data = input_data.copy()
            feedback_data["predicted_status"] = result["prediction"]  # Что предсказала модель
            feedback_data["actual_status"] = actual_status[1] if isinstance(actual_status, tuple) else actual_status  # Что произошло на самом деле
            feedback_data["probability_repaid"] = result.get("probability_repaid")  # Вероятность возврата
            feedback_data["probability_default"] = result.get("probability_default")  # Вероятность дефолта

            try:
                # Отправляем feedback на сервер для сохранения в БД
                response = save_feedback(feedback_data)
                if response.status_code == 200:
                    st.success(
                        "✅ Обратная связь сохранена для дообучения модели"
                    )
                else:
                    st.error(
                        f"❌ Ошибка: {response.json().get('detail', 'Неизвестная ошибка')}"
                    )
            except Exception as e:
                st.error("⚠️ Не удалось отправить обратную связь")
                st.exception(e)
    else:
        st.info(
            "Сначала выполните прогноз, чтобы оставить обратную связь."
        )


# === ВКЛАДКА 2: Сравнение моделей ===
# Вкладка для сравнения производительности различных ML моделей
with tab2:
    st.subheader("Сравнение моделей")

    # Кнопка для обновления сравнения моделей
    # При нажатии модели обучаются заново и сравниваются их метрики
    if st.button("🔄 Обновить сравнение", key="compare_models_button"):
        with st.spinner("Загрузка метрик..."):
            try:
                # Запрос к API для получения сравнения моделей
                response = compare_models()
                if response.status_code == 200:
                    data = response.json()["models"]
                    # Преобразуем в DataFrame для удобного отображения
                    df = pd.DataFrame(data)

                    # Отображаем таблицу с метриками моделей
                    # Форматируем accuracy и auc до 3 знаков после запятой
                    st.dataframe(
                        df.style.format({"accuracy": "{:.3f}", "auc": "{:.3f}"}),
                        #use_container_width=True
                    )

                    # Визуализация метрик в виде барчартов
                    col1, col2 = st.columns(2)
                    with col1:
                        # График точности (accuracy) для каждой модели
                        st.bar_chart(df.set_index("model")["accuracy"])
                    with col2:
                        # График ROC-AUC для каждой модели
                        st.bar_chart(df.set_index("model")["auc"])

                else:
                    st.warning("Метрики недоступны. Обучите модели сначала.")
            except Exception as e:
                st.error("⚠️ Не удалось загрузить данные")
                st.exception(e)

    # --- 📄 Генерация PDF-отчёта по сравнению моделей ---
    st.markdown("---")
    st.subheader("📄 Отчёт по сравнению моделей")

    if st.button("📥 Сформировать PDF-отчёт по моделям", key="generate_comparison_report_button"):
        with st.spinner("Генерация отчёта..."):
            try:
                response = generate_comparison_report()
                if response.status_code == 200:
                    report_path = response.json()["report_path"]
                    st.success(f"✅ Отчёт сгенерирован: `{report_path}`")
                    
                    # Скачивание файла через API endpoint
                    try:
                        download_response = requests.get(
                            f"{API_BASE_URL}/download/model_comparison_report.pdf",
                            headers=get_auth_headers()
                        )
                        if download_response.status_code == 200:
                            st.download_button(
                                "⬇️ Скачать PDF",
                                download_response.content,
                                file_name="model_comparison_report.pdf",
                                mime="application/pdf"
                            )
                        elif download_response.status_code == 401:
                            # Попробуем обновить токен и повторить запрос
                            if refresh_access_token():
                                download_response = requests.get(
                                    f"{API_BASE_URL}/download/model_comparison_report.pdf",
                                    headers=get_auth_headers()
                                )
                                if download_response.status_code == 200:
                                    st.download_button(
                                        "⬇️ Скачать PDF",
                                        download_response.content,
                                        file_name="model_comparison_report.pdf",
                                        mime="application/pdf"
                                    )
                                else:
                                    error_detail = download_response.json().get("detail", "Неизвестная ошибка")
                                    st.error(f"❌ Ошибка скачивания: {error_detail}")
                            else:
                                st.error("❌ Не удалось авторизоваться. Перезайдите в систему.")
                        else:
                            error_detail = download_response.json().get("detail", "Неизвестная ошибка") if download_response.headers.get("content-type", "").startswith("application/json") else download_response.text
                            st.error(f"❌ Ошибка скачивания (код {download_response.status_code}): {error_detail}")
                    except requests.exceptions.RequestException as download_error:
                        st.error(f"❌ Ошибка подключения к API: {str(download_error)}")
                    except Exception as download_error:
                        st.error(f"❌ Не удалось скачать файл: {str(download_error)}")
                        st.exception(download_error)
                else:
                    st.error(
                        f"❌ Ошибка: {response.json().get('detail')}"
                    )
            except Exception as e:
                st.error(
                    "⚠️ Не удалось сгенерировать отчёт"
                )
                st.exception(e)


# === ВКЛАДКА 3: Дообучение ===
# Вкладка для обучения и дообучения ML моделей
with tab3:
    st.subheader("🔄 Дообучение модели на обратной связи")

    # --- Обучение ансамбля с нуля ---
    # Обучает VotingClassifier (RandomForest + XGBoost + CatBoost) на полном датасете
    # Требует роль admin
    if st.button("🎓 Обучить ансамбль", key="train_ensemble_button"):
        with st.spinner("Обучение..."):
            try:
                response = train_ensemble()
                if response.status_code == 200:
                    result = response.json()
                    st.success(
                        f"✅ Модель обучена: {result['model']}, "
                        f"точность: {result['accuracy']:.3f}"
                    )
                else:
                    error_detail = response.json().get("detail", "Неизвестная ошибка")
                    st.error(f"❌ Ошибка обучения: {error_detail}")
                    if response.status_code == 403:
                        st.warning("⚠️ Недостаточно прав. Требуется роль 'admin'.")
            except Exception as e:
                st.error("⚠️ Не удалось обучить модель")
                st.exception(e)
    
    # Добавляем визуальный разделитель между кнопками
    st.markdown("---")

    # --- Дообучение на фидбэках ---
    # Дообучает существующую модель на собранных обратных связях (feedback)
    # Использует данные, сохраненные через эндпоинт /feedback
    # Требует роль admin или analyst
    if st.button("🚀 Дообучить на фидбэках", key="retrain_model_button"):
        with st.spinner("Дообучение..."):
            try:
                response = retrain_model()
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Модель дообучена!")
                    # Отображаем полный JSON результат для детального просмотра
                    st.json(result)
                else:
                    error_detail = response.json().get("detail", "Неизвестная ошибка")
                    st.error(f"❌ Ошибка: {error_detail}")
                    if response.status_code == 403:
                        st.warning("⚠️ Недостаточно прав. Требуется роль 'admin' или 'analyst'.")
            except Exception as e:
                st.error("⚠️ Не удалось дообучить")
                st.exception(e)

# === ВКЛАДКА 4: Админ-панель ===
if tab4 is not None:
    with tab4:
        st.subheader("🛡️ Админ-панель: Обратная связь")
        
        # Функция для загрузки feedback через API
        def load_feedback_from_api():
            """Загружает список feedback через API"""
            try:
                response = requests.get(
                    f"{API_BASE_URL}/feedback",
                    headers=get_auth_headers()
                )
                if response.status_code == 401:
                    if refresh_access_token():
                        response = requests.get(
                            f"{API_BASE_URL}/feedback",
                            headers=get_auth_headers()
                        )
                
                if response.status_code == 200:
                    data = response.json()
                    feedback_list = data.get("feedback", [])
                    
                    if not feedback_list:
                        return pd.DataFrame()
                    
                    # Преобразуем в DataFrame
                    df = pd.DataFrame(feedback_list)
                    
                    # Преобразуем числовые коды в читаемые значения
                    df["Предсказано"] = df["predicted_status"].map({0: "ОДОБРЕНО", 1: "ОТКАЗ"})
                    df["Факт"] = df["actual_status"].map({0: "Вернул", 1: "Не вернул"})
                    df["P(возврат)"] = df["probability_repaid"].apply(
                        lambda x: f"{x:.1%}" if pd.notna(x) and x is not None else "-"
                    )
                    df["Дата"] = pd.to_datetime(df["created_at"], errors='coerce')
                    
                    # Переименовываем колонки для удобства
                    df = df.rename(columns={
                        "id": "ID",
                        "person_age": "Возраст",
                        "person_income": "Доход",
                        "person_home_ownership": "Собственность",
                        "person_emp_length": "Стаж",
                        "loan_intent": "Цель кредита",
                        "loan_grade": "Рейтинг",
                        "loan_amnt": "Сумма",
                        "loan_int_rate": "Ставка",
                        "loan_percent_income": "Доля дохода",
                        "cb_person_default_on_file": "Был дефолт",
                        "cb_person_cred_hist_length": "История"
                    })
                    
                    # Выбираем нужные колонки для отображения
                    display_columns = [
                        "ID", "Возраст", "Доход", "Собственность", "Стаж",
                        "Цель кредита", "Рейтинг", "Сумма", "Ставка",
                        "Доля дохода", "Был дефолт", "История",
                        "Предсказано", "Факт", "P(возврат)", "Дата"
                    ]
                    
                    return df[[col for col in display_columns if col in df.columns]]
                else:
                    error_detail = response.json().get("detail", "Неизвестная ошибка") if response.status_code != 401 else "Не авторизован"
                    st.error(f"❌ Ошибка загрузки данных: {error_detail}")
                    if response.status_code == 403:
                        st.warning("⚠️ Недостаточно прав. Требуется роль 'admin' или 'analyst'.")
                    return pd.DataFrame()
            except Exception as e:
                st.error(f"❌ Ошибка при загрузке данных: {str(e)}")
                st.exception(e)
                return pd.DataFrame()
        
        # --- Загрузка данных ---
        # Кнопка для обновления списка feedback из базы данных
        if st.button("🔄 Обновить данные", key="refresh_feedback_button"):
            st.rerun()  # Перезапускаем приложение для обновления данных
        
        # Загружаем данные через API
        df = load_feedback_from_api()
        
        if df.empty:
            st.info("📭 Нет данных о фидбэках.")
        else:
            # --- Фильтры ---
            # Секция для фильтрации feedback по различным критериям
            st.markdown("---")
            st.subheader("🔍 Фильтры")
            col1, col2 = st.columns(2)
            with col1:
                # Фильтр по решению модели (ОДОБРЕНО/ОТКАЗ)
                filter_decision = st.selectbox(
                    "Решение модели",
                    ["Все", "ОДОБРЕНО", "ОТКАЗ"],
                    key="filter_decision_admin"
                )
            with col2:
                # Фильтр по фактическому результату (Вернул/Не вернул)
                filter_actual = st.selectbox(
                    "Фактический результат",
                    ["Все", "Вернул", "Не вернул"],
                    key="filter_actual_admin"
                )
            
            # Применение фильтров к DataFrame
            df_filtered = df.copy()
            # Фильтруем по решению модели (если выбрано не "Все")
            if filter_decision != "Все":
                df_filtered = df_filtered[df_filtered["Предсказано"] == filter_decision]
            # Фильтруем по фактическому результату (если выбрано не "Все")
            if filter_actual != "Все":
                df_filtered = df_filtered[df_filtered["Факт"] == filter_actual]
            
            # --- Отображение отфильтрованных данных ---
            st.markdown("---")
            st.subheader(f"📋 Записи: {len(df_filtered)}")
            # Отображаем таблицу с сортировкой по дате (новые сверху)
            st.dataframe(
                df_filtered.sort_values("Дата", ascending=False, na_position='last'),
                use_container_width=True,
                hide_index=True
            )
            
            # --- Экспорт ---
            st.markdown("---")
            if st.button("📥 Экспорт в CSV", key="export_csv_admin"):
                csv = df_filtered.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "⬇️ Скачать CSV",
                    csv,
                    f"feedback_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    key="download_csv_admin"
                )
            
            # --- Статистика ---
            st.markdown("---")
            st.subheader("📊 Статистика")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Всего фидбэков", len(df))
            with col2:
                # Вычисляем точность модели
                if len(df) > 0:
                    df_accuracy = df.copy()
                    df_accuracy["Предсказано_норм"] = df_accuracy["Предсказано"].replace({"ОДОБРЕНО": "Вернул", "ОТКАЗ": "Не вернул"})
                    correct = (df_accuracy["Предсказано_норм"] == df_accuracy["Факт"]).sum()
                    accuracy = correct / len(df_accuracy) if len(df_accuracy) > 0 else 0
                    st.metric("Точность модели", f"{accuracy:.1%}")
                else:
                    st.metric("Точность модели", "-")
            with col3:
                avg_income = df["Доход"].mean() if len(df) > 0 else 0
                st.metric("Средний доход", f"{avg_income:,.0f} ₽")
            
            # Распределение решений
            if len(df) > 0:
                st.markdown("---")
                st.subheader("📈 Распределение фактических результатов")
                st.bar_chart(df["Факт"].value_counts())

# --- 🧾 Футер ---
st.markdown("---")
st.caption("Кредитный скоринг — дипломный проект | 2025")

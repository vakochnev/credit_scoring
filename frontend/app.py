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
tab1, tab2, tab3 = st.tabs([
    "🔍 Прогноз и объяснение",
    "📊 Сравнение моделей",
    "🔄 Дообучение"
])

# === ВКЛАДКА 1: Прогноз и объяснение ===
with tab1:
    st.subheader("Введите данные заемщика")

    col1, col2 = st.columns(2)
    with col1:
        person_age = st.number_input("Возраст", 18, 100, 35)
        person_income = st.number_input(
            "Доход", 10_000, 1_000_000, 75_000
        )
        person_home_ownership = st.selectbox(
            "Собственность",
            ["RENT", "OWN", "MORTGAGE", "OTHER"]
        )
        person_emp_length = st.number_input(
            "Стаж (лет)", 0.0, 50.0, 5.0
        )
        loan_intent = st.selectbox("Цель кредита", [
            "DEBTCONSOLIDATION", "EDUCATION", "HOMEIMPROVEMENT",
            "MEDICAL", "PERSONAL", "VENTURE"
        ])

    with col2:
        loan_grade = st.selectbox(
            "Кредитный рейтинг",
            ["A", "B", "C", "D", "E", "F", "G"]
        )
        loan_amnt = st.number_input(
            "Сумма кредита", 1_000, 100_000, 20_000
        )
        loan_int_rate = st.number_input(
            "Процентная ставка", 0.0, 100.0, 9.5
        )
        loan_percent_income = st.slider(
            "Процент дохода", 0.0, 1.0, 0.27
        )
        cb_person_default_on_file = st.selectbox(
            "Был ли дефолт", ["Y", "N"]
        )
        cb_person_cred_hist_length = st.number_input(
            "Длина кредитной истории", 0, 50, 4
        )

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
    if st.button("🔮 Прогнозировать и объяснить", key="predict_button"):
        with st.spinner("Выполняется анализ..."):
            try:
                response = explain_request(data)
                if response.status_code == 200:
                    result = response.json()

                    # Сохраняем результат в session_state
                    st.session_state['prediction_result'] = result
                    st.session_state['input_data'] = data

                    # Сбрасываем предыдущий PDF
                    if 'pdf_generated' in st.session_state:
                        del st.session_state['pdf_generated']
                    if 'report_path' in st.session_state:
                        del st.session_state['report_path']

                    # Отображаем результат
                    decision = "✅ ОДОБРЕНО" if result["decision"] == "approve" else "❌ ОТКАЗ"
                    status = "Клиент вернёт кредит" if result["status"] == "repaid" else "Риск дефолта"
                    prob = result["probability_repaid"]

                    st.success(f"📌 Решение: **{decision}**")
                    st.info(f"📊 Статус: {status}")
                    st.metric("Вероятность возврата", f"{prob:.1%}")

                    # Текстовое объяснение
                    st.subheader("📝 Объяснение решения")
                    for line in result["explanation"]["summary"]:
                        st.markdown(f"- {line.replace('↑ риск', '⬆️ повышает риск').replace('↓ риск', '⬇️ понижает риск')}")

                    # График SHAP (если есть)
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
    st.subheader("📄 Скачать PDF-отчёт")
    if 'prediction_result' in st.session_state:
        if st.button("📥 Сформировать PDF", key="generate_pdf_button"):
            with st.spinner("Генерация PDF..."):
                try:
                    input_data = st.session_state['input_data']
                    response = generate_report(input_data)
                    if response.status_code == 200:
                        report_path = response.json()["report_path"]
                        st.session_state['pdf_generated'] = True
                        st.session_state['report_path'] = report_path
                        st.success(f"✅ Отчёт сформирован: `{report_path}`")
                    else:
                        st.error(f"❌ Ошибка: {response.json().get('detail')}")
                except Exception as e:
                    st.error("⚠️ Не удалось сгенерировать отчёт")
                    st.exception(e)

        # Кнопка скачивания (только если отчёт сформирован)
        if 'pdf_generated' in st.session_state and 'report_path' in st.session_state:
            report_path = st.session_state['report_path']
            if os.path.exists(report_path):
                with open(report_path, "rb") as f:
                    st.download_button(
                        "⬇️ Скачать PDF",
                        f,
                        file_name="credit_report.pdf",
                        mime="application/pdf",
                        key="download_pdf_button"
                    )
            else:
                st.error("❌ Файл отчёта не найден. Попробуйте сформировать снова.")
    else:
        st.info("Сначала выполните прогноз, чтобы сформировать PDF.")

    # --- 📩 Обратная связь ---
    st.markdown("---")
    st.subheader("📩 Обратная связь")

    if 'prediction_result' in st.session_state:
        actual_status = st.radio(
            "Фактический статус кредита (по итогам выплаты):",
            options=[("Клиент вернул", 0), ("Клиент не вернул", 1)],
            format_func=lambda x: x[0]
        )

        if st.button("✅ Сохранить обратную связь", key="save_feedback_button"):
            result = st.session_state['prediction_result']
            input_data = st.session_state['input_data']

            feedback_data = input_data.copy()
            feedback_data["predicted_status"] = result["prediction"]
            feedback_data["actual_status"] = actual_status[1] if isinstance(actual_status, tuple) else actual_status
            feedback_data["probability_repaid"] = result.get("probability_repaid")
            feedback_data["probability_default"] = result.get("probability_default")

            try:
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
with tab2:
    st.subheader("Сравнение моделей")

    if st.button("🔄 Обновить сравнение", key="compare_models_button"):
        with st.spinner("Загрузка метрик..."):
            try:
                response = compare_models()
                if response.status_code == 200:
                    data = response.json()["models"]
                    df = pd.DataFrame(data)

                    st.dataframe(
                        df.style.format({"accuracy": "{:.3f}", "auc": "{:.3f}"}),
                        #use_container_width=True
                    )

                    # Барчарты
                    col1, col2 = st.columns(2)
                    with col1:
                        st.bar_chart(df.set_index("model")["accuracy"])
                    with col2:
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
                    st.success(f"✅ Отчёт сохранён: `{report_path}`")
                    with open(report_path, "rb") as f:
                        st.download_button(
                            "⬇️ Скачать PDF",
                            f,
                            file_name="model_comparison_report.pdf",
                            mime="application/pdf"
                        )
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
with tab3:
    st.subheader("🔄 Дообучение модели на обратной связи")

    # Обучение ансамбля
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
    
    # Добавляем разделитель между кнопками
    st.markdown("---")

    # Дообучение
    if st.button("🚀 Дообучить на фидбэках", key="retrain_model_button"):
        with st.spinner("Дообучение..."):
            try:
                response = retrain_model()
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Модель дообучена!")
                    st.json(result)
                else:
                    error_detail = response.json().get("detail", "Неизвестная ошибка")
                    st.error(f"❌ Ошибка: {error_detail}")
                    if response.status_code == 403:
                        st.warning("⚠️ Недостаточно прав. Требуется роль 'admin' или 'analyst'.")
            except Exception as e:
                st.error("⚠️ Не удалось дообучить")
                st.exception(e)

# --- 🧾 Футер ---
st.markdown("---")
st.caption("Кредитный скоринг — дипломный проект | 2025")

# frontend/app.py
import os
import sys
from pathlib import Path
import streamlit as st
import requests
import pandas as pd
import base64
from shared.config import API_BASE_URL, API_AUTH


# Добавляем корень проекта в путь
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

def generate_report(data):
    return requests.post(
        url=f"{API_BASE_URL}/report",
        json=data,
        auth=API_AUTH
    )

# --- 🔐 Авторизация ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.subheader("🔐 Вход в систему")
        username = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        if st.button("Войти"):
            if username == API_AUTH[0] and password == API_AUTH[1]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Неверный логин или пароль")
        return False
    return True

if not check_password():
    st.stop()

# --- 🎨 Настройка страницы ---
st.set_page_config(
    page_title="Кредитный скоринг",
    page_icon="💳",
    layout="wide"
)

# --- Загрузка данных ---
@st.cache_data
def load_data():
    try:
        response = requests.get(f"{API_BASE_URL}/compare", auth=API_AUTH)
        if response.status_code == 200:
            return response.json()["models"]
        else:
            return []
    except:
        return []

# --- Вкладки ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Прогноз и объяснение",
    "📊 Сравнение моделей",
    "📄 PDF-отчёт",
    "🔄 Дообучение"
])

# === ВКЛАДКА 1: Прогноз ===
with tab1:
    st.subheader("Введите данные заемщика")

    col1, col2 = st.columns(2)
    with col1:
        person_age = st.number_input("Возраст", 18, 100, 35)
        person_income = st.number_input("Доход", 10_000, 1_000_000, 75_000)
        person_home_ownership = st.selectbox("Собственность", ["RENT", "OWN", "MORTGAGE", "OTHER"])
        person_emp_length = st.number_input("Стаж (лет)", 0.0, 50.0, 5.0)
        loan_intent = st.selectbox("Цель кредита", [
            "DEBTCONSOLIDATION", "EDUCATION", "HOMEIMPROVEMENT",
            "MEDICAL", "PERSONAL", "VENTURE"
        ])

    with col2:
        loan_grade = st.selectbox("Кредитный рейтинг", ["A", "B", "C", "D", "E", "F", "G"])
        loan_amnt = st.number_input("Сумма кредита", 1_000, 100_000, 20_000)
        loan_int_rate = st.number_input("Процентная ставка", 0.0, 100.0, 9.5)
        loan_percent_income = st.slider("Процент дохода", 0.0, 1.0, 0.27)
        cb_person_default_on_file = st.selectbox("Был ли дефолт", ["Y", "N"])
        cb_person_cred_hist_length = st.number_input("Длина кредитной истории", 0, 50, 4)

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

    if st.button("🔮 Прогнозировать и объяснить"):
        with st.spinner("Выполняется анализ..."):
            try:
                response = requests.post(f"{API_BASE_URL}/explain", json=data, auth=API_AUTH)
                if response.status_code == 200:
                    result = response.json()

                    # Сохраняем результат
                    st.session_state['prediction_result'] = result
                    st.session_state['input_data'] = data

                    # Отображаем результат
                    decision = "✅ ОДОБРЕНО" if result["decision"] == "approve" else "❌ ОТКАЗ"
                    status = "Клиент вернёт кредит" if result["status"] == "repaid" else "Риск дефолта"
                    prob = result["probability_repaid"]

                    st.success(f"📌 Решение: **{decision}**")
                    st.info(f"📊 Статус: {status}")
                    st.metric("Вероятность возврата", f"{prob:.1%}")

                    # SHAP изображение
                    st.subheader("🔍 Объяснение решения")
                    for line in result["explanation"]["summary"]:
                        st.markdown(f"- {line.replace('↑ риск', '⬆️ повышает риск').replace('↓ риск', '⬇️ понижает риск')}")

                    st.image(
                        f"data:image/png;base64,{result['explanation']['shap_image_base64']}",
                        caption="Вклад признаков (SHAP)",
                        use_column_width=True
                    )
                else:
                    st.error(f"❌ Ошибка: {response.json().get('detail')}")
            except Exception as e:
                st.error("⚠️ Не удалось подключиться к API")
                st.exception(e)

# === ВКЛАДКА 2: Сравнение моделей ===
with tab2:
    st.subheader("📊 Сравнение моделей")

    if st.button("🔄 Обновить сравнение"):
        with st.spinner("Загрузка метрик..."):
            try:
                models = load_data()
                if models:
                    df = pd.DataFrame(models)
                    st.dataframe(df.style.format({"accuracy": "{:.3f}"}))
                    st.bar_chart(df.set_index("model")["accuracy"])
                else:
                    st.warning("Нет данных. Обучите модели сначала.")
            except Exception as e:
                st.error("Не удалось загрузить данные")
                st.exception(e)

# === ВКЛАДКА 3: PDF-отчёт ===
with tab3:
    st.subheader("📄 Генерация PDF-отчёта")

    if 'input_data' in st.session_state and 'prediction_result' in st.session_state:
        if st.button("📥 Сгенерировать PDF-отчёт"):
            with st.spinner("Генерация PDF..."):
                try:
                    response = generate_report(data)
                    if response.status_code == 200:
                        report_info = response.json()
                        report_path = report_info["report_path"]

                        # 🔍 Проверим, существует ли файл
                        if not os.path.exists(report_path):
                            st.error(f"❌ Файл не найден: {report_path}")
                            st.info("Проверьте, что бэкенд и фронтенд используют одну папку `reports`")
                        else:
                            st.success(f"✅ Отчёт сохранён: `{report_path}`")

                            # ✅ Читаем файл как байты
                            with open(report_path, "rb") as f:
                                st.download_button(
                                    "⬇️ Скачать PDF",
                                    f,
                                    file_name="credit_report.pdf",
                                    mime="application/pdf"
                                )
                    else:
                        st.error(f"❌ Ошибка: {response.json().get('detail')}")
                except Exception as e:
                    st.error("⚠️ Не удалось сгенерировать отчёт")
                    st.exception(e)

# === ВКЛАДКА 4: Дообучение ===
with tab4:
    st.subheader("🔄 Дообучение модели на обратной связи")

    # Кнопка обучения ансамбля
    if st.button("🎓 Обучить ансамбль"):
        with st.spinner("Обучение..."):
            try:
                response = requests.post(f"{API_BASE_URL}/train-final", auth=API_AUTH)
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ Модель обучена: {result['model']}, точность: {result['accuracy']:.3f}")
                else:
                    st.error("❌ Ошибка обучения")
            except Exception as e:
                st.error("⚠️ Не удалось обучить модель")
                st.exception(e)

    # Кнопка дообучения
    if st.button("🚀 Дообучить на фидбэках"):
        with st.spinner("Дообучение..."):
            try:
                response = requests.post(f"{API_BASE_URL}/retrain", auth=API_AUTH)
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Модель дообучена!")
                    st.json(result)
                else:
                    st.error(f"❌ Ошибка: {response.json().get('detail')}")
            except Exception as e:
                st.error("⚠️ Не удалось дообучить")
                st.exception(e)

    # Блок обратной связи
    st.markdown("---")
    st.subheader("📩 Оставить обратную связь")

    if 'prediction_result' in st.session_state:
        actual_status = st.radio(
            "Фактический статус кредита:",
            options=[("Клиент вернул", 0), ("Клиент не вернул", 1)],
            format_func=lambda x: x[0]
        )

        if st.button("✅ Сохранить обратную связь"):
            result = st.session_state['prediction_result']
            input_data = st.session_state['input_data']

            feedback_data = input_data.copy()
            feedback_data["predicted_status"] = result["prediction"]
            feedback_data["actual_status"] = actual_status[1] if isinstance(actual_status, tuple) else actual_status

            try:
                fb_response = requests.post(
                    f"{API_BASE_URL}/feedback",
                    json=feedback_data,
                    auth=API_AUTH
                )
                if fb_response.status_code == 200:
                    st.success("✅ Обратная связь сохранена для дообучения")
                else:
                    st.error("❌ Ошибка при отправке")
            except Exception as e:
                st.error("⚠️ Не удалось отправить")
                st.exception(e)
    else:
        st.info("Сначала выполните прогноз.")

# --- 🧾 Футер ---
st.markdown("---")
st.caption("Кредитный скоринг — дипломный проект | 2025")
# frontend/admin.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, select
from shared.database import Base, SessionLocal, engine
from shared.models import FeedbackDB

# --- Настройка страницы ---
st.set_page_config(
    page_title="Админ-панель",
    layout="wide",
    page_icon="🛡️"
)

# --- Заголовок ---
st.title("🛡️ Админ-панель: Обратная связь")

# --- Подключение к БД ---
#engine = create_engine(SQLALCHEMY_DATABASE_URL)
Base.metadata.create_all(bind=engine)

# --- Загрузка данных ---
def load_feedback():
    db = SessionLocal()
    try:
        query = select(FeedbackDB)
        result = db.execute(query)
        rows = result.scalars().all()
        return pd.DataFrame([
            {
                "ID": fb.id,
                "Возраст": fb.person_age,
                "Доход": fb.person_income,
                "Собственность": fb.person_home_ownership,
                "Стаж": fb.person_emp_length,
                "Цель кредита": fb.loan_intent,
                "Рейтинг": fb.loan_grade,
                "Сумма": fb.loan_amnt,
                "Ставка": fb.loan_int_rate,
                "Доля дохода": fb.loan_percent_income,
                "Был дефолт": fb.cb_person_default_on_file,
                "История": fb.cb_person_cred_hist_length,
                "Предсказано": "ОДОБРЕНО" if fb.predicted_status == 0 else "ОТКАЗ",
                "Факт": "Вернул" if fb.actual_status == 0 else "Не вернул",
                "P(возврат)": f"{fb.probability_repaid:.1%}" if fb.probability_repaid else "-",
                "Дата": fb.created_at
            }
            for fb in rows
        ])
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}")
        return pd.DataFrame()
    finally:
        db.close()

# --- Загрузка ---
df = load_feedback()

if df.empty:
    st.info("Нет данных о фидбэках.")
else:
    # --- Фильтры ---
    st.subheader("Фильтры")
    col1, col2 = st.columns(2)
    with col1:
        filter_decision = st.selectbox(
            "Решение модели",
            ["Все", "ОДОБРЕНО", "ОТКАЗ"]
        )
    with col2:
        filter_actual = st.selectbox(
            "Фактический результат",
            ["Все", "Вернул", "Не вернул"]
        )

    # Применение фильтров
    if filter_decision != "Все":
        df = df[df["Предсказано"] == filter_decision]
    if filter_actual != "Все":
        df = df[df["Факт"] == filter_actual]

    # --- Отображение ---
    st.subheader(f"Записи: {len(df)}")
    st.dataframe(
        df.sort_values("Дата", ascending=False),
        #use_container_width=True,
        hide_index=True
    )

    # --- Экспорт ---
    if st.button("📥 Экспорт в CSV"):
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "Скачать CSV",
            csv,
            "feedback_export.csv",
            "text/csv"
        )

# --- Статистика ---
if not df.empty:
    st.markdown("---")
    st.subheader("📊 Статистика")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего фидбэков", len(df))
    with col2:
        accuracy = (df["Предсказано"] == df["Факт"].replace({"Вернул": "ОДОБРЕНО", "Не вернул": "ОТКАЗ"})).mean()
        st.metric("Точность модели", f"{accuracy:.1%}")
    with col3:
        avg_income = df["Доход"].mean()
        st.metric("Средний доход", f"{avg_income:,.0f} ₽")

    # Распределение решений
    st.bar_chart(df["Факт"].value_counts())

# --- Футер ---
st.markdown("---")
st.caption("Админ-панель кредитного скоринга | 2025")
# app/services/retrain.py
"""
Модуль дообучения модели на основе обратной связи (feedback)

Модуль реализует:
- Загрузку фидбэков из базы данных
- Валидацию структуры и качества данных
- Предобработку и выравнивание признаков
- Дообучение ансамблевой модели (VotingClassifier)
- Сохранение обновлённой модели и background_data

Используется в эндпоинте /retrain

Автор: [Кочнева Арина]
Год: 2025
"""

import pandas as pd
import joblib
import logging
from pathlib import Path
from sklearn.ensemble import VotingClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score

from shared.data_processing import preprocess_data_for_prediction
from shared.config import (
    FEATURE_NAMES_PATH,
    BACKGROUND_DATA_PATH,
    ENSEMBLE_MODEL_PATH
)

# Импорт ORM-модели и сессии
from shared.models import FeedbackDB
from sqlalchemy.orm import Session
from sqlalchemy import select

logger = logging.getLogger(__name__)


def retrain_model_from_feedback(db: Session):
    """
    Переобучает ансамблевую модель на основе собранных фидбэков из БД.

    Процесс включает:
        1. Загрузку фидбэков из SQLite (таблица feedback)
        2. Валидацию структуры, типов и баланса классов
        3. Предобработку данных (OHE, feature engineering)
        4. Выравнивание признаков с текущей моделью
        5. Дообучение ансамбля (RF + XGBoost + CatBoost)
        6. Сохранение модели и background_data

    Args:
        db (Session): Сессия SQLAlchemy

    Returns:
        dict: Результат дообучения:
            {
                "status": "retrained",
                "samples_used": 12,
                "model_path": "/полный/путь/к/ensemble_model.pkl",
                "accuracy_on_feedback": 0.917,
                "class_balance": {0: 0.55, 1: 0.45}
            }

    Raises:
        ValueError: При ошибках валидации (пустые данные, дисбаланс)
        Exception: При ошибках предобработки или обучения

    Примечания:
        - Используется soft voting для усреднения вероятностей
        - Модель загружается из файла, дообучается и сохраняется обратно
        - background_data обновляется для SHAP-объяснений

    Пример использования:
        >>> from database import SessionLocal
        >>> db = SessionLocal()
        >>> try:
        >>>     result = retrain_model_from_feedback(db)
        >>>     print(f"Точность на фидбэках: {result['accuracy_on_feedback']:.3f}")
        >>> finally:
        >>>     db.close()
    """
    # --- 1. Загрузка фидбэков из БД ---
    try:
        stmt = select(FeedbackDB)
        result = db.execute(stmt)
        rows = result.scalars().all()

        if not rows:
            logger.warning("Попытка дообучения при отсутствии данных в таблице feedback")
            raise ValueError("Нет данных в таблице feedback. Нечего дообучать.")

        df = pd.DataFrame([{
            "person_age": fb.person_age,
            "person_income": fb.person_income,
            "person_home_ownership": fb.person_home_ownership,
            "person_emp_length": fb.person_emp_length,
            "loan_intent": fb.loan_intent,
            "loan_grade": fb.loan_grade,
            "loan_amnt": fb.loan_amnt,
            "loan_int_rate": fb.loan_int_rate,
            "loan_percent_income": fb.loan_percent_income,
            "cb_person_default_on_file": fb.cb_person_default_on_file,
            "cb_person_cred_hist_length": fb.cb_person_cred_hist_length,
            "actual_status": fb.actual_status
        } for fb in rows])

        logger.info(f"Загружено {len(df)} фидбэков из базы данных")
    except ValueError:
        # ValueError уже содержит правильное сообщение (например, "Нет данных в таблице feedback")
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке фидбэков из БД: {e}", exc_info=True)
        raise ValueError(f"Не удалось загрузить данные из БД: {str(e)}")

    # --- 2. Валидация целевой переменной ---
    if not pd.api.types.is_numeric_dtype(df['actual_status']):
        raise ValueError("Колонка 'actual_status' должна быть числовой (0 или 1)")

    unique_statuses = set(df['actual_status'].unique())
    if not unique_statuses.issubset({0, 1}):
        raise ValueError(f"Допустимые значения actual_status: 0 (repaid), 1 (default). Найдены: {unique_statuses}")

    # --- 3. Минимальный размер выборки ---
    min_samples = 5
    if len(df) < min_samples:
        raise ValueError(f"Недостаточно данных для дообучения. Минимум: {min_samples}, получено: {len(df)}")

    # --- 4. Проверка баланса классов ---
    class_ratio = df['actual_status'].value_counts(normalize=True).to_dict()
    imbalance_threshold = 0.1
    if len(class_ratio) == 2 and min(class_ratio.values()) < imbalance_threshold:
        raise ValueError(
            f"Сильный дисбаланс классов: {class_ratio}. "
            f"Минимальная доля одного класса: {imbalance_threshold}"
        )

    # --- 5. Разделение признаков и целевой переменной ---
    X_raw = df.drop(columns=['actual_status'])
    y = df['actual_status']

    # --- 6. Предобработка ---
    X_list = []
    for _, row in X_raw.iterrows():
        row_df = pd.DataFrame([row])
        processed = preprocess_data_for_prediction(row_df)
        X_list.append(processed.iloc[0])
    X = pd.DataFrame(X_list).reset_index(drop=True)

    # --- 7. Выравнивание признаков ---
    if FEATURE_NAMES_PATH.exists():
        expected_features = joblib.load(FEATURE_NAMES_PATH)
        logger.info(f"Загружены ожидаемые фичи: {len(expected_features)}")
    else:
        expected_features = X.columns.tolist()
        joblib.dump(expected_features, FEATURE_NAMES_PATH)
        logger.warning(f"feature_names.pkl не найден. Сохранён новый список из {len(expected_features)} фичей")

    # Добавляем недостающие колонки как 0
    for col in expected_features:
        if col not in X.columns:
            X[col] = 0
    X = X[expected_features]

    # --- 8. Загрузка или создание модели ---
    if ENSEMBLE_MODEL_PATH.exists():
        model = joblib.load(ENSEMBLE_MODEL_PATH)
        logger.info(f"Загружена модель для дообучения: {ENSEMBLE_MODEL_PATH}")
    else:
        logger.info("Создана новая ансамблевая модель")
        rf = RandomForestClassifier(n_estimators=50, random_state=42)
        xgb = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
        cb = CatBoostClassifier(silent=True, random_state=42)
        model = VotingClassifier(
            estimators=[('rf', rf), ('xgb', xgb), ('cb', cb)],
            voting='soft'
        )

    # --- 9. Дообучение ---
    logger.info(f"Начало дообучения на {len(X)} примерах...")
    model.fit(X, y)

    # --- 10. Оценка качества ---
    y_pred = model.predict(X)
    accuracy = accuracy_score(y, y_pred)
    logger.info(f"Точность на фидбэках: {accuracy:.3f}")

    # --- 11. Сохранение ---
    joblib.dump(model, ENSEMBLE_MODEL_PATH)
    logger.info(f"Модель сохранена: {ENSEMBLE_MODEL_PATH}")

    background_data = X.sample(min(100, len(X)), random_state=42)
    joblib.dump(background_data, BACKGROUND_DATA_PATH)
    logger.info(f"background_data обновлён: {BACKGROUND_DATA_PATH}")

    # --- 12. Возврат результата ---
    return {
        "status": "retrained",
        "samples_used": len(X),
        "model_path": str(ENSEMBLE_MODEL_PATH),
        "accuracy_on_feedback": accuracy,
        "class_balance": class_ratio
    }
# # app/services/retrain.py
"""
Модуль дообучения модели на основе обратной связи (feedback)

Модуль реализует:
- Загрузку фидбэков из файла
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
import json
import logging
from pathlib import Path
from sklearn.ensemble import VotingClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score

from shared.data_processing import preprocess_data_for_prediction
from shared.config import (
    FEEDBACK_PATH,
    FEATURE_NAMES_PATH,
    BACKGROUND_DATA_PATH,
    ENSEMBLE_MODEL_PATH
)


logger = logging.getLogger(__name__)


def retrain_model_from_feedback():
    """
    Переобучает ансамблевую модель на основе собранных
    фидбэков от пользователей.

    Процесс включает:
        1. Загрузку и парсинг feedback.jsonl
        2. Валидацию структуры, типов и баланса классов
        3. Предобработку данных (OHE, feature engineering)
        4. Выравнивание признаков с текущей моделью
        5. Дообучение ансамбля (RF + XGBoost + CatBoost)
        6. Сохранение модели и background_data

    Модель сохраняется в формате joblib. Используется soft voting для
    усреднения вероятностей.

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
        FileNotFoundError: Если feedback.jsonl не существует
        ValueError: При ошибках валидации
            (пустой файл, нехватка данных, дисбаланс)
        Exception: При ошибках предобработки или обучения

    Примечания:
        - Фидбэки хранятся в формате JSONL (один JSON-объект на строку)
        - actual_status: 0 — repaid, 1 — default
        - Модель переиспользуется или создаётся новая при отсутствии
        - background_data обновляется для SHAP-объяснений

    Пример использования:
        >>> result = retrain_model_from_feedback()
        >>> print(f"Точность на фидбэках: {result['accuracy_on_feedback']:.3f}")
    """
    # --- 1. Проверка существования файла ---
    if not FEEDBACK_PATH.exists():
        raise FileNotFoundError(
            f"Файл фидбэков не найден: {FEEDBACK_PATH}"
        )

    # --- 2. Загрузка и парсинг JSONL ---
    try:
        lines = FEEDBACK_PATH.read_text(
            encoding="utf-8"
        ).strip().split("\n")
        lines = [line.strip() for line in lines if line.strip()]
        if len(lines) == 0:
            raise ValueError(
                "Файл feedback.jsonl пуст. Нет данных для дообучения."
            )

        df = pd.DataFrame([json.loads(line) for line in lines])
        logger.info(
            f"📥 Загружено {len(df)} записей из {FEEDBACK_PATH.name}"
        )

    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка парсинга JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"Не удалось загрузить фидбэки: {str(e)}")

    # --- 3. Валидация структуры ---
    required_cols = [
        'person_age', 'person_income', 'person_home_ownership',
        'person_emp_length', 'loan_intent', 'loan_grade',
        'loan_amnt', 'loan_int_rate', 'loan_percent_income',
        'cb_person_default_on_file', 'cb_person_cred_hist_length',
        'actual_status'
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(
            f"Отсутствуют обязательные колонки: {missing}"
        )

    # --- 4. Валидация целевой переменной ---
    if not pd.api.types.is_numeric_dtype(df['actual_status']):
        raise ValueError(
            "Колонка 'actual_status' должна быть числовой (0 или 1)"
        )

    unique_statuses = set(df['actual_status'].unique())
    if not unique_statuses.issubset({0, 1}):
        raise ValueError(
            f"Допустимые значения actual_status: 0 (repaid), "
            f"1 (default). Найдены: {unique_statuses}"
        )

    # --- 5. Минимальный размер выборки ---
    min_samples = 5
    if len(df) < min_samples:
        raise ValueError(
            f"Недостаточно данных для дообучения. "
            f"Минимум: {min_samples}, получено: {len(df)}"
        )

    # --- 6. Проверка баланса классов ---
    class_ratio = (
        df['actual_status'].value_counts(normalize=True).to_dict()
    )
    imbalance_threshold = 0.1
    if (
        len(class_ratio) == 2 and min(class_ratio.values()) <
            imbalance_threshold
    ):
        raise ValueError(
            f"Сильный дисбаланс классов: {class_ratio}. "
            f"Минимальная доля одного класса: {imbalance_threshold}"
        )

    # --- 7. Удаление дубликатов ---
    df_clean = df.drop_duplicates(subset=required_cols[:-1])  # без actual_status
    if len(df_clean) < min_samples:
        raise ValueError(
            "После удаления дубликатов недостаточно данных "
            "для обучения"
        )

    logger.info(f"✅ Очищено: {len(df)} → {len(df_clean)} записей")

    # --- 8. Разделение признаков и целевой переменной ---
    X_raw = df_clean[required_cols[:-1]]
    y = df_clean['actual_status']

    # --- 9. Предобработка ---
    X_list = []
    for _, row in X_raw.iterrows():
        row_df = pd.DataFrame([row])
        processed = preprocess_data_for_prediction(row_df)
        X_list.append(processed.iloc[0])
    X = pd.DataFrame(X_list).reset_index(drop=True)

    # --- 10. Выравнивание признаков ---
    if FEATURE_NAMES_PATH.exists():
        expected_features = joblib.load(FEATURE_NAMES_PATH)
        logger.info(
            f"✅ Загружены ожидаемые фичи: {len(expected_features)}"
        )
    else:
        expected_features = X.columns.tolist()
        joblib.dump(expected_features, FEATURE_NAMES_PATH)
        logger.error(
            f"⚠️ feature_names.pkl не найден. Сохранён новый список "
            f"из {len(expected_features)} фичей"
        )

    # Добавляем недостающие колонки как 0
    for col in expected_features:
        if col not in X.columns:
            X[col] = 0
    X = X[expected_features]

    # --- 11. Загрузка или создание модели ---
    if ENSEMBLE_MODEL_PATH.exists():
        model = joblib.load(ENSEMBLE_MODEL_PATH)
        logger.info(
            f"✅ Загружена модель для дообучения: "
            f"{ENSEMBLE_MODEL_PATH}"
        )
    else:
        logger.info("🆕 Создана новая ансамблевая модель")
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        xgb = XGBClassifier(
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42
        )
        cb = CatBoostClassifier(silent=True, random_state=42)
        model = VotingClassifier(
            estimators=[('rf', rf), ('xgb', xgb), ('cb', cb)],
            voting='soft'  # усреднение вероятностей
        )

    # --- 12. Дообучение ---
    logger.info(f"🚀 Начало дообучения на {len(X)} примерах...")
    model.fit(X, y)

    # --- 13. Оценка качества ---
    y_pred = model.predict(X)
    accuracy = accuracy_score(y, y_pred)
    logger.info(f"✅ Точность на фидбэках: {accuracy:.3f}")

    # --- 14. Сохранение ---
    joblib.dump(model, ENSEMBLE_MODEL_PATH)
    logger.info(f"💾 Модель сохранена: {ENSEMBLE_MODEL_PATH}")

    background_data = X.sample(min(100, len(X)), random_state=42)
    joblib.dump(background_data, BACKGROUND_DATA_PATH)
    logger.info(
        f"💾 background_data обновлён: {BACKGROUND_DATA_PATH}"
    )

    # --- 15. Возврат результата ---
    return {
        "status": "retrained",
        "samples_used": len(X),
        "model_path": str(ENSEMBLE_MODEL_PATH),
        "accuracy_on_feedback": accuracy,
        "class_balance": class_ratio
    }

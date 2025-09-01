# app/services/retrain.py
import pandas as pd
import joblib
import json
from sklearn.ensemble import VotingClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score
from shared.data_processing import preprocess_data_for_prediction
from shared.config import (
    DATA_DIR,
    FEATURE_NAMES_PATH,
    BACKGROUND_DATA_PATH,
    ENSEMBLE_MODEL_PATH
)

FEEDBACK_FILE = DATA_DIR / "feedback.jsonl"

def retrain_model_from_feedback():
    """
    Переобучает ансамбль с валидацией фидбэков.
    """
    if not FEEDBACK_FILE.exists():
        raise FileNotFoundError(f"Файл {FEEDBACK_FILE} не найден")

    # 1. Загрузка
    lines = FEEDBACK_FILE.read_text(encoding="utf-8").strip().split("\n")
    lines = [l for l in lines if l.strip()]
    if len(lines) == 0:
        raise ValueError("Файл feedback.jsonl пуст")

    try:
        df = pd.DataFrame([json.loads(line) for line in lines])
    except Exception as e:
        raise ValueError(f"Ошибка парсинга JSON: {str(e)}")

    # 2. Валидация структуры
    required_cols = [
        'person_age', 'person_income', 'person_home_ownership',
        'person_emp_length', 'loan_intent', 'loan_grade',
        'loan_amnt', 'loan_int_rate', 'loan_percent_income',
        'cb_person_default_on_file', 'cb_person_cred_hist_length',
        'actual_status'
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Отсутствуют колонки: {missing}")

    # 3. Валидация целевой переменной
    if not pd.api.types.is_numeric_dtype(df['actual_status']):
        raise ValueError("actual_status должен быть числовым: 0 (repaid) или 1 (default)")
    if not set(df['actual_status'].unique()).issubset({0, 1}):
        raise ValueError("actual_status может быть только 0 или 1")

    # 4. Минимальный размер
    min_samples = 5
    if len(df) < min_samples:
        raise ValueError(f"Недостаточно данных для дообучения. Минимум: {min_samples}, получено: {len(df)}")

    # 5. Проверка баланса
    class_ratio = df['actual_status'].value_counts(normalize=True)
    imbalance_threshold = 0.1
    if len(class_ratio) == 2 and min(class_ratio) < imbalance_threshold:
        raise ValueError(
            f"Сильный дисбаланс классов: {class_ratio.to_dict()}. "
            f"Минимальная доля класса: {imbalance_threshold}"
        )

    # 6. Удаление дубликатов
    df = df.drop_duplicates(subset=required_cols[:-1])  # без actual_status
    if len(df) < min_samples:
        raise ValueError("После удаления дубликатов недостаточно данных")

    # 7. Предобработка
    X_raw = df[required_cols[:-1]]
    y = df['actual_status']

    X_list = []
    for _, row in X_raw.iterrows():
        row_df = pd.DataFrame([row])
        processed = preprocess_data_for_prediction(row_df)
        X_list.append(processed.iloc[0])
    X = pd.DataFrame(X_list).reset_index(drop=True)

    # 8. Выравнивание фичей
    if FEATURE_NAMES_PATH.exists():
        expected_features = joblib.load(FEATURE_NAMES_PATH)
    else:
        expected_features = X.columns.tolist()
        joblib.dump(expected_features, FEATURE_NAMES_PATH)

    for col in expected_features:
        if col not in X.columns:
            X[col] = 0
    X = X[expected_features]

    # 9. Загрузка или создание модели
    if ENSEMBLE_MODEL_PATH.exists():
        model = joblib.load(ENSEMBLE_MODEL_PATH)
        print(f"✅ Загружена модель: {ENSEMBLE_MODEL_PATH}")
    else:
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        xgb = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
        cb = CatBoostClassifier(silent=True, random_state=42)
        model = VotingClassifier([('rf', rf), ('xgb', xgb), ('cb', cb)], voting='soft')

    # 10. Дообучение
    model.fit(X, y)
    y_pred = model.predict(X)
    accuracy = accuracy_score(y, y_pred)

    # 11. Сохранение
    joblib.dump(model, ENSEMBLE_MODEL_PATH)
    background_data = X.sample(min(100, len(X)), random_state=42)
    joblib.dump(background_data, BACKGROUND_DATA_PATH)

    return {
        "status": "retrained",
        "samples_used": len(X),
        "model_path": str(ENSEMBLE_MODEL_PATH),
        "accuracy_on_feedback": accuracy,
        "class_balance": class_ratio.to_dict()
    }
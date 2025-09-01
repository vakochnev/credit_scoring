import pandas as pd
from shared.config import FEATURE_NAMES_PATH
import joblib

from shared.config import DATA_DIR

CATEGORIES = {
    'person_home_ownership': ['MORTGAGE', 'OTHER', 'OWN', 'RENT'],
    'loan_intent': ['DEBTCONSOLIDATION', 'EDUCATION', 'HOMEIMPROVEMENT', 'MEDICAL', 'PERSONAL', 'VENTURE'],
    'loan_grade': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
    'cb_person_default_on_file': ['N', 'Y']
}

def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['loan_to_income_ratio'] = df['loan_amnt'] / df['person_income']
    return df

def preprocess_data_for_prediction(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = feature_engineering(df)
    for col, categories in CATEGORIES.items():
        for cat in categories:
            df[f"{col}_{cat}"] = (df[col] == cat).astype(int)
        df = df.drop(col, axis=1)
    # Выравнивание по ожидаемым фичам
    if FEATURE_NAMES_PATH.exists():
        expected_features = joblib.load(FEATURE_NAMES_PATH)
        for col in expected_features:
            if col not in df.columns:
                df[col] = 0
        df = df[expected_features]
    return df

def preprocess_data(df: pd.DataFrame) -> (pd.DataFrame, pd.Series):
    df = df.copy()
    df = feature_engineering(df)
    for col, categories in CATEGORIES.items():
        for cat in categories:
            df[f"{col}_{cat}"] = (df[col] == cat).astype(int)
        df = df.drop(col, axis=1)
    X = df.drop('loan_status', axis=1)
    y = df['loan_status']
    return X, y


def check_and_retrain():
    """
    Проверяет, нужно ли дообучать модель.
    """
    feedback_file = DATA_DIR / "feedback.jsonl"
    if not feedback_file.exists():
        return

    lines = feedback_file.read_text().strip().split("\n")
    lines = [l for l in lines if l.strip()]

    if len(lines) >= 10:  # порог
        print(f"🔄 Автоматическое дообучение: {len(lines)} фидбэков")
        try:
            from app.services.retrain import retrain_model_from_feedback
            result = retrain_model_from_feedback()
            print(f"✅ Авто-дообучение завершено: {result['accuracy_on_feedback']:.3f}")
        except Exception as e:
            print(f"❌ Ошибка авто-дообучения: {e}")
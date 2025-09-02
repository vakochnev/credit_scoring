from pathlib import Path
import joblib
import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt
import base64
from io import BytesIO

from shared.data_processing import preprocess_data_for_prediction
from shared.config import (
    ENSEMBLE_MODEL_PATH, FEATURE_NAMES_PATH, BACKGROUND_DATA_PATH
)


_model = None
_feature_names = None
_background_data = None


def _load_model():
    global _model, _feature_names, _background_data
    if _model is None:
        _model = joblib.load(ENSEMBLE_MODEL_PATH)
        _feature_names = joblib.load(FEATURE_NAMES_PATH)
        _background_data = joblib.load(BACKGROUND_DATA_PATH)
    return _model, _feature_names, _background_data

def predict_loan_status(input_df: pd.DataFrame) -> dict:
    model, feature_names, background_data = _load_model()
    input_processed = preprocess_data_for_prediction(input_df)
    input_processed = input_processed[feature_names]

    pred = model.predict(input_processed)[0]
    proba = model.predict_proba(input_processed)[0]

    return {
        "prediction": int(pred),
        "probability_repaid": float(proba[0]),
        "probability_default": float(proba[1])
    }

def explain_prediction(input_data) -> dict:
    model, feature_names, background_data = _load_model()

    input_df = pd.DataFrame([input_data])
    input_processed = preprocess_data_for_prediction(input_df)
    input_processed = input_processed[feature_names]

    # Создаём callable-обёртку для VotingClassifier
    def model_predict_proba(X):
        # X может быть numpy array или DataFrame
        if isinstance(X, np.ndarray):
            X = pd.DataFrame(X, columns=feature_names)
        return model.predict_proba(X)

    # Передаём обёртку в Explainer
    explainer = shap.Explainer(model_predict_proba, background_data)

    # Получаем SHAP значения
    shap_values = explainer(input_processed)

    # Для бинарной классификации: используем значения для класса "дефолт" (1)
    if len(shap_values.output_names) == 2:
        shap_vals = shap_values.values[:, :, 1].flatten()  # (1, n_features, 2) -> (n_features,)
        base_value = float(shap_values.base_values[0][1])
    else:
        shap_vals = shap_values.values.flatten()
        base_value = float(shap_values.base_values[0])

    # Предсказание
    prediction = model.predict(input_processed)[0]
    prediction_proba = model.predict_proba(input_processed)[0]

    # Топ-5 признаков
    top_features = sorted(
        zip(feature_names, shap_vals),
        key=lambda x: abs(x[1]),
        reverse=True
    )[:5]

    # Генерация графика SHAP
    fig, ax = plt.subplots(figsize=(8, 6))
    try:
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_vals,
                base_values=base_value,
                data=input_processed.iloc[0],
                feature_names=feature_names
            ),
            show=False
        )
    except Exception as e:
        plt.close(fig)
        raise ValueError(f"Ошибка при построении waterfall: {str(e)}")

    # Генерация графика
    shap.plots.waterfall(shap_values[0, :, 1], show=False)
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')

    # Сохраняем в файл
    images_dir = Path("reports/images")
    images_dir.mkdir(exist_ok=True)
    img_path = images_dir / "shap_waterfall.png"
    fig.savefig(img_path, format='png', bbox_inches='tight', dpi=150, facecolor='white')
    plt.close(fig)

    return {
        "prediction": int(prediction),
        "status": "repaid" if prediction == 0 else "default",
        "decision": "approve" if prediction == 0 else "reject",
        "probability_repaid": float(prediction_proba[0]),
        "probability_default": float(prediction_proba[1]),
        "explanation": {
            "base_value": base_value,
            "shap_values": [
                {"feature": name, "value": float(val)}
                for name, val in top_features
            ],
            "summary": [
                f"{name}: {'↑ риск' if val > 0 else '↓ риск'} ({val:+.3f})"
                for name, val in top_features
            ],
            "shap_image_base64": image_base64,
            "shap_image_path": "images/shap_waterfall.png"
        }
    }
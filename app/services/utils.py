# app/services/utils.py
"""
Модуль предсказания и объяснения решений

Модуль реализует:
- Загрузку ансамблевой модели (VotingClassifier)
- Прогнозирование статуса кредита
- Объяснение решения с помощью SHAP
- Генерацию графиков и текстовых объяснений

Особенности:
- Поддержка VotingClassifier через callable-обёртку
- Кэширование модели для производительности
- Генерация waterfall-графика SHAP
- Сохранение графика для PDF-отчётов

Автор: [Кочнева Арина]
Год: 2025
"""

from pathlib import Path
import joblib
import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import logging

# Импорт компонентов системы
from shared.data_processing import preprocess_data_for_prediction
from shared.config import (
    ENSEMBLE_MODEL_PATH, FEATURE_NAMES_PATH, BACKGROUND_DATA_PATH,
    IMAGES_DIR
)


logger = logging.getLogger(__name__)


# --- 🧠 Глобальные переменные для кэширования ---
"""
Кэширование модели, фичей и background_data
для ускорения повторных вызовов.
Загружается один раз при первом вызове.
"""
_model = None
_feature_names = None
_background_data = None


def _load_model():
    """
    Загружает модель, названия фичей и background_data один
    раз и кэширует их.

    Реализует паттерн Singleton: при повторных вызовах возвращает
    закэшированные объекты.

    Returns:
        tuple: (model, feature_names, background_data)

    Raises:
        FileNotFoundError: Если модель или данные не найдены
        Exception: При ошибках десериализации

    Примечания:
        - Используется для ускорения прогнозирования
        - Пути задаются в shared/config.py
    """
    global _model, _feature_names, _background_data

    if _model is None:
        try:
            logger.info(f"📥 Загрузка модели: {ENSEMBLE_MODEL_PATH}")
            _model = joblib.load(ENSEMBLE_MODEL_PATH)

            logger.info(
                f"📥 Загрузка названий фичей: {FEATURE_NAMES_PATH}"
            )
            _feature_names = joblib.load(FEATURE_NAMES_PATH)

            logger.info(
                f"📥 Загрузка background_data: {BACKGROUND_DATA_PATH}"
            )
            _background_data = joblib.load(BACKGROUND_DATA_PATH)

            logger.info(
                f"✅ Модель загружена: {_model.__class__.__name__}"
            )

        except FileNotFoundError as e:
            raise FileNotFoundError(f"Файл не найден: {e}")
        except Exception as e:
            raise Exception(f"Ошибка при загрузке модели: {e}")

    return _model, _feature_names, _background_data


def predict_loan_status(input_df: pd.DataFrame) -> dict:
    """
    Выполняет прогноз статуса кредита с использованием ансамблевой
    модели.

    Args:
        input_df (pd.DataFrame): Входные данные одного заемщика

    Returns:
        dict: Результат прогноза:
            {
                "prediction": 0 или 1,
                "probability_repaid": float,
                "probability_default": float
            }

    Raises:
        ValueError: Если входные данные некорректны
        Exception: При ошибках предсказания

    Пример:
        >>> input_df = pd.DataFrame([{
        ...     "person_age": 35,
        ...     "person_income": 75000,
        ...     ...
        ... }])
        >>> result = predict_loan_status(input_df)
        >>> print(result)
        {
            'prediction': 0,
            'probability_repaid': 0.92,
            'probability_default': 0.08
        }
    """
    try:
        model, feature_names, _ = _load_model()

        # Предобработка
        input_processed = preprocess_data_for_prediction(input_df)
        # Выравнивание
        input_processed = input_processed[feature_names]

        # Предсказание
        pred = model.predict(input_processed)[0]
        proba = model.predict_proba(input_processed)[0]

        return {
            "prediction": int(pred),
            "probability_repaid": float(proba[0]),
            "probability_default": float(proba[1])
        }

    except Exception as e:
        raise ValueError(f"Ошибка при предсказании: {str(e)}")


def explain_prediction(input_data: dict) -> dict:
    """
    Генерирует интерпретируемое объяснение решения модели
    с помощью SHAP.

    Поддерживает ансамбль (VotingClassifier) через создание
    callable-обёртки.

    Args:
        input_data (dict): Данные заемщика в формате словаря

    Returns:
        dict: Полное объяснение:
            {
                "prediction": int,
                "status": str,
                "decision": str,
                "probability_repaid": float,
                "explanation": {
                    "base_value": float,
                    "shap_values": [{"feature": str, "value": float}],
                    "summary": [str],
                    "shap_image_base64": str,
                    "shap_image_path": str
                }
            }

    Raises:
        ValueError: При ошибках предобработки или объяснения
        Exception: При ошибках генерации графика

    Особенности:
        - Использует shap.Explainer с callable-обёрткой
        - Генерирует waterfall-график
        - Сохраняет изображение для PDF-отчётов
        - Возвращает top-5 наиболее важных признаков
    """
    try:
        # 1. Загрузка модели
        model, feature_names, background_data = _load_model()

        # 2. Предобработка данных
        input_df = pd.DataFrame([input_data])
        input_processed = preprocess_data_for_prediction(input_df)
        input_processed = input_processed[feature_names]

        # 3. Создание callable-обёртки для ансамбля
        def model_predict_proba(X):
            """
            Обёртка, преобразующая VotingClassifier в вызываемую
            функцию.
            Требуется, так как SHAP не поддерживает VotingClassifier
            напрямую.
            """
            if isinstance(X, np.ndarray):
                X = pd.DataFrame(X, columns=feature_names)
            return model.predict_proba(X)

        # 4. Создание SHAP Explainer
        explainer = shap.Explainer(
            model_predict_proba,
            background_data
        )

        # 5. Получение SHAP значений
        shap_values = explainer(input_processed)

        # 6. Извлечение значений для класса "дефолт" (1)
        if len(shap_values.output_names) == 2:
            shap_vals = shap_values.values[:, :, 1].flatten()
            base_value = float(shap_values.base_values[0][1])
        else:
            shap_vals = shap_values.values.flatten()
            base_value = float(shap_values.base_values[0])

        # 7. Предсказание
        prediction = model.predict(input_processed)[0]
        prediction_proba = model.predict_proba(input_processed)[0]

        # 8. Топ-5 признаков по абсолютному вкладу
        top_features = sorted(
            zip(feature_names, shap_vals),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:5]

        # 9. Генерация waterfall-графика
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
            raise ValueError(
                f"Ошибка при построении waterfall: {str(e)}"
            )

        # 10. Сохранение в base64 (для встраивания в PDF)
        buf = BytesIO()
        fig.savefig(
            buf,
            format='png',
            bbox_inches='tight',
            dpi=150,
            facecolor='white'
        )
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        # 11. Сохранение на диск (для отчётов)
        img_path = IMAGES_DIR / "shap_waterfall.png"
        # Пересоздаём график для сохранения
        fig, ax = plt.subplots(figsize=(8, 6))
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_vals,
                base_values=base_value,
                data=input_processed.iloc[0],
                feature_names=feature_names
            ),
            show=False
        )
        fig.savefig(
            img_path,
            format='png',
            bbox_inches='tight',
            dpi=150,
            facecolor='white'
        )
        plt.close(fig)

        # 12. Формирование результата
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

    except Exception as e:
        raise ValueError(f"Ошибка при объяснении: {str(e)}")

# shared/data_processing.py
"""
Модуль предобработки данных для кредитного скоринга

Модуль реализует:
- Feature engineering (например, loan_to_income_ratio)
- One-Hot Encoding категориальных признаков
- Предобработку данных для предсказания и обучения
- Автоматическое дообучение при накоплении фидбэков

Основные функции:
- feature_engineering: создание новых признаков
- preprocess_data_for_prediction: обработка входных данных заемщика
- preprocess_data: подготовка данных для обучения модели
- check_and_retrain: автоматическое дообучение модели

Автор: [Кочнева Арина]
Год: 2025
"""

import pandas as pd
from pathlib import Path
import joblib
import logging

# Импорт путей из централизованной конфигурации
from shared.config import (
    FEATURE_NAMES_PATH,
    DATA_DIR
)


logger = logging.getLogger(__name__)


# --- 🔹 Категории для One-Hot Encoding ---
"""
Словарь определяет все возможные значения категориальных признаков.
Используется для OHE, чтобы гарантировать одинаковое количество фичей
при обучении и предсказании.

Ключевые признаки:
- person_home_ownership: тип собственности
- loan_intent: цель кредита
- loan_grade: кредитный рейтинг
- cb_person_default_on_file: был ли дефолт
"""
CATEGORIES = {
    'person_home_ownership': ['MORTGAGE', 'OTHER', 'OWN', 'RENT'],
    'loan_intent': [
        'DEBTCONSOLIDATION', 'EDUCATION', 'HOMEIMPROVEMENT',
        'MEDICAL', 'PERSONAL', 'VENTURE'
    ],
    'loan_grade': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
    'cb_person_default_on_file': ['N', 'Y']
}


def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавляет новые признаки на основе существующих.

    В текущей реализации:
        - loan_to_income_ratio = loan_amnt / person_income

    Args:
        df (pd.DataFrame): Исходный датафрейм

    Returns:
        pd.DataFrame: Датафрейм с новыми признаками

    Пример:
        >>> df['loan_to_income_ratio'] =
            df['loan_amnt'] / df['person_income']

    Примечания:
        - Функция не изменяет исходный DataFrame
        - Результат всегда содержит исходные колонки + новые
    """
    df = df.copy()
    df['loan_to_income_ratio'] = df['loan_amnt'] / df['person_income']
    return df


def preprocess_data_for_prediction(df: pd.DataFrame) -> pd.DataFrame:
    """
    Подготавливает данные заемщика для предсказания модели.

    Этапы:
        1. Создание новых признаков (feature engineering)
        2. One-Hot Encoding категориальных переменных
        3. Удаление исходных категориальных колонок
        4. Выравнивание с ожидаемыми фичами из обученной модели

    Args:
        df (pd.DataFrame): Данные одного или нескольких заемщиков

    Returns:
        pd.DataFrame: Обработанный датафрейм с правильным порядком и количеством фичей

    Raises:
        ValueError: Если отсутствуют обязательные колонки
        Exception: При ошибках загрузки feature_names.pkl

    Особенности:
        - Если feature_names.pkl не существует, используется текущий набор фичей
        - Недостающие фичи добавляются как 0
        - Лишние фичи удаляются
        - Гарантирует совместимость с моделью, обученной ранее
    """
    df = df.copy()
    df = feature_engineering(df)

    # One-Hot Encoding
    for col, categories in CATEGORIES.items():
        for cat in categories:
            df[f"{col}_{cat}"] = (df[col] == cat).astype(int)
        df = df.drop(col, axis=1)

    # Выравнивание по фичам из обученной модели
    if FEATURE_NAMES_PATH.exists():
        try:
            expected_features = joblib.load(FEATURE_NAMES_PATH)
            logger.info(
                f"✅ Загружено {len(expected_features)} ожидаемых "
                f"фичей из {FEATURE_NAMES_PATH}"
            )
        except Exception as e:
            raise Exception(
                f"Ошибка загрузки {FEATURE_NAMES_PATH}: {e}"
            )
    else:
        # Если файл не найден — используем текущие фичи (только для первого обучения)
        expected_features = df.columns.tolist()
        logger.error(
            f"⚠️ {FEATURE_NAMES_PATH} не найден. Используем текущие "
            f"фичи: {len(expected_features)}"
        )

    # Добавляем недостающие фичи как 0
    for col in expected_features:
        if col not in df.columns:
            df[col] = 0

    # Упорядочиваем фичи в том же порядке, что и при обучении
    df = df[expected_features]

    return df


def preprocess_data(df: pd.DataFrame) -> (pd.DataFrame, pd.Series):
    """
    Подготавливает данные для обучения модели.

    Включает:
        - Feature engineering
        - One-Hot Encoding
        - Разделение на признаки (X) и целевую переменную (y)

    Args:
        df (pd.DataFrame): Исходный датафрейм с целевой переменной

    Returns:
        tuple: (X, y) — матрица признаков и вектор целевой переменной

    Примечания:
        - Используется на этапе обучения и дообучения
        - Не требует feature_names.pkl, так как X формируется заново
    """
    df = df.copy()
    df = feature_engineering(df)

    # One-Hot Encoding
    for col, categories in CATEGORIES.items():
        for cat in categories:
            df[f"{col}_{cat}"] = (df[col] == cat).astype(int)
        df = df.drop(col, axis=1)

    X = df.drop('loan_status', axis=1)
    y = df['loan_status']

    return X, y


def check_and_retrain():
    """
    Проверяет количество фидбэков и запускает автоматическое дообучение.

    Логика:
        - Проверяет наличие файла feedback.jsonl
        - Считает количество записей
        - Если >= 10 — запускает retrain_model_from_feedback()

    Используется как фоновая задача или вызывается после каждого feedback_api.

    Пример использования:
        >>> check_and_retrain()  # вызывается автоматически

    Примечания:
        - Порог (10) можно вынести в config.py
        - Функция не сохраняет состояние — каждый раз читает файл
        - Ошибки логируются в консоль
    """
    feedback_file = DATA_DIR / "feedback.jsonl"
    if not feedback_file.exists():
        return

    try:
        lines = feedback_file.read_text(
            encoding="utf-8"
        ).strip().split("\n"
                                            )
        lines = [l for l in lines if l.strip()]
    except Exception as e:
        logger.critical(
            f"❌ Ошибка чтения feedback.jsonl: {e}"
        )
        return

    threshold = 10  # порог для дообучения
    if len(lines) >= threshold:
        logger.info(
            f"🔄 Автоматическое дообучение: {len(lines)} фидбэков"
        )
        try:
            from app.services.retrain import retrain_model_from_feedback
            result = retrain_model_from_feedback()
            logger.info(
                f"✅ Авто-дообучение завершено. Точность: "
                f"{result['accuracy_on_feedback']:.3f}"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка авто-дообучения: {e}")

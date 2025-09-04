# app/services/model_training.py
"""
Модуль обучения ансамблевой модели

Модуль реализует обучение ансамбля из трёх моделей:
- RandomForest
- XGBoost
- CatBoost

Используется VotingClassifier с мягким голосованием (soft voting),
что позволяет учитывать вероятности каждой модели.

Основные функции:
- train_ensemble_model: обучение и сохранение ансамбля

Автор: [Кочнева Арина]
Год: 2025
"""

from sklearn.ensemble import VotingClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
import joblib
import logging

# Импорт путей из централизованной конфигурации
from shared.config import (
    ENSEMBLE_MODEL_PATH,
    FEATURE_NAMES_PATH,
    BACKGROUND_DATA_PATH
)


logger = logging.getLogger(__name__)


def train_ensemble_model(X, y):
    """
    Обучает ансамблевую модель методом голосования
        (VotingClassifier).

    Ансамбль состоит из трёх моделей:
        - RandomForestClassifier
        - XGBClassifier
        - CatBoostClassifier

    Используется **мягкое голосование (soft voting)** —
    усреднение вероятностей, что даёт более стабильные и
    точные предсказания по сравнению с жёстким голосованием.

    Модель сохраняется вместе с:
        - feature_names.pkl — список признаков (для согласованности
            при предсказании)
        - background_data.pkl — подвыборка для SHAP-объяснений

    Args:
        X (pd.DataFrame или np.ndarray): Матрица признаков (фичей)
        y (pd.Series или np.ndarray): Вектор целевой переменной
            (0 — repaid, 1 — default)

    Returns:
        dict: Результат обучения с информацией о модели и её точности:
            {
                "model": "Ensemble (RF + XGBoost + CatBoost)",
                "accuracy": 0.934
            }

    Raises:
        ValueError: Если X или y пусты
        ValueError: Если размеры X и y не совпадают
        Exception: Если возникла ошибка при обучении одной из моделей

    Примечания:
        - Все модели инициализируются с random_state=42 для
            воспроизводимости
        - CatBoost работает в silent-режиме (без логов)
        - XGBoost: отключён use_label_encoder, указана eval_metric
        - VotingClassifier: voting='soft' — усреднение вероятностей

    Пример использования:
        >>> X, y = preprocess_data(df)
        >>> result = train_ensemble_model(X, y)
        >>> print(f"Точность: {result['accuracy']:.3f}")
    """
    # Валидация входных данных
    if X.empty or len(X) == 0:
        raise ValueError("Матрица признаков X пуста")
    if len(X) != len(y):
        raise ValueError(
            f"Размеры X ({len(X)}) и y ({len(y)}) не совпадают"
        )

    # Определение ансамблевой модели
    model = VotingClassifier(
        estimators=[
            # 1. Случайный лес — устойчив к переобучению
            (
                'rf',
                RandomForestClassifier(
                    n_estimators=50,           # количество деревьев
                    random_state=42,           # воспроизводимость
                    n_jobs=-1                  # параллельная обработка
                )
            ),
            # 2. XGBoost — градиентный бустинг, высокая точность
            (
                'xgb',
                XGBClassifier(
                    use_label_encoder=False,   # отключаем предупреждение
                    eval_metric='logloss',     # метрика для валидации
                    random_state=42,           # воспроизводимость
                    n_jobs=-1                  # ускорение
                )
            ),
            # 3. CatBoost — автоматическая обработка категориальных признаков
            (
                'cb',
                CatBoostClassifier(
                    silent=True,               # отключаем вывод в консоль
                    random_state=42,           # воспроизводимость
                    #verbose=0                  # альтернатива silent
                )
            )
        ],
        voting='soft'  # усреднение вероятностей (лучше для интерпретируемости)
    )

    # Обучение ансамбля на всех данных
    logger.info("🚀 Начало обучения ансамблевой модели...")
    model.fit(X, y)
    logger.info("✅ Модель обучена")

    # Сохранение компонентов
    logger.info(f"💾 Сохранение модели: {ENSEMBLE_MODEL_PATH}")
    joblib.dump(model, ENSEMBLE_MODEL_PATH)

    logger.info(
        f"💾 Сохранение названий признаков: {FEATURE_NAMES_PATH}"
    )
    joblib.dump(X.columns.tolist(), FEATURE_NAMES_PATH)

    logger.info(
        f"💾 Сохранение background_data: {BACKGROUND_DATA_PATH}"
    )
    background_data = X.sample(min(100, len(X)), random_state=42)
    joblib.dump(background_data, BACKGROUND_DATA_PATH)

    # Оценка точности на обучающей выборке
    accuracy = model.score(X, y)
    logger.info(
        f"📊 Точность модели на обучающей выборке: {accuracy:.3f}"
    )

    return {
        "model": "Ensemble (RF + XGBoost + CatBoost)",
        "accuracy": accuracy
    }

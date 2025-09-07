# app/services/model_comparison.py
"""
Сравнение моделей машинного обучения

Модуль реализует:
- Обучение нескольких моделей (RandomForest, XGBoost, LightGBM,
    CatBoost, Ensemble)
- Сравнение по метрикам: accuracy и AUC-ROC
- Построение ROC-кривых
- Генерацию графиков

Используется в:
- Эндпоинте /compare
- Генерации отчётов

Автор: [Кочнева Арина]
Год: 2025
"""

import matplotlib.pyplot as plt
import os
from pathlib import Path
import logging

from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
import joblib


logger = logging.getLogger(__name__)


def compare_models(X, y):
    """
    Обучает несколько моделей и сравнивает их производительность.

    Модели:
        - RandomForest
        - XGBoost
        - LightGBM
        - CatBoost
        - Ансамбль (VotingClassifier)

    Метрики:
        - Точность (accuracy)
        - AUC-ROC

    Args:
        X (pd.DataFrame or np.ndarray): Признаки (фичи)
        y (pd.Series or np.ndarray): Целевая переменная (loan_status)

    Returns:
        dict: Словарь с результатами и обученными моделями:
            {
                "results": [
                    {
                        "model": "RandomForest",
                        "accuracy": 0.91,
                        "auc": 0.93
                    },
                    ...
                ],
                "X_test": X_test,        # Тестовые признаки
                "y_test": y_test,        # Тестовые метки
                "trained_models": {      # Обученные модели
                    "RandomForest": model_rf,
                    ...
                }
            }

    Raises:
        ValueError: Если X или y пусты
        ValueError: Если размеры X и y не совпадают
    """
    if X.empty or len(X) == 0:
        raise ValueError("Признаки (X) пусты")
    if len(X) != len(y):
        raise ValueError(
            f"Размеры X ({len(X)}) и "
            f"y ({len(y)}) не совпадают"
        )

    # Разделение данных
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Определение моделей
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=100,
            random_state=42
        ),
        "XGBoost": XGBClassifier(
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42
        ),
        "LightGBM": LGBMClassifier(random_state=42),
        "CatBoost": CatBoostClassifier(silent=True, random_state=42),
        "Ensemble": VotingClassifier(
            estimators=[
                (
                    'rf',
                    RandomForestClassifier(
                        n_estimators=50,
                        random_state=42
                    )
                ),
                (
                    'xgb',
                    XGBClassifier(
                        use_label_encoder=False,
                        eval_metric='logloss',
                        random_state=42
                    )
                ),
                (
                    'lgb',
                    LGBMClassifier(random_state=42)
            )],
            voting='soft'
        )
    }

    results = []
    trained_models = {}

    for name, model in models.items():
        try:
            # Обучение
            model.fit(X_train, y_train)

            # Предсказания
            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            auc = roc_auc_score(
                y_test,
                model.predict_proba(X_test)[:, 1]
            )

            # Сохранение результатов
            results.append({
                "model": name,
                "accuracy": acc,
                "auc": auc
            })
            trained_models[name] = model

            # Логирование
            logger.info(f"✅ {name}: Accuracy={acc:.3f}, AUC={auc:.3f}")

        except Exception as e:
            logger.error(f"❌ Ошибка при обучении {name}: {e}")
            continue

    return {
        "results": results,
        "X_test": X_test,
        "y_test": y_test,
        "trained_models": trained_models
    }


def generate_roc_auc_plot(
        X_test,
        y_test,
        trained_models,
        filename='reports/images/roc_auc.png'
):
    """
    Генерирует и сохраняет график ROC-AUC кривых для всех моделей.

    График показывает:
        - TPR (True Positive Rate) vs FPR (False Positive Rate)
        - Площадь под кривой (AUC) для каждой модели
        - Случайный классификатор (диагональ)

    Args:
        X_test (pd.DataFrame or np.ndarray): Тестовые признаки
        y_test (pd.Series or np.ndarray): Истинные метки
        trained_models (dict): Словарь обученных моделей
        filename (str or Path): Путь для сохранения изображения

    Returns:
        str: Абсолютный путь к сохранённому файлу

    Raises:
        ValueError: Если trained_models пуст
        ValueError: Если X_test или y_test пусты
    """
    if not trained_models:
        raise ValueError("Список моделей пуст. Нечего сравнивать.")
    if len(X_test) == 0 or len(y_test) == 0:
        raise ValueError("Тестовые данные пусты")

    # Создание директории
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Настройка графика
    plt.figure(figsize=(10, 8))
    plt.title(label="ROC-кривые моделей", fontsize=16)
    plt.xlabel(xlabel="Доля ложноположительных исходов (FPR)", fontsize=12)
    plt.ylabel(ylabel="Доля истинноположительных исходов (TPR)", fontsize=12)
    plt.grid(visible=True, alpha=0.3)

    # Построение кривых
    for name, model in trained_models.items():
        try:
            if hasattr(model, "predict_proba"):
                y_score = model.predict_proba(X_test)[:, 1]
            elif hasattr(model, "decision_function"):
                y_score = model.decision_function(X_test)
            else:
                logger.error(
                    f"⚠️ {name} не поддерживает predict_proba или decision_function — пропущено"
                )
                continue

            fpr, tpr, _ = roc_curve(y_test, y_score)
            auc = roc_auc_score(y_test, y_score)
            plt.plot(fpr, tpr, lw=2, label=f'{name} (AUC = {auc:.3f})')

        except Exception as e:
            logger.critical(
                f"❌ Не удалось построить ROC-кривую для {name}: {e}"
            )
            continue

    # Диагональ — случайный классификатор
    plt.plot(
        [0, 1], [0, 1],
        'k--',
        lw=2,
        label='Случайный классификатор (AUC = 0.500)'
    )

    # Легенда
    plt.legend(loc='lower right', fontsize=10)
    plt.tight_layout()

    # Сохранение
    plt.savefig(
        filename,
        bbox_inches='tight',
        dpi=150,
        facecolor='white'
    )
    plt.close()

    # Возвращаем абсолютный путь
    return str(Path(filename).resolve())

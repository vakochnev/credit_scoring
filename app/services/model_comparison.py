# services/model_comparison.py
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
import joblib
import os
from pathlib import Path

from shared.config import IMAGES_DIR, REPORTS_DIR


def compare_models(X, y):
    """
    Обучает и сравнивает несколько моделей.
    Возвращает результаты и обученные модели.
    """
    from sklearn.ensemble import RandomForestClassifier
    from xgboost import XGBClassifier
    from catboost import CatBoostClassifier
    from lightgbm import LGBMClassifier
    from sklearn.ensemble import VotingClassifier

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    models = {
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
        "XGBoost": XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42),
        "LightGBM": LGBMClassifier(random_state=42),
        "CatBoost": CatBoostClassifier(silent=True, random_state=42),
        "Ensemble": VotingClassifier([
            ('rf', RandomForestClassifier(n_estimators=50, random_state=42)),
            ('xgb', XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)),
            ('lgb', LGBMClassifier(random_state=42))
        ], voting='soft')
    }

    results = []
    trained_models = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
        results.append({
            "model": name,
            "accuracy": acc,
            "auc": auc
        })
        trained_models[name] = model

    return {
        "results": results,
        "X_test": X_test,
        "y_test": y_test,
        "trained_models": trained_models
    }


def generate_roc_auc_plot(X_test, y_test, trained_models, filename='reports/images/roc_auc.png'):

    plt.figure(figsize=(10, 8))

    for name, model in trained_models.items():
        if hasattr(model, "predict_proba"):
            y_score = model.predict_proba(X_test)[:, 1]
        else:
            y_score = model.decision_function(X_test)
        fpr, tpr, _ = roc_curve(y_test, y_score)
        auc = roc_auc_score(y_test, y_score)
        plt.plot(fpr, tpr, lw=2, label=f'{name} (AUC = {auc:.2f})')

    plt.plot([0, 1], [0, 1], 'k--', lw=2, label='Случайный классификатор')
    plt.xlabel('FPR')
    plt.ylabel('TPR')
    plt.title('ROC-кривые')
    plt.legend()
    plt.grid(True)

    plt.savefig(filename, bbox_inches='tight', dpi=150)
    plt.close()

    return os.path.abspath(filename) # Вернуть полный путь к файлу
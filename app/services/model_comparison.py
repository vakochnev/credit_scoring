# services/model_comparison.py
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

def compare_models(X_train, X_test, y_train, y_test):
    from sklearn.ensemble import RandomForestClassifier
    from xgboost import XGBClassifier
    from catboost import CatBoostClassifier
    from sklearn.ensemble import VotingClassifier

    models = {
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
        "XGBoost": XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42),
        "CatBoost": CatBoostClassifier(silent=True, random_state=42),
        "Ensemble": VotingClassifier([
            ('rf', RandomForestClassifier(n_estimators=50)),
            ('xgb', XGBClassifier(use_label_encoder=False, eval_metric='logloss')),
            ('cb', CatBoostClassifier(silent=True))
        ], voting='soft')
    }

    results = []
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

    return results


def generate_comparison_plot(results, filename="reports/model_comparison.png"):
    df = pd.DataFrame(results)
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(df))
    width = 0.35

    ax.bar(x - width/2, df['accuracy'], width, label='Accuracy', color='skyblue')
    ax.bar(x + width/2, df['auc'], width, label='AUC-ROC', color='lightcoral')

    ax.set_ylabel('Метрика')
    ax.set_title('Сравнение моделей')
    ax.set_xticks(x)
    ax.set_xticklabels(df['model'])
    ax.legend()

    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()

    return filename
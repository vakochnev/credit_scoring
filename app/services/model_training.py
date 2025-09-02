from sklearn.ensemble import VotingClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier
import joblib

from shared.config import (
    ENSEMBLE_MODEL_PATH, FEATURE_NAMES_PATH, BACKGROUND_DATA_PATH
)


def train_ensemble_model(X, y):
    model = VotingClassifier(
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
                'cb',
                CatBoostClassifier(
                    silent=True,
                    random_state=42
                )
            )
        ],
        voting='soft'
    )
    model.fit(X, y)

    joblib.dump(model, ENSEMBLE_MODEL_PATH)
    joblib.dump(X.columns.tolist(), FEATURE_NAMES_PATH)
    joblib.dump(X.sample(100, random_state=42), BACKGROUND_DATA_PATH)

    return {
        "model": "Ensemble (RF + XGBoost + CatBoost)",
        "accuracy": model.score(X, y)
    }
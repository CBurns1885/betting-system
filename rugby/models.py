#!/usr/bin/env python3
"""
Rugby Union Betting Models

Trains ensemble ML models for rugby match prediction.
Handles 3-way outcome (Home/Draw/Away).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, classification_report
from sklearn.calibration import CalibratedClassifierCV

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None

from config import (
    FEATURES_PARQUET, MODEL_ARTIFACTS_DIR, RANDOM_SEED,
    PRIMARY_TARGETS, log_header
)
from progress_utils import Timer

class RugbyModelTrainer:
    """Trains and manages rugby betting models"""

    def __init__(self, random_seed: int = RANDOM_SEED):
        self.random_seed = random_seed
        self.models = {}
        self.model_dir = MODEL_ARTIFACTS_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def get_base_models(self, num_classes: int = 3) -> Dict[str, Any]:
        """Get base models for ensemble"""
        models = {
            'logistic': LogisticRegression(
                max_iter=1000,
                random_state=self.random_seed,
                multi_class='multinomial'  # For 3-way classification
            ),
            'random_forest': RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_split=20,
                random_state=self.random_seed,
                n_jobs=-1
            ),
            'gradient_boost': GradientBoostingClassifier(
                n_estimators=150,
                max_depth=5,
                learning_rate=0.1,
                random_state=self.random_seed
            ),
        }

        if XGBClassifier:
            models['xgboost'] = XGBClassifier(
                n_estimators=150,
                max_depth=6,
                learning_rate=0.1,
                random_state=self.random_seed,
                eval_metric='mlogloss',
                use_label_encoder=False,
                objective='multi:softprob' if num_classes > 2 else 'binary:logistic',
                num_class=num_classes if num_classes > 2 else None
            )

        if LGBMClassifier:
            models['lightgbm'] = LGBMClassifier(
                n_estimators=150,
                max_depth=7,
                learning_rate=0.1,
                random_state=self.random_seed,
                verbose=-1,
                objective='multiclass' if num_classes > 2 else 'binary',
                num_class=num_classes if num_classes > 2 else None
            )

        return models

    def prepare_data(self, df: pd.DataFrame, target_col: str = 'target_winner') -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """Prepare features and target"""
        exclude_cols = ['match_id', 'date', 'home_team', 'away_team',
                       'target_winner', 'target_total_points', 'target_points_diff']
        feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[feature_cols].copy()
        y = df[target_col].copy() if target_col in df.columns else None

        X = X.fillna(X.median())

        return X, y, feature_cols

    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series,
                   X_val: pd.DataFrame = None, y_val: pd.Series = None,
                   market: str = "MATCH_WINNER") -> Dict[str, Any]:
        """Train ensemble of models"""
        log_header(f"Training Models for {market}")

        # Determine number of classes
        num_classes = len(y_train.unique())
        print(f"Number of classes: {num_classes}")
        print(f"Class distribution: {y_train.value_counts().to_dict()}")

        base_models = self.get_base_models(num_classes=num_classes)
        trained_models = {}
        scores = {}

        with Timer(f"Training {len(base_models)} models"):
            for name, model in base_models.items():
                print(f"\n  Training {name}...")

                model.fit(X_train, y_train)

                # Calibrate probabilities
                calibrated = CalibratedClassifierCV(model, cv=3, method='isotonic')
                calibrated.fit(X_train, y_train)

                trained_models[name] = calibrated

                # Evaluate
                train_preds = calibrated.predict(X_train)
                train_proba = calibrated.predict_proba(X_train)
                train_acc = accuracy_score(y_train, train_preds)
                train_logloss = log_loss(y_train, train_proba)

                scores[name] = {
                    'train_accuracy': train_acc,
                    'train_logloss': train_logloss,
                }

                print(f"    Train Accuracy: {train_acc:.4f}")
                print(f"    Train Log Loss: {train_logloss:.4f}")

                if X_val is not None and y_val is not None:
                    val_preds = calibrated.predict(X_val)
                    val_proba = calibrated.predict_proba(X_val)
                    val_acc = accuracy_score(y_val, val_preds)
                    val_logloss = log_loss(y_val, val_proba)

                    scores[name]['val_accuracy'] = val_acc
                    scores[name]['val_logloss'] = val_logloss

                    print(f"    Val Accuracy: {val_acc:.4f}")
                    print(f"    Val Log Loss: {val_logloss:.4f}")

        trained_models['ensemble'] = trained_models

        self.models[market] = trained_models

        print(f"\n✅ Trained {len(trained_models)-1} models for {market}")

        return trained_models

    def save_models(self, market: str = "MATCH_WINNER"):
        """Save trained models"""
        if market not in self.models:
            return

        models = self.models[market]

        for name, model in models.items():
            if name != 'ensemble':
                model_file = self.model_dir / f"rugby_{market.lower()}_{name}.pkl"
                joblib.dump(model, model_file)
                print(f"  ✅ Saved {name} to {model_file}")

    def load_models(self, market: str = "MATCH_WINNER") -> Dict[str, Any]:
        """Load trained models"""
        models = {}

        for model_file in self.model_dir.glob(f"rugby_{market.lower()}_*.pkl"):
            name = model_file.stem.replace(f"rugby_{market.lower()}_", "")
            models[name] = joblib.load(model_file)
            print(f"  ✅ Loaded {name}")

        if models:
            models['ensemble'] = models
            self.models[market] = models

        return models

    def predict(self, X: pd.DataFrame, market: str = "MATCH_WINNER") -> np.ndarray:
        """Make predictions using ensemble"""
        if market not in self.models:
            self.load_models(market)

        models = self.models[market]

        all_probas = []
        for name, model in models.items():
            if name != 'ensemble':
                proba = model.predict_proba(X)
                all_probas.append(proba)

        ensemble_proba = np.mean(all_probas, axis=0)

        return ensemble_proba


def main():
    """Train rugby models"""
    log_header("Rugby Union Model Training")

    if not FEATURES_PARQUET.exists():
        print("⚠️  Features file not found. Run features.py first.")
        return

    df = pd.read_parquet(FEATURES_PARQUET)
    df = df.dropna(subset=['target_winner'])
    print(f"Training on {len(df):,} completed matches")

    trainer = RugbyModelTrainer()

    X, y, feature_cols = trainer.prepare_data(df, target_col='target_winner')

    # Temporal split
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]

    print(f"\nTrain set: {len(X_train):,}")
    print(f"Val set: {len(X_val):,}")

    models = trainer.train_model(X_train, y_train, X_val, y_val, market="MATCH_WINNER")

    trainer.save_models(market="MATCH_WINNER")

    print("\n✅ Model training complete!")


if __name__ == "__main__":
    main()

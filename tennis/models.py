#!/usr/bin/env python3
"""
Tennis Betting Models

Trains ensemble ML models for tennis match prediction.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any
import joblib

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score, classification_report
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

class TennisModelTrainer:
    """Trains and manages tennis betting models"""

    def __init__(self, random_seed: int = RANDOM_SEED):
        self.random_seed = random_seed
        self.models = {}
        self.feature_importance = {}
        self.model_dir = MODEL_ARTIFACTS_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def get_base_models(self) -> Dict[str, Any]:
        """Get base models for ensemble"""
        models = {
            'logistic': LogisticRegression(
                max_iter=1000,
                random_state=self.random_seed,
                class_weight='balanced'
            ),
            'random_forest': RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=self.random_seed,
                n_jobs=-1,
                class_weight='balanced'
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
                eval_metric='logloss',
                use_label_encoder=False
            )

        if LGBMClassifier:
            models['lightgbm'] = LGBMClassifier(
                n_estimators=150,
                max_depth=7,
                learning_rate=0.1,
                random_state=self.random_seed,
                verbose=-1
            )

        return models

    def prepare_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """
        Prepare features and target for training

        Args:
            df: Features DataFrame

        Returns:
            Tuple of (X, y, feature_names)
        """
        # Identify feature columns (exclude identifiers and target)
        exclude_cols = ['match_id', 'date', 'player1', 'player2', 'target']
        feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[feature_cols].copy()
        y = df['target'].copy() if 'target' in df.columns else None

        # Handle missing values
        X = X.fillna(X.median())

        return X, y, feature_cols

    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series,
                   X_val: pd.DataFrame = None, y_val: pd.Series = None,
                   market: str = "MATCH_WINNER") -> Dict[str, Any]:
        """
        Train ensemble of models

        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features (optional)
            y_val: Validation target (optional)
            market: Market type

        Returns:
            Dictionary of trained models
        """
        log_header(f"Training Models for {market}")

        base_models = self.get_base_models()
        trained_models = {}
        scores = {}

        with Timer(f"Training {len(base_models)} models"):
            for name, model in base_models.items():
                print(f"\n  Training {name}...")

                # Train model
                model.fit(X_train, y_train)

                # Calibrate probabilities (important for betting!)
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

                # Feature importance (for tree-based models)
                if hasattr(model, 'feature_importances_'):
                    self.feature_importance[name] = model.feature_importances_

        # Create ensemble (simple average of probabilities)
        trained_models['ensemble'] = trained_models  # Store all for ensemble prediction

        # Store models
        self.models[market] = trained_models

        print(f"\n✅ Trained {len(trained_models)-1} models for {market}")
        print("\n📊 Model Scores:")
        for name, score in scores.items():
            print(f"  {name:15s} - Train Acc: {score['train_accuracy']:.4f}")

        return trained_models

    def save_models(self, market: str = "MATCH_WINNER"):
        """Save trained models to disk"""
        if market not in self.models:
            print(f"⚠️  No trained models found for {market}")
            return

        models = self.models[market]

        for name, model in models.items():
            if name != 'ensemble':  # Don't save ensemble separately
                model_file = self.model_dir / f"tennis_{market.lower()}_{name}.pkl"
                joblib.dump(model, model_file)
                print(f"  ✅ Saved {name} to {model_file}")

        print(f"\n✅ All models saved to {self.model_dir}")

    def load_models(self, market: str = "MATCH_WINNER") -> Dict[str, Any]:
        """Load trained models from disk"""
        models = {}

        for model_file in self.model_dir.glob(f"tennis_{market.lower()}_*.pkl"):
            name = model_file.stem.replace(f"tennis_{market.lower()}_", "")
            models[name] = joblib.load(model_file)
            print(f"  ✅ Loaded {name}")

        if models:
            models['ensemble'] = models  # Add ensemble
            self.models[market] = models

        return models

    def predict(self, X: pd.DataFrame, market: str = "MATCH_WINNER") -> np.ndarray:
        """
        Make predictions using ensemble

        Args:
            X: Features DataFrame
            market: Market type

        Returns:
            Array of probabilities [prob_player1_wins, prob_player2_wins]
        """
        if market not in self.models:
            print(f"⚠️  No models found for {market}. Loading from disk...")
            self.load_models(market)

        models = self.models[market]

        # Get predictions from each model (excluding 'ensemble' key)
        all_probas = []
        for name, model in models.items():
            if name != 'ensemble':
                proba = model.predict_proba(X)
                all_probas.append(proba)

        # Ensemble: average probabilities
        ensemble_proba = np.mean(all_probas, axis=0)

        return ensemble_proba


def main():
    """Train tennis betting models"""
    log_header("Tennis Model Training")

    # Load features
    if not FEATURES_PARQUET.exists():
        print("⚠️  Features file not found. Run features.py first.")
        return

    print(f"Loading features from {FEATURES_PARQUET}")
    df = pd.read_parquet(FEATURES_PARQUET)
    print(f"Loaded {len(df):,} matches with {len(df.columns)} columns")

    # Filter complete matches with target
    df = df.dropna(subset=['target'])
    print(f"Training on {len(df):,} completed matches")

    # Initialize trainer
    trainer = TennisModelTrainer()

    # Prepare data
    X, y, feature_cols = trainer.prepare_data(df)
    print(f"\nFeatures: {len(feature_cols)}")
    print(f"Target distribution: {y.value_counts().to_dict()}")

    # Split data (temporal split to avoid lookahead bias)
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]

    print(f"\nTrain set: {len(X_train):,} matches")
    print(f"Val set: {len(X_val):,} matches")

    # Train models
    models = trainer.train_model(X_train, y_train, X_val, y_val, market="MATCH_WINNER")

    # Save models
    trainer.save_models(market="MATCH_WINNER")

    print("\n✅ Model training complete!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
NFL Betting Models

Trains machine learning models for NFL betting markets:
1. Moneyline (Home Win / Away Win)
2. Spread (Cover / No Cover)
3. Totals (Over / Under)

Uses ensemble of models:
- Random Forest
- XGBoost
- LightGBM
- Logistic Regression
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import log_loss, accuracy_score, roc_auc_score
from sklearn.calibration import CalibratedClassifierCV

# Optional advanced models
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    lgb.set_option('verbosity', -1)
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

from config import (
    MODEL_ARTIFACTS_DIR, PROCESSED_DIR, RANDOM_SEED,
    PRIMARY_MARKETS, log_header
)
from progress_utils import Timer, heartbeat


@dataclass
class ModelResult:
    """Results from a trained model"""
    model_name: str
    market: str
    train_accuracy: float
    val_accuracy: float
    train_logloss: float
    val_logloss: float
    feature_importance: Dict[str, float]


class NFLModelTrainer:
    """Train models for NFL betting markets"""

    def __init__(self, features_df: pd.DataFrame):
        """
        Initialize trainer with feature data

        Args:
            features_df: DataFrame with features and targets
        """
        self.features_df = features_df
        self.models = {}
        self.scalers = {}
        self.feature_names = []

    def prepare_data(self, market: str, test_size: float = 0.2) -> Tuple:
        """
        Prepare features and targets for a specific market

        Args:
            market: One of MONEYLINE, SPREAD, TOTAL
            test_size: Fraction for validation set

        Returns:
            X_train, X_val, y_train, y_val, feature_names
        """
        df = self.features_df.copy()

        # Remove games without results
        df = df[df['result'].notna()].copy()

        # Define target based on market
        if market == "MONEYLINE":
            # Binary: Home Win (1) vs Away Win (0)
            df['target'] = (df['result'] == 'H').astype(int)

        elif market == "SPREAD":
            # For spread, we need to know if home team covered
            # Assuming spread is in the data or we calculate from historical avg
            # For now, use simple win/loss
            df['target'] = (df['spread_result'] > 0).astype(int)

        elif market == "TOTAL":
            # Over/Under - need a line (e.g., 45.5)
            # For now, use median total as the line
            median_total = df['total_score'].median()
            df['target'] = (df['total_score'] > median_total).astype(int)

        else:
            raise ValueError(f"Unknown market: {market}")

        # Select features (exclude targets and identifiers)
        exclude_cols = [
            'season', 'week', 'home_team', 'away_team',
            'result', 'home_score', 'away_score', 'total_score',
            'spread_result', 'target', 'date'
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        # Handle missing values
        df[feature_cols] = df[feature_cols].fillna(df[feature_cols].median())

        X = df[feature_cols].values
        y = df['target'].values

        # Split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=test_size, random_state=RANDOM_SEED, stratify=y
        )

        self.feature_names = feature_cols

        return X_train, X_val, y_train, y_val, feature_cols

    def train_model(self, model_type: str, market: str, X_train, X_val, y_train, y_val) -> ModelResult:
        """
        Train a single model

        Args:
            model_type: 'rf', 'xgb', 'lgb', 'logistic', 'gb'
            market: Market name
            X_train, X_val, y_train, y_val: Training data

        Returns:
            ModelResult with performance metrics
        """
        heartbeat(f"Training {model_type} for {market}")

        # Create model
        if model_type == 'rf':
            base_model = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=RANDOM_SEED,
                n_jobs=-1
            )

        elif model_type == 'xgb' and HAS_XGB:
            base_model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=RANDOM_SEED,
                n_jobs=-1,
                eval_metric='logloss'
            )

        elif model_type == 'lgb' and HAS_LGB:
            base_model = lgb.LGBMClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=RANDOM_SEED,
                n_jobs=-1,
                verbose=-1
            )

        elif model_type == 'gb':
            base_model = GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                random_state=RANDOM_SEED
            )

        elif model_type == 'logistic':
            base_model = LogisticRegression(
                max_iter=1000,
                random_state=RANDOM_SEED,
                n_jobs=-1
            )

        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Build pipeline with scaling and imputation
        pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('classifier', base_model)
        ])

        # Train
        pipeline.fit(X_train, y_train)

        # Calibrate probabilities
        calibrated = CalibratedClassifierCV(pipeline, method='isotonic', cv='prefit')
        calibrated.fit(X_val, y_val)

        # Predict
        y_train_pred = calibrated.predict(X_train)
        y_val_pred = calibrated.predict(X_val)

        y_train_proba = calibrated.predict_proba(X_train)
        y_val_proba = calibrated.predict_proba(X_val)

        # Metrics
        train_acc = accuracy_score(y_train, y_train_pred)
        val_acc = accuracy_score(y_val, y_val_pred)

        train_ll = log_loss(y_train, y_train_proba)
        val_ll = log_loss(y_val, y_val_proba)

        # Feature importance
        importance = {}
        if hasattr(base_model, 'feature_importances_'):
            for name, imp in zip(self.feature_names, base_model.feature_importances_):
                importance[name] = float(imp)

        print(f"  ✅ {model_type}: Val Acc={val_acc:.3f}, Val LogLoss={val_ll:.3f}")

        # Save model
        model_key = f"{market}_{model_type}"
        self.models[model_key] = calibrated

        return ModelResult(
            model_name=model_type,
            market=market,
            train_accuracy=train_acc,
            val_accuracy=val_acc,
            train_logloss=train_ll,
            val_logloss=val_ll,
            feature_importance=importance
        )

    def train_all_markets(self, model_types: List[str] = None) -> Dict[str, List[ModelResult]]:
        """
        Train all models for all markets

        Args:
            model_types: List of model types to train (default: all available)

        Returns:
            Dict of market -> list of ModelResults
        """
        if model_types is None:
            model_types = ['rf', 'logistic', 'gb']
            if HAS_XGB:
                model_types.append('xgb')
            if HAS_LGB:
                model_types.append('lgb')

        results = {}

        for market in PRIMARY_MARKETS:
            log_header(f"Training {market} Models")

            # Prepare data
            X_train, X_val, y_train, y_val, feature_names = self.prepare_data(market)

            print(f"  Training set: {len(X_train)} games")
            print(f"  Validation set: {len(X_val)} games")
            print(f"  Features: {len(feature_names)}")

            market_results = []

            for model_type in model_types:
                try:
                    result = self.train_model(
                        model_type, market,
                        X_train, X_val, y_train, y_val
                    )
                    market_results.append(result)

                except Exception as e:
                    print(f"  ⚠️  Error training {model_type}: {e}")

            results[market] = market_results

        return results

    def save_models(self, output_dir: Path = MODEL_ARTIFACTS_DIR):
        """Save all trained models"""
        output_dir.mkdir(parents=True, exist_ok=True)

        for model_name, model in self.models.items():
            model_path = output_dir / f"{model_name}.pkl"
            joblib.dump(model, model_path)
            print(f"  ✅ Saved {model_name} to {model_path}")

    def load_models(self, input_dir: Path = MODEL_ARTIFACTS_DIR):
        """Load saved models"""
        model_files = list(input_dir.glob("*.pkl"))

        for model_path in model_files:
            model_name = model_path.stem
            self.models[model_name] = joblib.load(model_path)
            print(f"  ✅ Loaded {model_name}")


class NFLEnsemblePredictor:
    """Ensemble predictions from multiple models"""

    def __init__(self, models: Dict[str, any]):
        """
        Initialize with trained models

        Args:
            models: Dict of model_name -> trained model
        """
        self.models = models

    def predict(self, X: np.ndarray, market: str, method: str = 'average') -> np.ndarray:
        """
        Generate ensemble predictions

        Args:
            X: Features
            market: Market to predict
            method: 'average' or 'weighted'

        Returns:
            Array of probabilities
        """
        # Get all models for this market
        market_models = {
            name: model for name, model in self.models.items()
            if name.startswith(market)
        }

        if not market_models:
            raise ValueError(f"No models found for market: {market}")

        # Get predictions from each model
        predictions = []

        for name, model in market_models.items():
            proba = model.predict_proba(X)
            predictions.append(proba)

        # Ensemble
        if method == 'average':
            ensemble_proba = np.mean(predictions, axis=0)

        elif method == 'weighted':
            # Weight by model performance (would need validation scores)
            # For now, just use average
            ensemble_proba = np.mean(predictions, axis=0)

        else:
            raise ValueError(f"Unknown ensemble method: {method}")

        return ensemble_proba


def train_nfl_models(features_path: str = None):
    """
    Main training function

    Args:
        features_path: Path to features parquet file
    """
    if features_path is None:
        features_path = PROCESSED_DIR / "features.parquet"

    log_header("NFL Model Training")

    # Load features
    print(f"📂 Loading features from {features_path}")
    features_df = pd.read_parquet(features_path)
    print(f"  ✅ Loaded {len(features_df)} games")

    # Train models
    with Timer("Training all models"):
        trainer = NFLModelTrainer(features_df)
        results = trainer.train_all_markets()

        # Save models
        print("\n💾 Saving models...")
        trainer.save_models()

    # Print summary
    print("\n📊 Training Summary:")
    for market, market_results in results.items():
        print(f"\n{market}:")
        for result in market_results:
            print(f"  {result.model_name}: "
                  f"Val Acc={result.val_accuracy:.3f}, "
                  f"Val LogLoss={result.val_logloss:.3f}")

    print("\n✅ Training complete!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Train NFL betting models')
    parser.add_argument('--features', type=str,
                       help='Path to features parquet file')

    args = parser.parse_args()

    train_nfl_models(args.features)

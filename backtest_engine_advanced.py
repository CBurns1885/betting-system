#!/usr/bin/env python3
"""
backtest_engine_advanced.py
Advanced backtesting engine with per-market model optimization
Finds the best model/ensemble for each betting market and optimizes hyperparameters
"""

import os
import sys
import json
import pickle
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score, precision_score, recall_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from scipy import stats

# Optional advanced models
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

try:
    from catboost import CatBoostClassifier
    HAS_CAT = True
except ImportError:
    HAS_CAT = False

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    print("Install optuna for hyperparameter optimization: pip install optuna")

warnings.filterwarnings('ignore')

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ModelPerformance:
    """Store model performance metrics for a specific market"""
    model_name: str
    market: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    log_loss_score: float
    roc_auc: float
    profit_loss: float
    roi: float
    best_threshold: float
    total_predictions: int
    correct_predictions: int
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)

@dataclass
class EnsembleWeights:
    """Optimal ensemble weights for a specific market"""
    market: str
    model_weights: Dict[str, float]
    performance: ModelPerformance
    validation_score: float

@dataclass
class MarketOptimization:
    """Complete optimization results for a market"""
    market: str
    best_model: str
    best_ensemble: EnsembleWeights
    all_model_performances: List[ModelPerformance]
    recommended_config: Dict[str, Any]
    expected_accuracy: float
    expected_roi: float

# ============================================================================
# BETTING MARKETS DEFINITION
# ============================================================================

BETTING_MARKETS = {
    # Traditional Markets
    'match_result': {
        'type': 'multiclass',
        'classes': ['H', 'D', 'A'],
        'target_column': 'FTR',
        'description': 'Match Result (1X2)'
    },
    'over_under_25': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'Over25',
        'description': 'Over/Under 2.5 Goals'
    },
    'over_under_15': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'Over15',
        'description': 'Over/Under 1.5 Goals'
    },
    'over_under_35': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'Over35',
        'description': 'Over/Under 3.5 Goals'
    },
    'btts': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'BTTS',
        'description': 'Both Teams to Score'
    },
    'double_chance_home': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'DC_Home',
        'description': 'Double Chance - Home/Draw'
    },
    'double_chance_away': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'DC_Away',
        'description': 'Double Chance - Away/Draw'
    },
    'asian_handicap_home_-05': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'AH_Home_-05',
        'description': 'Asian Handicap Home -0.5'
    },
    'asian_handicap_home_-15': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'AH_Home_-15',
        'description': 'Asian Handicap Home -1.5'
    },
    'correct_score_class': {
        'type': 'multiclass',
        'classes': ['0-0', '1-0', '0-1', '1-1', '2-1', '1-2', '2-0', '0-2', 'Other'],
        'target_column': 'CorrectScoreClass',
        'description': 'Correct Score Groups'
    },
    'total_goals_class': {
        'type': 'multiclass',
        'classes': ['0-1', '2-3', '4+'],
        'target_column': 'TotalGoalsClass',
        'description': 'Total Goals Categories'
    },
    'clean_sheet_home': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'CS_Home',
        'description': 'Clean Sheet Home'
    },
    'clean_sheet_away': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'CS_Away',
        'description': 'Clean Sheet Away'
    },
    'half_time_result': {
        'type': 'multiclass',
        'classes': ['H', 'D', 'A'],
        'target_column': 'HTR',
        'description': 'Half Time Result'
    },
    'win_to_nil_home': {
        'type': 'binary',
        'classes': [0, 1],
        'target_column': 'WTN_Home',
        'description': 'Home Win to Nil'
    },
}

# ============================================================================
# MODEL DEFINITIONS
# ============================================================================

class ModelFactory:
    """Factory class for creating and configuring models"""
    
    @staticmethod
    def get_base_models() -> Dict[str, Any]:
        """Get dictionary of base models with default parameters"""
        models = {
            'logistic_regression': LogisticRegression(
                max_iter=1000,
                random_state=42,
                n_jobs=-1
            ),
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            ),
            'extra_trees': ExtraTreesClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                random_state=42
            ),
            'neural_network': MLPClassifier(
                hidden_layer_sizes=(100, 50),
                max_iter=1000,
                random_state=42,
                early_stopping=True
            )
        }
        
        if HAS_XGB:
            models['xgboost'] = xgb.XGBClassifier(
                n_estimators=100,
                random_state=42,
                use_label_encoder=False,
                eval_metric='logloss'
            )
        
        if HAS_LGB:
            models['lightgbm'] = lgb.LGBMClassifier(
                n_estimators=100,
                random_state=42,
                verbosity=-1
            )
        
        if HAS_CAT:
            models['catboost'] = CatBoostClassifier(
                iterations=100,
                random_state=42,
                verbose=False
            )
        
        return models
    
    @staticmethod
    def get_hyperparameter_space(model_name: str, market_type: str) -> Dict:
        """Get hyperparameter search space for a model"""
        
        if model_name == 'logistic_regression':
            return {
                'C': [0.001, 0.01, 0.1, 1.0, 10.0, 100.0],
                'penalty': ['l1', 'l2'],
                'solver': ['liblinear', 'saga']
            }
        
        elif model_name == 'random_forest':
            return {
                'n_estimators': [50, 100, 200, 300],
                'max_depth': [5, 10, 15, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'max_features': ['sqrt', 'log2', 0.5]
            }
        
        elif model_name == 'extra_trees':
            return {
                'n_estimators': [50, 100, 200, 300],
                'max_depth': [5, 10, 15, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
        
        elif model_name == 'gradient_boosting':
            return {
                'n_estimators': [50, 100, 150, 200],
                'learning_rate': [0.01, 0.05, 0.1, 0.15],
                'max_depth': [3, 5, 7, 9],
                'subsample': [0.7, 0.8, 0.9, 1.0]
            }
        
        elif model_name == 'xgboost' and HAS_XGB:
            return {
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 5, 7, 9],
                'learning_rate': [0.01, 0.05, 0.1, 0.3],
                'subsample': [0.7, 0.8, 0.9],
                'colsample_bytree': [0.7, 0.8, 0.9]
            }
        
        elif model_name == 'lightgbm' and HAS_LGB:
            return {
                'n_estimators': [100, 200, 300],
                'num_leaves': [31, 50, 100],
                'learning_rate': [0.01, 0.05, 0.1, 0.3],
                'feature_fraction': [0.7, 0.8, 0.9],
                'bagging_fraction': [0.7, 0.8, 0.9]
            }
        
        elif model_name == 'catboost' and HAS_CAT:
            return {
                'iterations': [100, 200, 300],
                'depth': [4, 6, 8],
                'learning_rate': [0.01, 0.05, 0.1],
                'l2_leaf_reg': [1, 3, 5, 7]
            }
        
        elif model_name == 'neural_network':
            return {
                'hidden_layer_sizes': [(50,), (100,), (100, 50), (150, 100, 50)],
                'activation': ['relu', 'tanh'],
                'alpha': [0.0001, 0.001, 0.01],
                'learning_rate_init': [0.001, 0.01, 0.1]
            }
        
        return {}

# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

class AdvancedBacktestEngine:
    """Advanced backtesting engine with per-market optimization"""
    
    def __init__(self, data_path: Optional[str] = None):
        """Initialize backtesting engine"""
        self.data_path = data_path
        self.data = None
        self.results = {}
        self.model_factory = ModelFactory()
        self.best_configs = {}
        
    def load_data(self, data_path: Optional[str] = None) -> pd.DataFrame:
        """Load historical data for backtesting"""
        if data_path:
            self.data_path = data_path
        
        print("Loading historical data...")
        
        # Try to load from parquet or CSV
        if Path(self.data_path).suffix == '.parquet':
            self.data = pd.read_parquet(self.data_path)
        else:
            self.data = pd.read_csv(self.data_path)
        
        # Create derived target columns if not present
        self._create_target_columns()
        
        print(f"Loaded {len(self.data)} matches")
        return self.data
    
    def _create_target_columns(self):
        """Create target columns for all markets"""
        df = self.data
        
        # Basic targets
        if 'FTHG' in df.columns and 'FTAG' in df.columns:
            # Over/Under markets
            total_goals = df['FTHG'] + df['FTAG']
            df['Over15'] = (total_goals > 1.5).astype(int)
            df['Over25'] = (total_goals > 2.5).astype(int)
            df['Over35'] = (total_goals > 3.5).astype(int)
            
            # BTTS
            df['BTTS'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)
            
            # Double Chance
            df['DC_Home'] = df['FTR'].isin(['H', 'D']).astype(int)
            df['DC_Away'] = df['FTR'].isin(['A', 'D']).astype(int)
            
            # Asian Handicap
            goal_diff = df['FTHG'] - df['FTAG']
            df['AH_Home_-05'] = (goal_diff > 0).astype(int)
            df['AH_Home_-15'] = (goal_diff > 1).astype(int)
            
            # Clean Sheets
            df['CS_Home'] = (df['FTAG'] == 0).astype(int)
            df['CS_Away'] = (df['FTHG'] == 0).astype(int)
            
            # Win to Nil
            df['WTN_Home'] = ((df['FTHG'] > df['FTAG']) & (df['FTAG'] == 0)).astype(int)
            
            # Correct Score Classes
            df['CorrectScoreClass'] = df.apply(self._classify_correct_score, axis=1)
            
            # Total Goals Classes
            df['TotalGoalsClass'] = pd.cut(
                total_goals,
                bins=[-1, 1.5, 3.5, 100],
                labels=['0-1', '2-3', '4+']
            )
        
        # Half-time result if available
        if 'HTR' not in df.columns and 'HTHG' in df.columns:
            df['HTR'] = df.apply(
                lambda x: 'H' if x['HTHG'] > x['HTAG'] else ('A' if x['HTHG'] < x['HTAG'] else 'D'),
                axis=1
            )
        
        self.data = df
    
    def _classify_correct_score(self, row) -> str:
        """Classify correct score into groups"""
        common_scores = ['0-0', '1-0', '0-1', '1-1', '2-1', '1-2', '2-0', '0-2']
        score = f"{int(row['FTHG'])}-{int(row['FTAG'])}"
        return score if score in common_scores else 'Other'
    
    def run_complete_backtest(self, 
                              test_size: float = 0.2,
                              n_splits: int = 5,
                              optimize_hyperparameters: bool = True,
                              n_jobs: int = -1) -> Dict[str, MarketOptimization]:
        """
        Run complete backtest for all markets and models
        
        Args:
            test_size: Proportion of data for final testing
            n_splits: Number of cross-validation splits
            optimize_hyperparameters: Whether to optimize hyperparameters
            n_jobs: Number of parallel jobs (-1 for all cores)
        
        Returns:
            Dictionary of MarketOptimization results per market
        """
        
        print("\n" + "="*80)
        print("STARTING COMPREHENSIVE BACKTESTING")
        print("="*80)
        
        # Split data into train and test
        split_idx = int(len(self.data) * (1 - test_size))
        train_data = self.data.iloc[:split_idx].copy()
        test_data = self.data.iloc[split_idx:].copy()
        
        print(f"\nData split:")
        print(f"  Training: {len(train_data)} matches")
        print(f"  Testing: {len(test_data)} matches")
        
        # Get feature columns (exclude targets and identifiers)
        exclude_cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTR', 'FTHG', 'FTAG', 
                       'HTHG', 'HTAG', 'HTR'] + list(BETTING_MARKETS.keys())
        feature_cols = [col for col in train_data.columns 
                       if col not in exclude_cols and not col.startswith('y_')]
        
        print(f"  Features: {len(feature_cols)}")
        
        optimization_results = {}
        
        # Process each market
        for market_name, market_config in BETTING_MARKETS.items():
            print(f"\n{'='*60}")
            print(f"ANALYZING MARKET: {market_config['description']}")
            print(f"{'='*60}")
            
            # Check if target column exists
            if market_config['target_column'] not in train_data.columns:
                print(f"  ⚠️ Target column '{market_config['target_column']}' not found, skipping...")
                continue
            
            # Prepare data for this market
            X_train = train_data[feature_cols].values
            y_train = train_data[market_config['target_column']].values
            X_test = test_data[feature_cols].values
            y_test = test_data[market_config['target_column']].values
            
            # Remove NaN values
            mask_train = ~np.isnan(y_train)
            X_train = X_train[mask_train]
            y_train = y_train[mask_train]
            
            mask_test = ~np.isnan(y_test)
            X_test = X_test[mask_test]
            y_test = y_test[mask_test]
            
            # Run optimization for this market
            market_optimization = self._optimize_market(
                market_name=market_name,
                market_config=market_config,
                X_train=X_train,
                y_train=y_train,
                X_test=X_test,
                y_test=y_test,
                feature_names=feature_cols,
                optimize_hyperparameters=optimize_hyperparameters,
                n_splits=n_splits,
                n_jobs=n_jobs
            )
            
            optimization_results[market_name] = market_optimization
            
            # Print summary for this market
            self._print_market_summary(market_optimization)
        
        # Save results
        self._save_results(optimization_results)
        
        # Generate final report
        self._generate_final_report(optimization_results)
        
        return optimization_results
    
    def _optimize_market(self,
                        market_name: str,
                        market_config: Dict,
                        X_train: np.ndarray,
                        y_train: np.ndarray,
                        X_test: np.ndarray,
                        y_test: np.ndarray,
                        feature_names: List[str],
                        optimize_hyperparameters: bool,
                        n_splits: int,
                        n_jobs: int) -> MarketOptimization:
        """Optimize models for a specific market"""
        
        print(f"\n  Testing {len(self.model_factory.get_base_models())} models...")
        
        model_performances = []
        base_models = self.model_factory.get_base_models()
        
        # Test each model
        for model_name, model in base_models.items():
            print(f"\n  📊 {model_name.upper()}")
            
            try:
                # Optimize hyperparameters if requested
                if optimize_hyperparameters and HAS_OPTUNA:
                    print(f"    Optimizing hyperparameters...")
                    best_params = self._optimize_hyperparameters(
                        model_name=model_name,
                        market_type=market_config['type'],
                        X_train=X_train,
                        y_train=y_train,
                        n_splits=n_splits
                    )
                    
                    # Update model with best parameters
                    model.set_params(**best_params)
                    print(f"    Best params: {best_params}")
                else:
                    best_params = {}
                
                # Train and evaluate model
                performance = self._evaluate_model(
                    model=model,
                    model_name=model_name,
                    market_name=market_name,
                    X_train=X_train,
                    y_train=y_train,
                    X_test=X_test,
                    y_test=y_test,
                    feature_names=feature_names,
                    hyperparameters=best_params
                )
                
                model_performances.append(performance)
                
                print(f"    Accuracy: {performance.accuracy:.3f}")
                print(f"    ROI: {performance.roi:.1f}%")
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                continue
        
        # Find best single model
        best_model_perf = max(model_performances, key=lambda x: x.accuracy)
        best_model_name = best_model_perf.model_name
        
        # Optimize ensemble weights
        print(f"\n  🔄 Optimizing ensemble weights...")
        ensemble_weights = self._optimize_ensemble_weights(
            model_performances=model_performances,
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            market_name=market_name
        )
        
        # Create optimization result
        optimization = MarketOptimization(
            market=market_name,
            best_model=best_model_name,
            best_ensemble=ensemble_weights,
            all_model_performances=model_performances,
            recommended_config={
                'use_ensemble': ensemble_weights.validation_score > best_model_perf.accuracy,
                'ensemble_weights': ensemble_weights.model_weights if ensemble_weights.validation_score > best_model_perf.accuracy else None,
                'single_model': best_model_name if ensemble_weights.validation_score <= best_model_perf.accuracy else None,
                'hyperparameters': best_model_perf.hyperparameters
            },
            expected_accuracy=max(ensemble_weights.validation_score, best_model_perf.accuracy),
            expected_roi=max(ensemble_weights.performance.roi, best_model_perf.roi)
        )
        
        return optimization
    
    def _optimize_hyperparameters(self,
                                 model_name: str,
                                 market_type: str,
                                 X_train: np.ndarray,
                                 y_train: np.ndarray,
                                 n_splits: int = 3) -> Dict:
        """Optimize hyperparameters using Optuna"""
        
        if not HAS_OPTUNA:
            return {}
        
        # Get hyperparameter space
        param_space = self.model_factory.get_hyperparameter_space(model_name, market_type)
        
        if not param_space:
            return {}
        
        # Define objective function
        def objective(trial):
            params = {}
            for param_name, param_values in param_space.items():
                if isinstance(param_values[0], (int, float)):
                    if isinstance(param_values[0], int):
                        params[param_name] = trial.suggest_int(
                            param_name, 
                            min(param_values), 
                            max(param_values)
                        )
                    else:
                        params[param_name] = trial.suggest_float(
                            param_name,
                            min(param_values),
                            max(param_values)
                        )
                else:
                    params[param_name] = trial.suggest_categorical(param_name, param_values)
            
            # Create model with suggested parameters
            model_class = self.model_factory.get_base_models()[model_name].__class__
            model = model_class(**params, random_state=42)
            
            # Cross-validation score
            tscv = TimeSeriesSplit(n_splits=n_splits)
            scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring='accuracy')
            
            return scores.mean()
        
        # Run optimization
        study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(objective, n_trials=20, n_jobs=1, show_progress_bar=False)
        
        return study.best_params
    
    def _evaluate_model(self,
                       model: Any,
                       model_name: str,
                       market_name: str,
                       X_train: np.ndarray,
                       y_train: np.ndarray,
                       X_test: np.ndarray,
                       y_test: np.ndarray,
                       feature_names: List[str],
                       hyperparameters: Dict) -> ModelPerformance:
        """Evaluate a model's performance"""
        
        # Train model
        model.fit(X_train, y_train)
        
        # Get predictions
        y_pred = model.predict(X_test)
        
        # Get probabilities if available
        try:
            y_proba = model.predict_proba(X_test)
            if len(y_proba.shape) > 1 and y_proba.shape[1] > 1:
                # Multiclass - use max probability
                y_proba_positive = y_proba.max(axis=1)
            else:
                y_proba_positive = y_proba[:, 1] if y_proba.shape[1] == 2 else y_proba
        except:
            y_proba_positive = y_pred
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        
        # Handle multiclass vs binary metrics
        unique_classes = np.unique(y_test)
        if len(unique_classes) > 2:
            # Multiclass
            precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
            try:
                roc_auc = roc_auc_score(y_test, y_proba, multi_class='ovr', average='weighted')
            except:
                roc_auc = 0.5
        else:
            # Binary
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            try:
                roc_auc = roc_auc_score(y_test, y_proba_positive)
            except:
                roc_auc = 0.5
        
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        try:
            log_loss_score = log_loss(y_test, y_proba) if hasattr(model, 'predict_proba') else 0
        except:
            log_loss_score = 0
        
        # Calculate profit/loss (simplified)
        profit_loss, roi = self._calculate_profit(y_test, y_pred, y_proba_positive)
        
        # Get feature importance if available
        feature_importance = {}
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            feature_importance = dict(zip(feature_names[:len(importance)], importance))
            # Keep top 10
            feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return ModelPerformance(
            model_name=model_name,
            market=market_name,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            log_loss_score=log_loss_score,
            roc_auc=roc_auc,
            profit_loss=profit_loss,
            roi=roi,
            best_threshold=0.5,  # Could optimize this
            total_predictions=len(y_test),
            correct_predictions=int(accuracy * len(y_test)),
            hyperparameters=hyperparameters,
            feature_importance=feature_importance
        )
    
    def _calculate_profit(self, y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray) -> Tuple[float, float]:
        """Calculate profit/loss and ROI from predictions"""
        
        # Simplified betting simulation
        # Assume flat €10 stakes and average odds
        stake = 10
        avg_odds = 2.0  # This should come from actual odds data
        
        correct = (y_true == y_pred).sum()
        incorrect = len(y_true) - correct
        
        # Only bet when confidence > threshold
        confidence_threshold = 0.6
        if hasattr(y_proba, '__iter__'):
            high_confidence = y_proba > confidence_threshold
            bets_placed = high_confidence.sum()
            correct_bets = ((y_true == y_pred) & high_confidence).sum()
        else:
            bets_placed = len(y_true)
            correct_bets = correct
        
        if bets_placed > 0:
            total_staked = bets_placed * stake
            total_returns = correct_bets * stake * avg_odds
            profit_loss = total_returns - total_staked
            roi = (profit_loss / total_staked) * 100 if total_staked > 0 else 0
        else:
            profit_loss = 0
            roi = 0
        
        return profit_loss, roi
    
    def _optimize_ensemble_weights(self,
                                  model_performances: List[ModelPerformance],
                                  X_train: np.ndarray,
                                  y_train: np.ndarray,
                                  X_test: np.ndarray,
                                  y_test: np.ndarray,
                                  market_name: str) -> EnsembleWeights:
        """Optimize ensemble weights for maximum accuracy"""
        
        # Train all models and get predictions
        models = self.model_factory.get_base_models()
        predictions = {}
        
        for perf in model_performances:
            model_name = perf.model_name
            if model_name in models:
                model = models[model_name]
                
                # Apply hyperparameters if available
                if perf.hyperparameters:
                    try:
                        model.set_params(**perf.hyperparameters)
                    except:
                        pass
                
                # Train and predict
                model.fit(X_train, y_train)
                
                # Get probabilities
                try:
                    if hasattr(model, 'predict_proba'):
                        proba = model.predict_proba(X_test)
                        if len(proba.shape) > 1 and proba.shape[1] > 1:
                            predictions[model_name] = proba
                        else:
                            predictions[model_name] = proba[:, 1]
                    else:
                        predictions[model_name] = model.predict(X_test)
                except:
                    predictions[model_name] = model.predict(X_test)
        
        # Optimize weights using grid search
        best_weights = {}
        best_score = 0
        
        # Generate weight combinations (sum to 1)
        weight_options = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        
        for weights in self._generate_weight_combinations(len(predictions), weight_options):
            if abs(sum(weights) - 1.0) > 0.001:
                continue
            
            # Create ensemble prediction
            ensemble_pred = np.zeros_like(y_test, dtype=float)
            
            for (model_name, pred), weight in zip(predictions.items(), weights):
                if len(pred.shape) > 1 and pred.shape[1] > 1:
                    # Multiclass - weighted average of probabilities
                    weighted_pred = pred * weight
                    ensemble_pred = pred.argmax(axis=1) if weight == 1.0 else ensemble_pred
                else:
                    ensemble_pred += pred * weight
            
            # Evaluate ensemble
            if len(np.unique(y_test)) > 2:
                # Multiclass - use argmax
                ensemble_final = ensemble_pred.astype(int)
            else:
                # Binary - threshold
                ensemble_final = (ensemble_pred > 0.5).astype(int)
            
            score = accuracy_score(y_test, ensemble_final)
            
            if score > best_score:
                best_score = score
                best_weights = dict(zip(predictions.keys(), weights))
        
        # Create ensemble performance
        ensemble_perf = ModelPerformance(
            model_name='ensemble',
            market=market_name,
            accuracy=best_score,
            precision=0,
            recall=0,
            f1_score=0,
            log_loss_score=0,
            roc_auc=0,
            profit_loss=0,
            roi=0,
            best_threshold=0.5,
            total_predictions=len(y_test),
            correct_predictions=int(best_score * len(y_test)),
            hyperparameters=best_weights,
            feature_importance={}
        )
        
        return EnsembleWeights(
            market=market_name,
            model_weights=best_weights,
            performance=ensemble_perf,
            validation_score=best_score
        )
    
    def _generate_weight_combinations(self, n_models: int, weight_options: List[float]):
        """Generate weight combinations that sum to 1"""
        if n_models == 1:
            yield [1.0]
        elif n_models == 2:
            for w1 in weight_options:
                w2 = 1.0 - w1
                if w2 >= 0:
                    yield [w1, w2]
        else:
            # For more models, use a simplified approach
            # Equal weights as baseline
            base_weight = 1.0 / n_models
            yield [base_weight] * n_models
            
            # Some variations
            for i in range(n_models):
                weights = [0.1] * n_models
                weights[i] = 1.0 - 0.1 * (n_models - 1)
                yield weights
    
    def _print_market_summary(self, optimization: MarketOptimization):
        """Print summary for a market optimization"""
        print(f"\n  ✅ MARKET OPTIMIZATION COMPLETE: {optimization.market}")
        print(f"  {'='*50}")
        print(f"  Best Single Model: {optimization.best_model}")
        print(f"  Best Model Accuracy: {max(p.accuracy for p in optimization.all_model_performances):.3f}")
        print(f"  Ensemble Accuracy: {optimization.best_ensemble.validation_score:.3f}")
        print(f"  Expected Accuracy: {optimization.expected_accuracy:.3f}")
        print(f"  Expected ROI: {optimization.expected_roi:.1f}%")
        
        if optimization.recommended_config['use_ensemble']:
            print(f"  Recommendation: USE ENSEMBLE")
            print(f"  Weights:")
            for model, weight in optimization.best_ensemble.model_weights.items():
                if weight > 0:
                    print(f"    - {model}: {weight:.2f}")
        else:
            print(f"  Recommendation: USE SINGLE MODEL ({optimization.best_model})")
    
    def _save_results(self, optimization_results: Dict[str, MarketOptimization]):
        """Save optimization results to files"""
        output_dir = Path("outputs") / "backtest_results"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        results_dict = {}
        for market, opt in optimization_results.items():
            results_dict[market] = {
                'best_model': opt.best_model,
                'expected_accuracy': opt.expected_accuracy,
                'expected_roi': opt.expected_roi,
                'use_ensemble': opt.recommended_config['use_ensemble'],
                'ensemble_weights': opt.best_ensemble.model_weights,
                'model_performances': [
                    {
                        'model': p.model_name,
                        'accuracy': p.accuracy,
                        'roi': p.roi,
                        'hyperparameters': p.hyperparameters
                    }
                    for p in opt.all_model_performances
                ]
            }
        
        json_path = output_dir / f"optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, 'w') as f:
            json.dump(results_dict, f, indent=2, default=str)
        
        print(f"\n  💾 Results saved to {json_path}")
        
        # Save optimized configurations
        config_path = output_dir / "optimized_configs.json"
        configs = {}
        for market, opt in optimization_results.items():
            configs[market] = opt.recommended_config
        
        with open(config_path, 'w') as f:
            json.dump(configs, f, indent=2, default=str)
        
        print(f"  💾 Configurations saved to {config_path}")
    
    def _generate_final_report(self, optimization_results: Dict[str, MarketOptimization]):
        """Generate comprehensive HTML report"""
        output_path = Path("outputs") / f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Backtest Optimization Report</title>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    max-width: 1400px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }
                h1 {
                    color: #333;
                    text-align: center;
                    font-size: 2.5em;
                    margin-bottom: 30px;
                }
                .market-section {
                    margin: 30px 0;
                    padding: 20px;
                    background: #f7fafc;
                    border-radius: 10px;
                    border-left: 4px solid #667eea;
                }
                .market-title {
                    font-size: 1.5em;
                    color: #2d3748;
                    margin-bottom: 15px;
                }
                .metrics-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }
                .metric-card {
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .metric-value {
                    font-size: 1.8em;
                    font-weight: bold;
                    color: #4a5568;
                }
                .metric-label {
                    color: #718096;
                    font-size: 0.9em;
                    margin-top: 5px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                th {
                    background: #667eea;
                    color: white;
                    padding: 10px;
                    text-align: left;
                }
                td {
                    padding: 8px;
                    border-bottom: 1px solid #e2e8f0;
                }
                tr:hover {
                    background: #f7fafc;
                }
                .best {
                    background: #c6f6d5;
                    font-weight: bold;
                }
                .recommendation {
                    background: #fef5e7;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 15px 0;
                    border-left: 4px solid #f39c12;
                }
                .summary-section {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 25px;
                    border-radius: 10px;
                    margin: 30px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Backtest Optimization Report</h1>
                <p style="text-align: center; color: #718096;">
                    Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """
                </p>
                
                <div class="summary-section">
                    <h2 style="color: white;">📊 Executive Summary</h2>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value">""" + str(len(optimization_results)) + """</div>
                            <div class="metric-label">Markets Analyzed</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">""" + f"{np.mean([opt.expected_accuracy for opt in optimization_results.values()]):.1%}" + """</div>
                            <div class="metric-label">Avg Expected Accuracy</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">""" + f"{np.mean([opt.expected_roi for opt in optimization_results.values()]):.1f}%" + """</div>
                            <div class="metric-label">Avg Expected ROI</div>
                        </div>
                    </div>
                </div>
        """
        
        # Add section for each market
        for market_name, optimization in optimization_results.items():
            market_desc = BETTING_MARKETS[market_name]['description']
            
            html += f"""
                <div class="market-section">
                    <h2 class="market-title">🎲 {market_desc}</h2>
                    
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value">{optimization.expected_accuracy:.1%}</div>
                            <div class="metric-label">Expected Accuracy</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{optimization.expected_roi:.1f}%</div>
                            <div class="metric-label">Expected ROI</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{optimization.best_model}</div>
                            <div class="metric-label">Best Model</div>
                        </div>
                    </div>
                    
                    <div class="recommendation">
                        <strong>🎯 Recommendation:</strong> 
            """
            
            if optimization.recommended_config['use_ensemble']:
                html += "Use ENSEMBLE with weights: "
                for model, weight in optimization.best_ensemble.model_weights.items():
                    if weight > 0:
                        html += f"{model}={weight:.2f} "
            else:
                html += f"Use SINGLE MODEL: {optimization.best_model}"
            
            html += """
                    </div>
                    
                    <h3>Model Performance Comparison</h3>
                    <table>
                        <tr>
                            <th>Model</th>
                            <th>Accuracy</th>
                            <th>Precision</th>
                            <th>Recall</th>
                            <th>F1 Score</th>
                            <th>ROI</th>
                        </tr>
            """
            
            # Sort models by accuracy
            sorted_perfs = sorted(optimization.all_model_performances, key=lambda x: x.accuracy, reverse=True)
            
            for perf in sorted_perfs:
                is_best = perf.model_name == optimization.best_model
                row_class = 'class="best"' if is_best else ''
                
                html += f"""
                        <tr {row_class}>
                            <td>{perf.model_name}</td>
                            <td>{perf.accuracy:.3f}</td>
                            <td>{perf.precision:.3f}</td>
                            <td>{perf.recall:.3f}</td>
                            <td>{perf.f1_score:.3f}</td>
                            <td>{perf.roi:.1f}%</td>
                        </tr>
                """
            
            # Add ensemble row
            html += f"""
                        <tr style="background: #e6f3ff;">
                            <td><strong>ENSEMBLE</strong></td>
                            <td><strong>{optimization.best_ensemble.validation_score:.3f}</strong></td>
                            <td>-</td>
                            <td>-</td>
                            <td>-</td>
                            <td><strong>{optimization.best_ensemble.performance.roi:.1f}%</strong></td>
                        </tr>
                    </table>
            """
            
            # Add top features if available
            if sorted_perfs and sorted_perfs[0].feature_importance:
                html += """
                    <h3>Top Features</h3>
                    <ul>
                """
                for feature, importance in list(sorted_perfs[0].feature_importance.items())[:5]:
                    html += f"<li>{feature}: {importance:.3f}</li>"
                html += "</ul>"
            
            html += "</div>"
        
        # Add recommendations section
        html += """
                <div class="summary-section">
                    <h2 style="color: white;">💡 Recommendations</h2>
                    <ol style="color: white;">
                        <li>Use the optimized configurations for each market</li>
                        <li>Markets with >65% accuracy are most reliable for betting</li>
                        <li>Ensemble models generally outperform single models</li>
                        <li>Focus on markets with positive ROI expectations</li>
                        <li>Re-run optimization monthly to adapt to changing patterns</li>
                    </ol>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save report
        with open(output_path, 'w') as f:
            f.write(html)
        
        print(f"\n  📄 HTML report saved to {output_path}")

# ============================================================================
# CONFIGURATION GENERATOR
# ============================================================================

class OptimizedConfigGenerator:
    """Generate optimized configuration files for production use"""
    
    @staticmethod
    def generate_production_config(optimization_results: Dict[str, MarketOptimization]) -> Dict:
        """Generate production-ready configuration"""
        
        config = {
            'version': '2.0',
            'generated': datetime.now().isoformat(),
            'markets': {}
        }
        
        for market_name, optimization in optimization_results.items():
            market_config = {
                'enabled': True,
                'expected_accuracy': optimization.expected_accuracy,
                'expected_roi': optimization.expected_roi,
                'min_confidence': 0.6,  # Can be optimized
                'max_stake_percentage': 0.05,  # 5% Kelly
            }
            
            if optimization.recommended_config['use_ensemble']:
                market_config['prediction_method'] = 'ensemble'
                market_config['ensemble_weights'] = optimization.best_ensemble.model_weights
            else:
                market_config['prediction_method'] = 'single'
                market_config['model'] = optimization.best_model
                market_config['hyperparameters'] = optimization.recommended_config.get('hyperparameters', {})
            
            # Add feature importance
            if optimization.all_model_performances:
                best_perf = max(optimization.all_model_performances, key=lambda x: x.accuracy)
                if best_perf.feature_importance:
                    market_config['top_features'] = list(best_perf.feature_importance.keys())[:10]
            
            config['markets'][market_name] = market_config
        
        # Save config
        config_path = Path("outputs") / "production_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        
        print(f"\n  ⚙️ Production config saved to {config_path}")
        
        return config

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║     ADVANCED BACKTESTING ENGINE WITH MODEL OPTIMIZATION       ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Check for data file
    data_files = [
        Path("data/processed/features.parquet"),
        Path("features.parquet"),
        Path("historical_data.parquet"),
        Path("historical_data.csv")
    ]
    
    data_path = None
    for file in data_files:
        if file.exists():
            data_path = file
            break
    
    if not data_path:
        print("❌ No data file found!")
        print("Please ensure you have historical data in one of these locations:")
        for file in data_files:
            print(f"  - {file}")
        return
    
    print(f"\n✅ Using data file: {data_path}")
    
    # Initialize engine
    engine = AdvancedBacktestEngine(str(data_path))
    
    # Load data
    engine.load_data()
    
    # Ask for optimization settings
    print("\nOptimization Settings:")
    print("1. Quick test (no hyperparameter optimization)")
    print("2. Standard optimization (recommended)")
    print("3. Full optimization (slow but best results)")
    
    choice = input("\nSelect option (1-3, default=2): ").strip() or "2"
    
    optimize_hyperparameters = choice != "1"
    n_splits = 3 if choice == "1" else 5 if choice == "2" else 10
    
    print(f"\nSettings:")
    print(f"  Hyperparameter optimization: {optimize_hyperparameters}")
    print(f"  Cross-validation splits: {n_splits}")
    
    # Run backtest
    print("\n🚀 Starting backtesting engine...")
    results = engine.run_complete_backtest(
        test_size=0.2,
        n_splits=n_splits,
        optimize_hyperparameters=optimize_hyperparameters,
        n_jobs=-1
    )
    
    # Generate production config
    config_gen = OptimizedConfigGenerator()
    production_config = config_gen.generate_production_config(results)
    
    # Print final summary
    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE!")
    print("="*80)
    
    print("\n📊 BEST CONFIGURATIONS PER MARKET:")
    print("-"*60)
    
    for market_name, opt in results.items():
        market_desc = BETTING_MARKETS[market_name]['description']
        print(f"\n{market_desc}:")
        
        if opt.recommended_config['use_ensemble']:
            print(f"  Method: ENSEMBLE")
            print(f"  Weights:")
            for model, weight in opt.best_ensemble.model_weights.items():
                if weight > 0:
                    print(f"    {model}: {weight:.2f}")
        else:
            print(f"  Method: SINGLE MODEL ({opt.best_model})")
        
        print(f"  Expected Accuracy: {opt.expected_accuracy:.1%}")
        print(f"  Expected ROI: {opt.expected_roi:.1f}%")
    
    print("\n✅ Optimization complete!")
    print("\n📁 Output files:")
    print("  • outputs/backtest_results/ - Detailed results")
    print("  • outputs/production_config.json - Ready-to-use configuration")
    print("  • outputs/backtest_report_*.html - Visual report")
    
    print("\n💡 Next steps:")
    print("  1. Review the HTML report for detailed insights")
    print("  2. Use production_config.json in your prediction system")
    print("  3. Focus on markets with >65% expected accuracy")
    print("  4. Re-run monthly to adapt to changing patterns")

if __name__ == "__main__":
    main()

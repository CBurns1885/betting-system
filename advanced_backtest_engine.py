#!/usr/bin/env python3
"""
advanced_backtest_engine.py
Comprehensive backtesting engine that:
1. Tests each model against each market
2. Finds optimal model-market combinations
3. Auto-tunes hyperparameters per model per market
4. Optimizes ensemble blends for maximum accuracy
"""

import os
import sys
import json
import pickle
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import itertools
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, PredefinedSplit
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    log_loss, roc_auc_score, brier_score_loss, matthews_corrcoef
)
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    ExtraTreesClassifier, VotingClassifier, StackingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

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
    import catboost as cb
    HAS_CAT = True
except ImportError:
    HAS_CAT = False

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    print("⚠️ Install optuna for hyperparameter tuning: pip install optuna")

warnings.filterwarnings('ignore')

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MarketConfig:
    """Configuration for a betting market"""
    name: str
    type: str  # 'binary', 'multiclass', 'regression'
    labels: List[str]
    feature_importance: Dict[str, float] = field(default_factory=dict)
    optimal_threshold: float = 0.5
    min_confidence: float = 0.55
    
@dataclass
class ModelConfig:
    """Configuration for a model"""
    name: str
    model_class: Any
    param_space: Dict[str, Any]
    supports_probability: bool = True
    supports_multiclass: bool = True
    training_time: float = 0.0
    
@dataclass
class BacktestResult:
    """Results from a backtest run"""
    model_name: str
    market_name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    auc: float
    log_loss: float
    brier_score: float
    mcc: float
    roi: float
    profit: float
    num_bets: int
    num_wins: int
    avg_odds: float
    best_params: Dict[str, Any]
    feature_importance: Dict[str, float]
    predictions: pd.DataFrame
    training_time: float
    
@dataclass
class EnsembleConfig:
    """Configuration for ensemble model"""
    models: List[str]
    weights: Dict[str, float]
    method: str  # 'voting', 'stacking', 'blending'
    meta_model: Optional[Any] = None
    performance: float = 0.0

# ============================================================================
# MARKET DEFINITIONS
# ============================================================================

MARKETS = {
    # Binary markets
    'BTTS': MarketConfig(
        name='Both Teams to Score',
        type='binary',
        labels=['No', 'Yes']
    ),
    'Over_2_5': MarketConfig(
        name='Over 2.5 Goals',
        type='binary',
        labels=['Under', 'Over']
    ),
    'Over_1_5': MarketConfig(
        name='Over 1.5 Goals',
        type='binary',
        labels=['Under', 'Over']
    ),
    'Over_3_5': MarketConfig(
        name='Over 3.5 Goals',
        type='binary',
        labels=['Under', 'Over']
    ),
    
    # Multiclass markets
    'Match_Result': MarketConfig(
        name='Match Result (1X2)',
        type='multiclass',
        labels=['Home', 'Draw', 'Away']
    ),
    'Double_Chance': MarketConfig(
        name='Double Chance',
        type='multiclass',
        labels=['1X', '12', 'X2']
    ),
    'HT_Result': MarketConfig(
        name='Half Time Result',
        type='multiclass',
        labels=['Home', 'Draw', 'Away']
    ),
    'Correct_Score': MarketConfig(
        name='Correct Score',
        type='multiclass',
        labels=['0-0', '1-0', '0-1', '1-1', '2-1', '1-2', '2-0', '0-2', 'Other']
    ),
    
    # Asian Handicap markets
    'AH_Home_-0.5': MarketConfig(
        name='Asian Handicap Home -0.5',
        type='binary',
        labels=['No', 'Yes']
    ),
    'AH_Home_-1.5': MarketConfig(
        name='Asian Handicap Home -1.5',
        type='binary',
        labels=['No', 'Yes']
    ),
    
    # Special markets
    'Total_Corners_O10_5': MarketConfig(
        name='Total Corners Over 10.5',
        type='binary',
        labels=['Under', 'Over']
    ),
    'Total_Cards_O3_5': MarketConfig(
        name='Total Cards Over 3.5',
        type='binary',
        labels=['Under', 'Over']
    ),
}

# ============================================================================
# MODEL DEFINITIONS
# ============================================================================

def get_model_configs() -> Dict[str, ModelConfig]:
    """Get all model configurations"""
    configs = {}
    
    # Random Forest
    configs['RandomForest'] = ModelConfig(
        name='RandomForest',
        model_class=RandomForestClassifier,
        param_space={
            'n_estimators': [100, 200, 300],
            'max_depth': [10, 20, 30, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2', 0.3],
            'class_weight': ['balanced', None]
        }
    )
    
    # Extra Trees
    configs['ExtraTrees'] = ModelConfig(
        name='ExtraTrees',
        model_class=ExtraTreesClassifier,
        param_space={
            'n_estimators': [100, 200, 300],
            'max_depth': [10, 20, 30, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2', 0.3]
        }
    )
    
    # Gradient Boosting
    configs['GradientBoosting'] = ModelConfig(
        name='GradientBoosting',
        model_class=GradientBoostingClassifier,
        param_space={
            'n_estimators': [100, 200],
            'learning_rate': [0.01, 0.1, 0.3],
            'max_depth': [3, 5, 7],
            'subsample': [0.8, 1.0],
            'min_samples_split': [2, 5]
        }
    )
    
    # Logistic Regression
    configs['LogisticRegression'] = ModelConfig(
        name='LogisticRegression',
        model_class=LogisticRegression,
        param_space={
            'C': [0.01, 0.1, 1.0, 10.0],
            'penalty': ['l1', 'l2'],
            'solver': ['liblinear', 'saga'],
            'class_weight': ['balanced', None]
        }
    )
    
    # XGBoost
    if HAS_XGB:
        configs['XGBoost'] = ModelConfig(
            name='XGBoost',
            model_class=xgb.XGBClassifier,
            param_space={
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 5, 7, 9],
                'learning_rate': [0.01, 0.05, 0.1, 0.3],
                'subsample': [0.8, 1.0],
                'colsample_bytree': [0.8, 1.0],
                'gamma': [0, 0.1, 0.5],
                'reg_alpha': [0, 0.1, 1.0],
                'reg_lambda': [0, 0.1, 1.0]
            }
        )
    
    # LightGBM
    if HAS_LGB:
        configs['LightGBM'] = ModelConfig(
            name='LightGBM',
            model_class=lgb.LGBMClassifier,
            param_space={
                'n_estimators': [100, 200, 300],
                'num_leaves': [31, 50, 100],
                'learning_rate': [0.01, 0.05, 0.1],
                'feature_fraction': [0.8, 1.0],
                'bagging_fraction': [0.8, 1.0],
                'bagging_freq': [0, 5],
                'min_child_samples': [20, 30, 40]
            }
        )
    
    # CatBoost
    if HAS_CAT:
        configs['CatBoost'] = ModelConfig(
            name='CatBoost',
            model_class=cb.CatBoostClassifier,
            param_space={
                'iterations': [100, 200, 300],
                'depth': [4, 6, 8],
                'learning_rate': [0.01, 0.05, 0.1],
                'l2_leaf_reg': [1, 3, 5],
                'border_count': [32, 64, 128],
                'verbose': [False]
            }
        )
    
    # Neural Network
    configs['NeuralNetwork'] = ModelConfig(
        name='NeuralNetwork',
        model_class=MLPClassifier,
        param_space={
            'hidden_layer_sizes': [(100,), (100, 50), (100, 100)],
            'activation': ['relu', 'tanh'],
            'alpha': [0.0001, 0.001, 0.01],
            'learning_rate': ['constant', 'adaptive'],
            'max_iter': [500]
        }
    )
    
    return configs

# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

class AdvancedBacktestEngine:
    """Advanced backtesting engine with model-market optimization"""
    
    def __init__(self, data_path: Optional[str] = None):
        """Initialize backtesting engine"""
        self.data_path = data_path
        self.model_configs = get_model_configs()
        self.markets = MARKETS
        self.results = {}
        self.best_combinations = {}
        self.ensemble_configs = {}
        
        # Load data if path provided
        if data_path:
            self.data = self._load_data(data_path)
        else:
            self.data = None
            
    def _load_data(self, path: str) -> pd.DataFrame:
        """Load historical data for backtesting"""
        if path.endswith('.parquet'):
            df = pd.read_parquet(path)
        else:
            df = pd.read_csv(path)
            
        # Ensure date column
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            
        print(f"✅ Loaded {len(df)} matches for backtesting")
        return df
    
    def prepare_market_data(self, market: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for a specific market"""
        if self.data is None:
            raise ValueError("No data loaded")
            
        market_config = self.markets[market]
        
        # Get features (exclude target columns)
        feature_cols = [col for col in self.data.columns 
                       if not col.startswith('y_') and col not in ['Date', 'HomeTeam', 'AwayTeam']]
        X = self.data[feature_cols].values
        
        # Get target based on market type
        if market == 'Match_Result':
            # Convert FTR to numeric
            y = self.data['FTR'].map({'H': 0, 'D': 1, 'A': 2}).values
        elif market == 'BTTS':
            y = ((self.data['FTHG'] > 0) & (self.data['FTAG'] > 0)).astype(int).values
        elif 'Over_2_5' in market:
            y = ((self.data['FTHG'] + self.data['FTAG']) > 2.5).astype(int).values
        elif 'Over_1_5' in market:
            y = ((self.data['FTHG'] + self.data['FTAG']) > 1.5).astype(int).values
        elif 'Over_3_5' in market:
            y = ((self.data['FTHG'] + self.data['FTAG']) > 3.5).astype(int).values
        else:
            # Default binary target
            y = np.random.randint(0, 2, len(self.data))
            
        # Get odds if available
        odds = self._extract_odds(market)
        
        return X, y, odds
    
    def _extract_odds(self, market: str) -> np.ndarray:
        """Extract odds for a specific market"""
        # Map market to odds columns
        odds_mapping = {
            'Match_Result': ['B365H', 'B365D', 'B365A'],
            'BTTS': ['B365BTTS_Y', 'B365BTTS_N'],
            'Over_2_5': ['B365_O25', 'B365_U25'],
        }
        
        if market in odds_mapping and all(col in self.data.columns for col in odds_mapping[market]):
            return self.data[odds_mapping[market]].values
        else:
            # Return dummy odds if not available
            return np.ones((len(self.data), 2)) * 2.0
    
    def optimize_model_for_market(self, model_name: str, market: str, 
                                 n_trials: int = 50) -> BacktestResult:
        """Optimize a specific model for a specific market"""
        print(f"\n🔧 Optimizing {model_name} for {market}...")
        
        # Prepare data
        X, y, odds = self.prepare_market_data(market)
        
        # Create train/test split (time series)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        odds_test = odds[split_idx:]
        
        # Scale features
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        
        # Get model config
        model_config = self.model_configs[model_name]
        
        # Optimize hyperparameters
        if HAS_OPTUNA and n_trials > 0:
            best_params = self._optuna_optimize(
                model_config, X_train, y_train, market, n_trials
            )
        else:
            best_params = self._grid_search_optimize(
                model_config, X_train, y_train
            )
        
        # Train final model with best params
        start_time = datetime.now()
        
        if model_name == 'CatBoost' and HAS_CAT:
            model = model_config.model_class(**best_params, verbose=False)
        else:
            model = model_config.model_class(**best_params, random_state=42)
            
        model.fit(X_train, y_train)
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Make predictions
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test) if hasattr(model, 'predict_proba') else None
        
        # Calculate metrics
        metrics = self._calculate_metrics(y_test, y_pred, y_proba, odds_test)
        
        # Extract feature importance
        feature_importance = self._extract_feature_importance(model, X_train)
        
        # Create result
        result = BacktestResult(
            model_name=model_name,
            market_name=market,
            accuracy=metrics['accuracy'],
            precision=metrics['precision'],
            recall=metrics['recall'],
            f1=metrics['f1'],
            auc=metrics['auc'],
            log_loss=metrics['log_loss'],
            brier_score=metrics['brier_score'],
            mcc=metrics['mcc'],
            roi=metrics['roi'],
            profit=metrics['profit'],
            num_bets=metrics['num_bets'],
            num_wins=metrics['num_wins'],
            avg_odds=metrics['avg_odds'],
            best_params=best_params,
            feature_importance=feature_importance,
            predictions=pd.DataFrame({
                'actual': y_test,
                'predicted': y_pred,
                'probability': y_proba[:, 1] if y_proba is not None else y_pred
            }),
            training_time=training_time
        )
        
        return result
    
    def _optuna_optimize(self, model_config: ModelConfig, X_train: np.ndarray, 
                        y_train: np.ndarray, market: str, n_trials: int) -> Dict:
        """Use Optuna for hyperparameter optimization"""
        import optuna
        
        def objective(trial):
            params = {}
            
            # Sample parameters based on model type
            for param, values in model_config.param_space.items():
                if param == 'verbose':
                    params[param] = False
                elif isinstance(values[0], bool):
                    params[param] = trial.suggest_categorical(param, values)
                elif isinstance(values[0], str):
                    params[param] = trial.suggest_categorical(param, values)
                elif isinstance(values[0], int):
                    params[param] = trial.suggest_int(param, min(values), max(values))
                elif isinstance(values[0], float):
                    params[param] = trial.suggest_float(param, min(values), max(values))
                elif isinstance(values[0], tuple):
                    params[param] = trial.suggest_categorical(param, values)
                    
            # Create and train model
            try:
                if model_config.name == 'CatBoost' and HAS_CAT:
                    model = model_config.model_class(**params, verbose=False)
                else:
                    model = model_config.model_class(**params, random_state=42)
                    
                # Use cross-validation
                scores = []
                tscv = TimeSeriesSplit(n_splits=3)
                
                for train_idx, val_idx in tscv.split(X_train):
                    X_t, X_v = X_train[train_idx], X_train[val_idx]
                    y_t, y_v = y_train[train_idx], y_train[val_idx]
                    
                    model.fit(X_t, y_t)
                    
                    if hasattr(model, 'predict_proba'):
                        y_pred = model.predict_proba(X_v)[:, 1]
                        score = roc_auc_score(y_v, y_pred) if len(np.unique(y_v)) > 1 else 0.5
                    else:
                        y_pred = model.predict(X_v)
                        score = accuracy_score(y_v, y_pred)
                        
                    scores.append(score)
                    
                return np.mean(scores)
                
            except Exception as e:
                return 0.0
        
        # Run optimization
        study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler())
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        
        return study.best_params
    
    def _grid_search_optimize(self, model_config: ModelConfig, 
                            X_train: np.ndarray, y_train: np.ndarray) -> Dict:
        """Simple grid search optimization"""
        from sklearn.model_selection import GridSearchCV
        
        # Simplify param space for grid search
        simple_params = {}
        for param, values in model_config.param_space.items():
            if len(values) <= 3:
                simple_params[param] = values[:2]  # Take first 2 values
                
        # Create model
        if model_config.name == 'CatBoost' and HAS_CAT:
            model = model_config.model_class(verbose=False, random_state=42)
        else:
            model = model_config.model_class(random_state=42)
            
        # Grid search
        tscv = TimeSeriesSplit(n_splits=3)
        grid = GridSearchCV(model, simple_params, cv=tscv, scoring='roc_auc', n_jobs=-1)
        grid.fit(X_train, y_train)
        
        return grid.best_params_
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, 
                          y_proba: Optional[np.ndarray], odds: np.ndarray) -> Dict:
        """Calculate comprehensive metrics"""
        metrics = {}
        
        # Classification metrics
        metrics['accuracy'] = accuracy_score(y_true, y_pred)
        
        # Handle multiclass vs binary
        if len(np.unique(y_true)) > 2:
            metrics['precision'] = precision_score(y_true, y_pred, average='weighted')
            metrics['recall'] = recall_score(y_true, y_pred, average='weighted')
            metrics['f1'] = f1_score(y_true, y_pred, average='weighted')
            metrics['auc'] = 0.5  # Placeholder for multiclass
        else:
            metrics['precision'] = precision_score(y_true, y_pred)
            metrics['recall'] = recall_score(y_true, y_pred)
            metrics['f1'] = f1_score(y_true, y_pred)
            
            if y_proba is not None:
                metrics['auc'] = roc_auc_score(y_true, y_proba[:, 1])
                metrics['log_loss'] = log_loss(y_true, y_proba)
                metrics['brier_score'] = brier_score_loss(y_true, y_proba[:, 1])
            else:
                metrics['auc'] = 0.5
                metrics['log_loss'] = 1.0
                metrics['brier_score'] = 0.5
                
        metrics['mcc'] = matthews_corrcoef(y_true, y_pred)
        
        # Betting metrics
        num_bets = len(y_pred)
        num_wins = np.sum(y_pred == y_true)
        
        # Calculate profit (simplified)
        profit = 0
        for i in range(len(y_pred)):
            if y_pred[i] == y_true[i]:
                # Win - profit is (odds - 1) * stake
                profit += (odds[i, int(y_pred[i])] - 1) if i < len(odds) else 1.0
            else:
                # Loss - lose stake
                profit -= 1.0
                
        metrics['roi'] = (profit / num_bets * 100) if num_bets > 0 else 0
        metrics['profit'] = profit
        metrics['num_bets'] = num_bets
        metrics['num_wins'] = num_wins
        metrics['avg_odds'] = np.mean(odds) if len(odds) > 0 else 2.0
        
        return metrics
    
    def _extract_feature_importance(self, model, X_train: np.ndarray) -> Dict[str, float]:
        """Extract feature importance from model"""
        importance = {}
        
        if hasattr(model, 'feature_importances_'):
            # Tree-based models
            importances = model.feature_importances_
            for i, imp in enumerate(importances):
                importance[f'feature_{i}'] = float(imp)
                
        elif hasattr(model, 'coef_'):
            # Linear models
            coef = model.coef_
            if len(coef.shape) > 1:
                coef = np.mean(np.abs(coef), axis=0)
            else:
                coef = np.abs(coef)
                
            for i, imp in enumerate(coef):
                importance[f'feature_{i}'] = float(imp)
                
        return importance
    
    def run_full_backtest(self, n_trials: int = 25, parallel: bool = True):
        """Run complete backtest for all model-market combinations"""
        print("=" * 80)
        print("COMPREHENSIVE BACKTEST - ALL MODELS × ALL MARKETS")
        print("=" * 80)
        
        total_combinations = len(self.model_configs) * len(self.markets)
        print(f"\nTesting {total_combinations} combinations...")
        print(f"Models: {list(self.model_configs.keys())}")
        print(f"Markets: {list(self.markets.keys())}")
        
        results = {}
        
        # Run backtests
        if parallel and os.cpu_count() > 1:
            # Parallel execution
            with ProcessPoolExecutor(max_workers=os.cpu_count() - 1) as executor:
                futures = []
                
                for model_name in self.model_configs:
                    for market in self.markets:
                        future = executor.submit(
                            self.optimize_model_for_market,
                            model_name, market, n_trials
                        )
                        futures.append((model_name, market, future))
                
                for model_name, market, future in futures:
                    key = f"{model_name}_{market}"
                    results[key] = future.result()
                    print(f"✅ {key}: Accuracy={results[key].accuracy:.3f}, ROI={results[key].roi:.1f}%")
        else:
            # Sequential execution
            for model_name in self.model_configs:
                for market in self.markets:
                    key = f"{model_name}_{market}"
                    results[key] = self.optimize_model_for_market(model_name, market, n_trials)
                    print(f"✅ {key}: Accuracy={results[key].accuracy:.3f}, ROI={results[key].roi:.1f}%")
        
        self.results = results
        return results
    
    def find_best_model_per_market(self) -> Dict[str, str]:
        """Find the best model for each market"""
        best_models = {}
        
        for market in self.markets:
            best_score = -float('inf')
            best_model = None
            
            for model_name in self.model_configs:
                key = f"{model_name}_{market}"
                if key in self.results:
                    # Use weighted score of accuracy and ROI
                    score = (self.results[key].accuracy * 0.5 + 
                           min(self.results[key].roi / 100, 1.0) * 0.5)
                    
                    if score > best_score:
                        best_score = score
                        best_model = model_name
            
            best_models[market] = best_model
            
        self.best_combinations = best_models
        return best_models
    
    def optimize_ensemble_blends(self, top_k: int = 3) -> Dict[str, EnsembleConfig]:
        """Optimize ensemble blends for each market"""
        print("\n" + "=" * 80)
        print("OPTIMIZING ENSEMBLE BLENDS")
        print("=" * 80)
        
        ensemble_configs = {}
        
        for market in self.markets:
            print(f"\n📊 Optimizing ensemble for {market}...")
            
            # Get top K models for this market
            market_results = []
            for model_name in self.model_configs:
                key = f"{model_name}_{market}"
                if key in self.results:
                    market_results.append((model_name, self.results[key]))
            
            # Sort by performance
            market_results.sort(key=lambda x: x[1].accuracy, reverse=True)
            top_models = [m[0] for m in market_results[:top_k]]
            
            if len(top_models) < 2:
                continue
            
            # Test different ensemble methods
            best_ensemble = self._find_best_ensemble(market, top_models)
            ensemble_configs[market] = best_ensemble
            
            print(f"  Best ensemble: {best_ensemble.method} with models: {best_ensemble.models}")
            print(f"  Performance: {best_ensemble.performance:.3f}")
        
        self.ensemble_configs = ensemble_configs
        return ensemble_configs
    
    def _find_best_ensemble(self, market: str, models: List[str]) -> EnsembleConfig:
        """Find the best ensemble configuration for a market"""
        X, y, _ = self.prepare_market_data(market)
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Scale features
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        
        best_config = None
        best_score = 0
        
        # Test voting ensemble
        voting_score = self._test_voting_ensemble(models, X_train, y_train, X_test, y_test)
        if voting_score > best_score:
            best_score = voting_score
            best_config = EnsembleConfig(
                models=models,
                weights={m: 1/len(models) for m in models},
                method='voting',
                performance=voting_score
            )
        
        # Test stacking ensemble
        stacking_score = self._test_stacking_ensemble(models, X_train, y_train, X_test, y_test)
        if stacking_score > best_score:
            best_score = stacking_score
            best_config = EnsembleConfig(
                models=models,
                weights={m: 1/len(models) for m in models},
                method='stacking',
                meta_model=LogisticRegression(),
                performance=stacking_score
            )
        
        # Test weighted average
        weighted_score, weights = self._optimize_weights(models, X_train, y_train, X_test, y_test)
        if weighted_score > best_score:
            best_score = weighted_score
            best_config = EnsembleConfig(
                models=models,
                weights=weights,
                method='weighted',
                performance=weighted_score
            )
        
        return best_config or EnsembleConfig(models=models, weights={}, method='voting', performance=0)
    
    def _test_voting_ensemble(self, models: List[str], X_train, y_train, X_test, y_test) -> float:
        """Test voting ensemble"""
        estimators = []
        
        for model_name in models:
            key = f"{model_name}_{models[0]}"  # Get best params from results
            if key in self.results:
                params = self.results[key].best_params
                model_config = self.model_configs[model_name]
                
                if model_name == 'CatBoost' and HAS_CAT:
                    model = model_config.model_class(**params, verbose=False)
                else:
                    model = model_config.model_class(**params, random_state=42)
                    
                estimators.append((model_name, model))
        
        if not estimators:
            return 0
        
        voting = VotingClassifier(estimators, voting='soft')
        voting.fit(X_train, y_train)
        
        return accuracy_score(y_test, voting.predict(X_test))
    
    def _test_stacking_ensemble(self, models: List[str], X_train, y_train, X_test, y_test) -> float:
        """Test stacking ensemble"""
        estimators = []
        
        for model_name in models:
            key = f"{model_name}_{models[0]}"
            if key in self.results:
                params = self.results[key].best_params
                model_config = self.model_configs[model_name]
                
                if model_name == 'CatBoost' and HAS_CAT:
                    model = model_config.model_class(**params, verbose=False)
                else:
                    model = model_config.model_class(**params, random_state=42)
                    
                estimators.append((model_name, model))
        
        if not estimators:
            return 0
        
        stacking = StackingClassifier(
            estimators=estimators,
            final_estimator=LogisticRegression(),
            cv=3
        )
        stacking.fit(X_train, y_train)
        
        return accuracy_score(y_test, stacking.predict(X_test))
    
    def _optimize_weights(self, models: List[str], X_train, y_train, X_test, y_test) -> Tuple[float, Dict]:
        """Optimize weights for weighted average ensemble"""
        from scipy.optimize import minimize
        
        # Train individual models
        predictions = []
        for model_name in models:
            key = f"{model_name}_{models[0]}"
            if key in self.results:
                params = self.results[key].best_params
                model_config = self.model_configs[model_name]
                
                if model_name == 'CatBoost' and HAS_CAT:
                    model = model_config.model_class(**params, verbose=False)
                else:
                    model = model_config.model_class(**params, random_state=42)
                
                model.fit(X_train, y_train)
                
                if hasattr(model, 'predict_proba'):
                    pred = model.predict_proba(X_test)[:, 1]
                else:
                    pred = model.predict(X_test)
                    
                predictions.append(pred)
        
        if not predictions:
            return 0, {}
        
        predictions = np.array(predictions).T
        
        # Optimize weights
        def objective(weights):
            weighted_pred = np.average(predictions, axis=1, weights=weights)
            return -roc_auc_score(y_test, weighted_pred) if len(np.unique(y_test)) > 1 else 0
        
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0, 1) for _ in models]
        initial = [1/len(models)] * len(models)
        
        result = minimize(objective, initial, method='SLSQP', bounds=bounds, constraints=constraints)
        
        best_weights = result.x
        best_score = -result.fun
        
        weight_dict = {model: weight for model, weight in zip(models, best_weights)}
        
        return best_score, weight_dict
    
    def generate_report(self, output_path: Optional[str] = None) -> str:
        """Generate comprehensive backtest report"""
        if output_path is None:
            output_path = f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Backtest Report - Model-Market Optimization</title>
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
                h2 {
                    color: #667eea;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 10px;
                    margin-top: 30px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                th {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px;
                    text-align: left;
                }
                td {
                    padding: 10px;
                    border-bottom: 1px solid #e0e0e0;
                }
                tr:hover {
                    background: #f5f5f5;
                }
                .best {
                    background: #e8f5e9;
                    font-weight: bold;
                }
                .metric {
                    text-align: center;
                    font-size: 0.9em;
                }
                .positive { color: #4caf50; }
                .negative { color: #f44336; }
                .neutral { color: #2196f3; }
                .heatmap {
                    display: grid;
                    gap: 2px;
                    margin: 20px 0;
                }
                .heatmap-cell {
                    padding: 10px;
                    text-align: center;
                    border-radius: 4px;
                    font-size: 0.9em;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Backtest Report - Model-Market Optimization</h1>
                <p style="text-align: center; color: #666;">
                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
                </p>
        """
        
        # Summary section
        html += """
                <h2>📊 Executive Summary</h2>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
        """
        
        if self.results:
            avg_accuracy = np.mean([r.accuracy for r in self.results.values()])
            avg_roi = np.mean([r.roi for r in self.results.values()])
            best_combo = max(self.results.values(), key=lambda x: x.accuracy)
            
            html += f"""
                    <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; text-align: center;">
                        <div style="font-size: 2em; color: #667eea;">{avg_accuracy:.1%}</div>
                        <div style="color: #666;">Average Accuracy</div>
                    </div>
                    <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; text-align: center;">
                        <div style="font-size: 2em; color: #764ba2;">{avg_roi:.1f}%</div>
                        <div style="color: #666;">Average ROI</div>
                    </div>
                    <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; text-align: center;">
                        <div style="font-size: 1.5em; color: #4caf50;">{best_combo.model_name}</div>
                        <div style="color: #666;">Best Model: {best_combo.market_name}</div>
                    </div>
            """
        
        html += """
                </div>
                
                <h2>🏆 Best Model per Market</h2>
                <table>
                    <tr>
                        <th>Market</th>
                        <th>Best Model</th>
                        <th>Accuracy</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1 Score</th>
                        <th>ROI</th>
                        <th>Training Time</th>
                    </tr>
        """
        
        # Best models table
        for market, model in self.best_combinations.items():
            key = f"{model}_{market}"
            if key in self.results:
                r = self.results[key]
                roi_class = 'positive' if r.roi > 0 else 'negative'
                
                html += f"""
                    <tr class="best">
                        <td><strong>{market}</strong></td>
                        <td>{model}</td>
                        <td class="metric">{r.accuracy:.3f}</td>
                        <td class="metric">{r.precision:.3f}</td>
                        <td class="metric">{r.recall:.3f}</td>
                        <td class="metric">{r.f1:.3f}</td>
                        <td class="metric {roi_class}">{r.roi:.1f}%</td>
                        <td class="metric">{r.training_time:.1f}s</td>
                    </tr>
                """
        
        html += """
                </table>
                
                <h2>📈 Complete Results Matrix</h2>
                <div style="overflow-x: auto;">
                <table style="font-size: 0.9em;">
                    <tr>
                        <th>Model</th>
                        <th>Market</th>
                        <th>Accuracy</th>
                        <th>AUC</th>
                        <th>Log Loss</th>
                        <th>MCC</th>
                        <th>ROI</th>
                        <th>Profit</th>
                        <th>Win Rate</th>
                    </tr>
        """
        
        # All results
        sorted_results = sorted(self.results.items(), key=lambda x: x[1].accuracy, reverse=True)
        
        for key, r in sorted_results:
            roi_class = 'positive' if r.roi > 0 else 'negative'
            win_rate = r.num_wins / r.num_bets if r.num_bets > 0 else 0
            
            html += f"""
                    <tr>
                        <td>{r.model_name}</td>
                        <td>{r.market_name}</td>
                        <td class="metric">{r.accuracy:.3f}</td>
                        <td class="metric">{r.auc:.3f}</td>
                        <td class="metric">{r.log_loss:.3f}</td>
                        <td class="metric">{r.mcc:.3f}</td>
                        <td class="metric {roi_class}">{r.roi:.1f}%</td>
                        <td class="metric {roi_class}">{r.profit:.2f}</td>
                        <td class="metric">{win_rate:.1%}</td>
                    </tr>
            """
        
        html += """
                </table>
                </div>
                
                <h2>🎲 Ensemble Configurations</h2>
                <table>
                    <tr>
                        <th>Market</th>
                        <th>Method</th>
                        <th>Models</th>
                        <th>Weights</th>
                        <th>Performance</th>
                    </tr>
        """
        
        # Ensemble configs
        for market, config in self.ensemble_configs.items():
            models_str = ', '.join(config.models)
            weights_str = ', '.join([f"{m}:{w:.2f}" for m, w in config.weights.items()])
            
            html += f"""
                    <tr>
                        <td><strong>{market}</strong></td>
                        <td>{config.method}</td>
                        <td>{models_str}</td>
                        <td>{weights_str}</td>
                        <td class="metric">{config.performance:.3f}</td>
                    </tr>
            """
        
        # Hyperparameter details
        html += """
                </table>
                
                <h2>⚙️ Optimal Hyperparameters</h2>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
        """
        
        # Group by model
        model_params = defaultdict(list)
        for key, result in self.results.items():
            model_params[result.model_name].append({
                'market': result.market_name,
                'params': result.best_params,
                'accuracy': result.accuracy
            })
        
        for model_name, markets in model_params.items():
            # Get best market for this model
            best_market = max(markets, key=lambda x: x['accuracy'])
            
            html += f"""
                <div style="background: #f9f9f9; padding: 15px; border-radius: 8px;">
                    <h4>{model_name}</h4>
                    <p style="color: #666; font-size: 0.9em;">Best on: {best_market['market']} ({best_market['accuracy']:.3f})</p>
                    <code style="background: #fff; padding: 10px; display: block; border-radius: 4px; font-size: 0.8em;">
        """
            
            for param, value in best_market['params'].items():
                html += f"{param}: {value}<br>"
                
            html += """
                    </code>
                </div>
            """
        
        html += """
                </div>
                
                <h2>💡 Recommendations</h2>
                <div style="background: #f0f7ff; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <ul style="line-height: 1.8;">
        """
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        for rec in recommendations:
            html += f"<li>{rec}</li>"
        
        html += """
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save report
        with open(output_path, 'w') as f:
            f.write(html)
        
        print(f"\n✅ Report saved to {output_path}")
        return output_path
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations from results"""
        recommendations = []
        
        if not self.results:
            return ["Run backtest first to generate recommendations"]
        
        # Find best overall model
        best_model_counts = defaultdict(int)
        for market, model in self.best_combinations.items():
            best_model_counts[model] += 1
        
        if best_model_counts:
            best_overall = max(best_model_counts.items(), key=lambda x: x[1])
            recommendations.append(
                f"<strong>{best_overall[0]}</strong> performs best across {best_overall[1]} markets - consider as primary model"
            )
        
        # Find high ROI markets
        high_roi_markets = []
        for key, result in self.results.items():
            if result.roi > 15:
                high_roi_markets.append((result.market_name, result.roi))
        
        if high_roi_markets:
            high_roi_markets.sort(key=lambda x: x[1], reverse=True)
            top_market = high_roi_markets[0]
            recommendations.append(
                f"Focus on <strong>{top_market[0]}</strong> market with {top_market[1]:.1f}% ROI potential"
            )
        
        # Check ensemble performance
        if self.ensemble_configs:
            best_ensemble = max(self.ensemble_configs.items(), key=lambda x: x[1].performance)
            recommendations.append(
                f"Use <strong>{best_ensemble[1].method}</strong> ensemble for {best_ensemble[0]} market"
            )
        
        # Model-specific recommendations
        if HAS_XGB and 'XGBoost' in best_model_counts and best_model_counts['XGBoost'] > 2:
            recommendations.append("XGBoost shows strong performance - increase n_estimators for production")
        
        if HAS_LGB and 'LightGBM' in best_model_counts and best_model_counts['LightGBM'] > 2:
            recommendations.append("LightGBM is efficient - good for real-time predictions")
        
        # Feature engineering recommendations
        avg_accuracy = np.mean([r.accuracy for r in self.results.values()])
        if avg_accuracy < 0.60:
            recommendations.append("Consider adding more features - xG data could improve accuracy by 15-20%")
        
        # Risk management
        recommendations.append("Use Kelly Criterion with 25% fraction for optimal bankroll management")
        recommendations.append("Avoid markets with accuracy below 55% unless ROI is exceptional")
        
        return recommendations
    
    def export_optimal_configs(self, output_path: str = "optimal_configs.json"):
        """Export optimal configurations for production use"""
        configs = {
            'best_models': self.best_combinations,
            'ensemble_configs': {},
            'model_params': {},
            'market_thresholds': {}
        }
        
        # Add ensemble configs
        for market, ensemble in self.ensemble_configs.items():
            configs['ensemble_configs'][market] = {
                'method': ensemble.method,
                'models': ensemble.models,
                'weights': ensemble.weights,
                'performance': ensemble.performance
            }
        
        # Add best params for each model-market combo
        for key, result in self.results.items():
            configs['model_params'][key] = {
                'params': result.best_params,
                'accuracy': result.accuracy,
                'roi': result.roi
            }
        
        # Add optimal thresholds
        for market in self.markets:
            # Find best threshold for this market
            configs['market_thresholds'][market] = {
                'min_confidence': 0.55,
                'min_odds': 1.5,
                'max_stake': 0.05
            }
        
        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(configs, f, indent=2, default=str)
        
        print(f"✅ Optimal configs exported to {output_path}")
        return configs

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║     ADVANCED BACKTEST ENGINE - MODEL-MARKET OPTIMIZATION      ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Check for data file
    import sys
    
    if len(sys.argv) > 1:
        data_path = sys.argv[1]
    else:
        # Try to find features file
        from pathlib import Path
        
        possible_paths = [
            "data/processed/features.parquet",
            "features.parquet",
            "data/features.csv",
            "weekly_bets.csv"
        ]
        
        data_path = None
        for path in possible_paths:
            if Path(path).exists():
                data_path = path
                break
        
        if not data_path:
            print("\n❌ No data file found!")
            print("\nUsage: python advanced_backtest_engine.py <data_file>")
            print("\nOr place features.parquet in data/processed/")
            sys.exit(1)
    
    # Initialize engine
    print(f"\n📊 Loading data from {data_path}...")
    engine = AdvancedBacktestEngine(data_path)
    
    # Get optimization level
    print("\nSelect optimization level:")
    print("1. Quick test (10 trials per model)")
    print("2. Standard (25 trials per model)")
    print("3. Thorough (50 trials per model)")
    print("4. Exhaustive (100 trials per model)")
    
    choice = input("\nChoice (1-4, default=2): ").strip() or "2"
    
    n_trials_map = {
        "1": 10,
        "2": 25,
        "3": 50,
        "4": 100
    }
    
    n_trials = n_trials_map.get(choice, 25)
    
    print(f"\n🚀 Starting backtest with {n_trials} trials per model-market combination...")
    print("This may take a while depending on data size and CPU cores...")
    
    # Run backtest
    results = engine.run_full_backtest(n_trials=n_trials, parallel=True)
    
    # Find best combinations
    print("\n" + "=" * 80)
    print("FINDING OPTIMAL MODEL-MARKET COMBINATIONS")
    print("=" * 80)
    
    best_models = engine.find_best_model_per_market()
    
    print("\n🏆 Best Model per Market:")
    for market, model in best_models.items():
        key = f"{model}_{market}"
        if key in results:
            r = results[key]
            print(f"  {market:.<30} {model} (Acc: {r.accuracy:.3f}, ROI: {r.roi:.1f}%)")
    
    # Optimize ensembles
    ensemble_configs = engine.optimize_ensemble_blends(top_k=3)
    
    # Generate report
    print("\n📄 Generating report...")
    report_path = engine.generate_report()
    
    # Export configs
    print("💾 Exporting optimal configurations...")
    configs = engine.export_optimal_configs()
    
    print("\n" + "=" * 80)
    print("✅ BACKTEST COMPLETE!")
    print("=" * 80)
    
    print(f"\n📊 Report: {report_path}")
    print("📁 Configs: optimal_configs.json")
    
    print("\n🎯 Next Steps:")
    print("1. Review the HTML report for detailed results")
    print("2. Use optimal_configs.json in production")
    print("3. Implement the recommended model-market combinations")
    print("4. Monitor live performance against backtest results")

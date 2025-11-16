#!/usr/bin/env python3
"""
intelligent_auto_tuner.py
Intelligent hyperparameter tuning system that:
1. Auto-tunes each model for each market
2. Learns from past tuning sessions
3. Provides recommendations for optimal settings
4. Integrates with existing pipeline
"""

import os
import json
import pickle
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
import warnings

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import make_scorer, accuracy_score, roc_auc_score

# Bayesian optimization
try:
    from skopt import BayesSearchCV
    from skopt.space import Real, Integer, Categorical
    from skopt.utils import use_named_args
    HAS_SKOPT = True
except ImportError:
    HAS_SKOPT = False
    print("⚠️ Install scikit-optimize for Bayesian optimization: pip install scikit-optimize")

# Optuna for advanced optimization
try:
    import optuna
    from optuna.integration import OptunaSearchCV
    from optuna.samplers import TPESampler, CmaEsSampler
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class TuningConfig:
    """Configuration for tuning session"""
    model_name: str
    market_name: str
    n_trials: int = 50
    cv_folds: int = 5
    scoring_metric: str = 'roc_auc'
    optimization_method: str = 'optuna'  # 'optuna', 'bayesian', 'random', 'grid'
    early_stopping: bool = True
    early_stopping_rounds: int = 10
    timeout_seconds: int = 3600
    use_gpu: bool = False
    cache_results: bool = True

@dataclass
class TuningResult:
    """Results from a tuning session"""
    config: TuningConfig
    best_params: Dict[str, Any]
    best_score: float
    cv_scores: List[float]
    training_time: float
    n_trials_completed: int
    convergence_history: List[float]
    feature_importance: Optional[Dict[str, float]] = None
    timestamp: datetime = datetime.now()

# ============================================================================
# TUNING DATABASE
# ============================================================================

class TuningDatabase:
    """Database to store and learn from tuning results"""
    
    def __init__(self, db_path: str = "tuning_history.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self._init_database()
        
    def _init_database(self):
        """Initialize database schema"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS tuning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                market_name TEXT NOT NULL,
                best_params TEXT NOT NULL,
                best_score REAL NOT NULL,
                cv_scores TEXT,
                n_trials INTEGER,
                optimization_method TEXT,
                training_time REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_hash TEXT,
                UNIQUE(model_name, market_name, data_hash)
            );
            
            CREATE TABLE IF NOT EXISTS parameter_importance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                market_name TEXT NOT NULL,
                parameter_name TEXT NOT NULL,
                importance_score REAL,
                optimal_range_min TEXT,
                optimal_range_max TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_sessions_model ON tuning_sessions(model_name);
            CREATE INDEX IF NOT EXISTS idx_sessions_market ON tuning_sessions(market_name);
            CREATE INDEX IF NOT EXISTS idx_sessions_score ON tuning_sessions(best_score DESC);
        """)
        self.conn.commit()
    
    def save_session(self, result: TuningResult, data_hash: str):
        """Save tuning session to database"""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO tuning_sessions 
                (model_name, market_name, best_params, best_score, cv_scores, 
                 n_trials, optimization_method, training_time, data_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.config.model_name,
                result.config.market_name,
                json.dumps(result.best_params),
                result.best_score,
                json.dumps(result.cv_scores),
                result.n_trials_completed,
                result.config.optimization_method,
                result.training_time,
                data_hash
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def get_best_params(self, model_name: str, market_name: str) -> Optional[Dict]:
        """Get best parameters for a model-market combination"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT best_params, best_score 
            FROM tuning_sessions 
            WHERE model_name = ? AND market_name = ?
            ORDER BY best_score DESC
            LIMIT 1
        """, (model_name, market_name))
        
        result = cursor.fetchone()
        if result:
            return json.loads(result[0])
        return None
    
    def get_parameter_importance(self, model_name: str) -> Dict[str, float]:
        """Get parameter importance for a model"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT parameter_name, importance_score
            FROM parameter_importance
            WHERE model_name = ?
            ORDER BY importance_score DESC
        """, (model_name,))
        
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def update_parameter_importance(self, model_name: str, market_name: str, 
                                   importance: Dict[str, float]):
        """Update parameter importance based on tuning results"""
        for param, score in importance.items():
            self.conn.execute("""
                INSERT OR REPLACE INTO parameter_importance
                (model_name, market_name, parameter_name, importance_score)
                VALUES (?, ?, ?, ?)
            """, (model_name, market_name, param, score))
        self.conn.commit()

# ============================================================================
# INTELLIGENT AUTO-TUNER
# ============================================================================

class IntelligentAutoTuner:
    """Intelligent hyperparameter tuning with learning capabilities"""
    
    def __init__(self, cache_dir: str = "tuning_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.db = TuningDatabase()
        self.tuning_history = []
        
    def tune_model(self, X: np.ndarray, y: np.ndarray, 
                  model_class: Any, config: TuningConfig,
                  param_space: Dict[str, Any]) -> TuningResult:
        """
        Intelligently tune a model for a specific market
        
        Args:
            X: Feature matrix
            y: Target values
            model_class: Model class to tune
            config: Tuning configuration
            param_space: Parameter search space
            
        Returns:
            TuningResult with best parameters and performance
        """
        print(f"\n🔧 Tuning {config.model_name} for {config.market_name}")
        print(f"   Method: {config.optimization_method}")
        print(f"   Trials: {config.n_trials}")
        
        start_time = datetime.now()
        
        # Check cache for existing results
        data_hash = self._compute_data_hash(X, y)
        cached_result = self._check_cache(config, data_hash)
        
        if cached_result and config.cache_results:
            print(f"   ✅ Using cached results (score: {cached_result.best_score:.4f})")
            return cached_result
        
        # Get warm-start parameters from history
        warm_start_params = self._get_warm_start_params(config.model_name, config.market_name)
        
        # Choose optimization method
        if config.optimization_method == 'optuna' and HAS_OPTUNA:
            result = self._tune_with_optuna(X, y, model_class, config, param_space, warm_start_params)
        elif config.optimization_method == 'bayesian' and HAS_SKOPT:
            result = self._tune_with_bayesian(X, y, model_class, config, param_space, warm_start_params)
        else:
            result = self._tune_with_random_search(X, y, model_class, config, param_space)
        
        # Calculate training time
        result.training_time = (datetime.now() - start_time).total_seconds()
        
        # Save to database
        self.db.save_session(result, data_hash)
        
        # Update parameter importance
        if result.feature_importance:
            self.db.update_parameter_importance(
                config.model_name, config.market_name, result.feature_importance
            )
        
        # Cache result
        if config.cache_results:
            self._save_to_cache(config, data_hash, result)
        
        print(f"   ✅ Best score: {result.best_score:.4f}")
        print(f"   ⏱️ Time: {result.training_time:.1f}s")
        
        return result
    
    def _tune_with_optuna(self, X: np.ndarray, y: np.ndarray, model_class: Any,
                         config: TuningConfig, param_space: Dict[str, Any],
                         warm_start: Optional[Dict] = None) -> TuningResult:
        """Tune using Optuna with advanced features"""
        import optuna
        
        # Create objective function
        def objective(trial):
            params = {}
            
            # Sample parameters
            for param_name, param_config in param_space.items():
                if isinstance(param_config, list):
                    # Categorical parameter
                    if isinstance(param_config[0], bool):
                        params[param_name] = trial.suggest_categorical(param_name, param_config)
                    elif isinstance(param_config[0], str):
                        params[param_name] = trial.suggest_categorical(param_name, param_config)
                    elif isinstance(param_config[0], int):
                        params[param_name] = trial.suggest_int(param_name, min(param_config), max(param_config))
                    elif isinstance(param_config[0], float):
                        params[param_name] = trial.suggest_float(param_name, min(param_config), max(param_config))
                    else:
                        params[param_name] = trial.suggest_categorical(param_name, param_config)
                elif isinstance(param_config, tuple):
                    if len(param_config) == 2:
                        # Range parameter
                        if isinstance(param_config[0], int):
                            params[param_name] = trial.suggest_int(param_name, param_config[0], param_config[1])
                        else:
                            params[param_name] = trial.suggest_float(param_name, param_config[0], param_config[1])
                    else:
                        params[param_name] = trial.suggest_categorical(param_name, param_config)
            
            # Create model
            try:
                if 'random_state' in model_class.__init__.__code__.co_varnames:
                    params['random_state'] = 42
                
                model = model_class(**params)
                
                # Cross-validation
                cv = TimeSeriesSplit(n_splits=config.cv_folds)
                
                if config.scoring_metric == 'roc_auc':
                    scorer = make_scorer(roc_auc_score, needs_proba=True)
                else:
                    scorer = config.scoring_metric
                
                scores = cross_val_score(model, X, y, cv=cv, scoring=scorer, n_jobs=-1)
                
                return scores.mean()
                
            except Exception as e:
                return 0.0
        
        # Create study with warm start
        sampler = TPESampler(seed=42)
        
        if warm_start:
            # Add warm start trial
            study = optuna.create_study(direction='maximize', sampler=sampler)
            study.enqueue_trial(warm_start)
        else:
            study = optuna.create_study(direction='maximize', sampler=sampler)
        
        # Optimize with pruning
        study.optimize(
            objective, 
            n_trials=config.n_trials,
            timeout=config.timeout_seconds if config.timeout_seconds > 0 else None,
            show_progress_bar=True
        )
        
        # Extract results
        result = TuningResult(
            config=config,
            best_params=study.best_params,
            best_score=study.best_value,
            cv_scores=[t.value for t in study.trials if t.value is not None],
            training_time=0,
            n_trials_completed=len(study.trials),
            convergence_history=[t.value for t in study.trials if t.value is not None]
        )
        
        # Calculate parameter importance
        if len(study.trials) > 10:
            importance = optuna.importance.get_param_importances(study)
            result.feature_importance = importance
        
        return result
    
    def _tune_with_bayesian(self, X: np.ndarray, y: np.ndarray, model_class: Any,
                           config: TuningConfig, param_space: Dict[str, Any],
                           warm_start: Optional[Dict] = None) -> TuningResult:
        """Tune using Bayesian optimization"""
        from skopt import BayesSearchCV
        from skopt.space import Real, Integer, Categorical
        
        # Convert param_space to skopt format
        skopt_space = {}
        for param_name, param_config in param_space.items():
            if isinstance(param_config, list):
                if isinstance(param_config[0], (int, float)):
                    if isinstance(param_config[0], int):
                        skopt_space[param_name] = Integer(min(param_config), max(param_config))
                    else:
                        skopt_space[param_name] = Real(min(param_config), max(param_config))
                else:
                    skopt_space[param_name] = Categorical(param_config)
            elif isinstance(param_config, tuple) and len(param_config) == 2:
                if isinstance(param_config[0], int):
                    skopt_space[param_name] = Integer(param_config[0], param_config[1])
                else:
                    skopt_space[param_name] = Real(param_config[0], param_config[1])
        
        # Create Bayesian search
        bayes_search = BayesSearchCV(
            model_class(),
            skopt_space,
            n_iter=config.n_trials,
            cv=TimeSeriesSplit(n_splits=config.cv_folds),
            scoring=config.scoring_metric,
            n_jobs=-1,
            random_state=42
        )
        
        # Fit with warm start if available
        if warm_start:
            # Set initial point
            bayes_search.set_params(**warm_start)
        
        bayes_search.fit(X, y)
        
        # Extract results
        result = TuningResult(
            config=config,
            best_params=bayes_search.best_params_,
            best_score=bayes_search.best_score_,
            cv_scores=list(bayes_search.cv_results_['mean_test_score']),
            training_time=0,
            n_trials_completed=len(bayes_search.cv_results_['mean_test_score']),
            convergence_history=list(bayes_search.cv_results_['mean_test_score'])
        )
        
        return result
    
    def _tune_with_random_search(self, X: np.ndarray, y: np.ndarray, model_class: Any,
                                config: TuningConfig, param_space: Dict[str, Any]) -> TuningResult:
        """Tune using random search"""
        from sklearn.model_selection import RandomizedSearchCV
        
        # Convert param_space to sklearn format
        sklearn_space = {}
        for param_name, param_config in param_space.items():
            if isinstance(param_config, list):
                sklearn_space[param_name] = param_config
            elif isinstance(param_config, tuple) and len(param_config) == 2:
                # Create range
                if isinstance(param_config[0], int):
                    sklearn_space[param_name] = list(range(param_config[0], param_config[1] + 1))
                else:
                    sklearn_space[param_name] = [param_config[0], param_config[1]]
        
        # Create random search
        random_search = RandomizedSearchCV(
            model_class(),
            sklearn_space,
            n_iter=min(config.n_trials, 20),  # Limit for random search
            cv=TimeSeriesSplit(n_splits=config.cv_folds),
            scoring=config.scoring_metric,
            n_jobs=-1,
            random_state=42
        )
        
        random_search.fit(X, y)
        
        # Extract results
        result = TuningResult(
            config=config,
            best_params=random_search.best_params_,
            best_score=random_search.best_score_,
            cv_scores=list(random_search.cv_results_['mean_test_score']),
            training_time=0,
            n_trials_completed=len(random_search.cv_results_['mean_test_score']),
            convergence_history=list(random_search.cv_results_['mean_test_score'])
        )
        
        return result
    
    def _compute_data_hash(self, X: np.ndarray, y: np.ndarray) -> str:
        """Compute hash of data for caching"""
        data_str = f"{X.shape}_{y.shape}_{np.mean(X)}_{np.mean(y)}"
        return hashlib.md5(data_str.encode()).hexdigest()[:16]
    
    def _check_cache(self, config: TuningConfig, data_hash: str) -> Optional[TuningResult]:
        """Check if results are cached"""
        cache_file = self.cache_dir / f"{config.model_name}_{config.market_name}_{data_hash}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        
        return None
    
    def _save_to_cache(self, config: TuningConfig, data_hash: str, result: TuningResult):
        """Save results to cache"""
        cache_file = self.cache_dir / f"{config.model_name}_{config.market_name}_{data_hash}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception as e:
            print(f"Failed to cache: {e}")
    
    def _get_warm_start_params(self, model_name: str, market_name: str) -> Optional[Dict]:
        """Get warm start parameters from history"""
        return self.db.get_best_params(model_name, market_name)
    
    def auto_tune_all_models(self, X: np.ndarray, y: np.ndarray,
                            models: Dict[str, Any], market_name: str,
                            n_trials: int = 50) -> Dict[str, TuningResult]:
        """
        Auto-tune all models for a specific market
        
        Args:
            X: Feature matrix
            y: Target values  
            models: Dictionary of model_name -> (model_class, param_space)
            market_name: Name of the betting market
            n_trials: Number of tuning trials per model
            
        Returns:
            Dictionary of model_name -> TuningResult
        """
        print(f"\n{'='*80}")
        print(f"AUTO-TUNING ALL MODELS FOR {market_name}")
        print(f"{'='*80}")
        
        results = {}
        
        for model_name, (model_class, param_space) in models.items():
            config = TuningConfig(
                model_name=model_name,
                market_name=market_name,
                n_trials=n_trials,
                cv_folds=5,
                scoring_metric='roc_auc',
                optimization_method='optuna' if HAS_OPTUNA else 'random'
            )
            
            result = self.tune_model(X, y, model_class, config, param_space)
            results[model_name] = result
        
        # Find best model
        best_model = max(results.items(), key=lambda x: x[1].best_score)
        print(f"\n🏆 Best model for {market_name}: {best_model[0]} (score: {best_model[1].best_score:.4f})")
        
        return results
    
    def generate_tuning_report(self, results: Dict[str, TuningResult]) -> str:
        """Generate HTML report of tuning results"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Auto-Tuning Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th { background: #4CAF50; color: white; padding: 12px; }
                td { border: 1px solid #ddd; padding: 8px; }
                .best { background: #e8f5e9; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>Hyperparameter Tuning Report</h1>
            <table>
                <tr>
                    <th>Model</th>
                    <th>Market</th>
                    <th>Best Score</th>
                    <th>Trials</th>
                    <th>Time (s)</th>
                    <th>Best Parameters</th>
                </tr>
        """
        
        # Sort by score
        sorted_results = sorted(results.items(), key=lambda x: x[1].best_score, reverse=True)
        
        for model_name, result in sorted_results:
            is_best = (model_name == sorted_results[0][0])
            row_class = 'class="best"' if is_best else ''
            
            params_str = ', '.join([f"{k}={v}" for k, v in result.best_params.items()])
            
            html += f"""
                <tr {row_class}>
                    <td>{model_name}</td>
                    <td>{result.config.market_name}</td>
                    <td>{result.best_score:.4f}</td>
                    <td>{result.n_trials_completed}</td>
                    <td>{result.training_time:.1f}</td>
                    <td style="font-size: 0.9em;">{params_str}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        # Save report
        report_path = f"tuning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_path, 'w') as f:
            f.write(html)
        
        return report_path

# ============================================================================
# INTEGRATION WITH EXISTING PIPELINE
# ============================================================================

def integrate_with_pipeline(feature_file: str, output_file: str = "optimal_model_configs.json"):
    """
    Integrate auto-tuning with existing pipeline
    
    This function:
    1. Loads your existing features
    2. Auto-tunes all models for all markets
    3. Exports optimal configurations for production use
    """
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║         INTELLIGENT AUTO-TUNER - PIPELINE INTEGRATION         ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Load features
    print(f"\n📊 Loading features from {feature_file}...")
    if feature_file.endswith('.parquet'):
        df = pd.read_parquet(feature_file)
    else:
        df = pd.read_csv(feature_file)
    
    print(f"   Loaded {len(df)} samples with {len(df.columns)} features")
    
    # Define models to tune
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    
    models = {
        'RandomForest': (
            RandomForestClassifier,
            {
                'n_estimators': [100, 200, 300],
                'max_depth': [10, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
        ),
        'GradientBoosting': (
            GradientBoostingClassifier,
            {
                'n_estimators': [100, 200],
                'learning_rate': [0.01, 0.1, 0.3],
                'max_depth': [3, 5, 7],
                'subsample': [0.8, 1.0]
            }
        ),
        'LogisticRegression': (
            LogisticRegression,
            {
                'C': [0.01, 0.1, 1.0, 10.0],
                'penalty': ['l1', 'l2'],
                'solver': ['liblinear']
            }
        )
    }
    
    # Add XGBoost if available
    try:
        import xgboost as xgb
        models['XGBoost'] = (
            xgb.XGBClassifier,
            {
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.05, 0.1],
                'subsample': [0.8, 1.0]
            }
        )
    except ImportError:
        pass
    
    # Define markets to tune
    markets = {
        'Match_Result': lambda df: df['FTR'].map({'H': 0, 'D': 1, 'A': 2}).values,
        'BTTS': lambda df: ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int).values,
        'Over_2.5': lambda df: ((df['FTHG'] + df['FTAG']) > 2.5).astype(int).values,
    }
    
    # Initialize tuner
    tuner = IntelligentAutoTuner()
    
    # Prepare features
    feature_cols = [col for col in df.columns 
                   if not col.startswith('y_') and col not in ['Date', 'HomeTeam', 'AwayTeam', 'FTR', 'FTHG', 'FTAG']]
    X = df[feature_cols].values
    
    # Scale features
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    
    # Store all results
    all_results = {}
    optimal_configs = {}
    
    # Tune for each market
    for market_name, target_func in markets.items():
        print(f"\n{'='*60}")
        print(f"Tuning for {market_name}")
        print('='*60)
        
        # Get target
        try:
            y = target_func(df)
        except Exception as e:
            print(f"   ⚠️ Skipping {market_name}: {e}")
            continue
        
        # Auto-tune all models
        results = tuner.auto_tune_all_models(X, y, models, market_name, n_trials=25)
        
        # Store results
        all_results[market_name] = results
        
        # Find best model for this market
        best_model = max(results.items(), key=lambda x: x[1].best_score)
        optimal_configs[market_name] = {
            'model': best_model[0],
            'params': best_model[1].best_params,
            'score': best_model[1].best_score,
            'cv_scores': best_model[1].cv_scores
        }
    
    # Generate report
    print("\n📄 Generating tuning report...")
    
    # Flatten results for report
    flat_results = {}
    for market, models in all_results.items():
        for model_name, result in models.items():
            flat_results[f"{model_name}_{market}"] = result
    
    report_path = tuner.generate_tuning_report(flat_results)
    print(f"   Report saved to {report_path}")
    
    # Export optimal configurations
    print(f"\n💾 Exporting optimal configurations to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(optimal_configs, f, indent=2, default=str)
    
    print("\n" + "="*60)
    print("✅ AUTO-TUNING COMPLETE!")
    print("="*60)
    
    print("\n🏆 Best Models by Market:")
    for market, config in optimal_configs.items():
        print(f"   {market:.<30} {config['model']} (score: {config['score']:.4f})")
    
    print(f"\n📁 Configurations saved to: {output_file}")
    print("📊 Use these in your production pipeline for optimal performance!")
    
    return optimal_configs

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run integration with provided feature file
        feature_file = sys.argv[1]
        integrate_with_pipeline(feature_file)
    else:
        # Demo mode
        print("""
        Intelligent Auto-Tuner
        ======================
        
        Usage:
            python intelligent_auto_tuner.py <feature_file>
        
        Example:
            python intelligent_auto_tuner.py data/processed/features.parquet
        
        This will:
        1. Load your features
        2. Auto-tune all models for all markets
        3. Export optimal configurations
        4. Generate performance report
        """)

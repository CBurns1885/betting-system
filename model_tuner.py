#!/usr/bin/env python3
"""
model_tuner.py
Automated model tuning system that finds optimal configurations
for each betting market and generates production-ready model files
"""

import os
import sys
import json
import pickle
import joblib
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import logging

# Import optimization results
from backtest_engine_advanced import (
    AdvancedBacktestEngine,
    BETTING_MARKETS,
    ModelFactory,
    OptimizedConfigGenerator
)

warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# OPTIMIZED MODEL TRAINER
# ============================================================================

class OptimizedModelTrainer:
    """Train and save optimized models based on backtest results"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with optimized configuration"""
        self.config = self._load_config(config_path)
        self.models = {}
        self.scalers = {}
        self.feature_configs = {}
        self.model_factory = ModelFactory()
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load optimized configuration"""
        if config_path is None:
            config_path = Path("outputs") / "production_config.json"
        
        if not Path(config_path).exists():
            logger.warning(f"Config file not found at {config_path}")
            logger.info("Run backtest_engine_advanced.py first to generate config")
            return {}
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def train_all_markets(self, data_path: str, save_models: bool = True) -> Dict:
        """Train optimized models for all markets"""
        
        logger.info("="*60)
        logger.info("TRAINING OPTIMIZED MODELS")
        logger.info("="*60)
        
        # Load data
        if Path(data_path).suffix == '.parquet':
            df = pd.read_parquet(data_path)
        else:
            df = pd.read_csv(data_path)
        
        logger.info(f"Loaded {len(df)} samples")
        
        # Create target columns
        self._create_targets(df)
        
        # Get feature columns
        feature_cols = self._get_feature_columns(df)
        logger.info(f"Using {len(feature_cols)} features")
        
        results = {}
        
        # Train model for each market
        for market_name, market_config in self.config.get('markets', {}).items():
            if not market_config.get('enabled', True):
                continue
            
            logger.info(f"\n{'='*40}")
            logger.info(f"Training: {BETTING_MARKETS.get(market_name, {}).get('description', market_name)}")
            logger.info(f"{'='*40}")
            
            # Check if target exists
            target_col = BETTING_MARKETS.get(market_name, {}).get('target_column')
            if not target_col or target_col not in df.columns:
                logger.warning(f"Target column {target_col} not found, skipping...")
                continue
            
            # Prepare data
            X = df[feature_cols].values
            y = df[target_col].values
            
            # Remove NaN
            mask = ~np.isnan(y)
            X = X[mask]
            y = y[mask]
            
            # Train model based on configuration
            if market_config.get('prediction_method') == 'ensemble':
                model, scaler = self._train_ensemble_model(
                    X, y, 
                    market_name,
                    market_config.get('ensemble_weights', {})
                )
            else:
                model, scaler = self._train_single_model(
                    X, y,
                    market_name,
                    market_config.get('model', 'random_forest'),
                    market_config.get('hyperparameters', {})
                )
            
            # Store model and configuration
            self.models[market_name] = model
            self.scalers[market_name] = scaler
            self.feature_configs[market_name] = {
                'feature_columns': feature_cols,
                'target_column': target_col,
                'expected_accuracy': market_config.get('expected_accuracy', 0),
                'expected_roi': market_config.get('expected_roi', 0),
                'min_confidence': market_config.get('min_confidence', 0.6),
                'top_features': market_config.get('top_features', [])
            }
            
            results[market_name] = {
                'trained': True,
                'model_type': market_config.get('prediction_method'),
                'expected_accuracy': market_config.get('expected_accuracy', 0)
            }
            
            logger.info(f"✅ Model trained successfully")
            logger.info(f"   Expected accuracy: {market_config.get('expected_accuracy', 0):.1%}")
            logger.info(f"   Expected ROI: {market_config.get('expected_roi', 0):.1f}%")
        
        # Save models if requested
        if save_models:
            self._save_models()
        
        return results
    
    def _train_single_model(self, X: np.ndarray, y: np.ndarray, 
                          market_name: str, model_name: str, 
                          hyperparameters: Dict) -> Tuple[Any, StandardScaler]:
        """Train a single optimized model"""
        
        logger.info(f"  Training {model_name}...")
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Get model
        base_models = self.model_factory.get_base_models()
        model = base_models.get(model_name)
        
        if model is None:
            logger.error(f"Model {model_name} not found!")
            return None, None
        
        # Apply hyperparameters
        if hyperparameters:
            try:
                model.set_params(**hyperparameters)
                logger.info(f"  Applied hyperparameters: {hyperparameters}")
            except Exception as e:
                logger.warning(f"  Could not apply hyperparameters: {e}")
        
        # Train model
        model.fit(X_scaled, y)
        
        # Quick validation
        score = model.score(X_scaled, y)
        logger.info(f"  Training score: {score:.3f}")
        
        return model, scaler
    
    def _train_ensemble_model(self, X: np.ndarray, y: np.ndarray,
                            market_name: str, weights: Dict) -> Tuple[Any, StandardScaler]:
        """Train an ensemble of models"""
        
        logger.info(f"  Training ensemble with {len(weights)} models...")
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train each model in ensemble
        ensemble_models = {}
        base_models = self.model_factory.get_base_models()
        
        for model_name, weight in weights.items():
            if weight > 0:
                logger.info(f"    Training {model_name} (weight: {weight:.2f})")
                
                model = base_models.get(model_name)
                if model:
                    model.fit(X_scaled, y)
                    ensemble_models[model_name] = (model, weight)
        
        # Create ensemble wrapper
        ensemble = EnsembleModel(ensemble_models)
        
        return ensemble, scaler
    
    def _create_targets(self, df: pd.DataFrame):
        """Create target columns for all markets"""
        
        if 'FTHG' in df.columns and 'FTAG' in df.columns:
            # Create all target columns
            total_goals = df['FTHG'] + df['FTAG']
            
            # Over/Under
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
            
            # Total Goals Class
            df['TotalGoalsClass'] = pd.cut(
                total_goals,
                bins=[-1, 1.5, 3.5, 100],
                labels=['0-1', '2-3', '4+']
            )
            
            # Correct Score Class
            df['CorrectScoreClass'] = df.apply(
                lambda x: f"{int(x['FTHG'])}-{int(x['FTAG'])}" 
                if f"{int(x['FTHG'])}-{int(x['FTAG'])}" in ['0-0', '1-0', '0-1', '1-1', '2-1', '1-2', '2-0', '0-2']
                else 'Other',
                axis=1
            )
    
    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get feature columns from dataframe"""
        
        # Exclude target and metadata columns
        exclude = ['Date', 'HomeTeam', 'AwayTeam', 'FTR', 'FTHG', 'FTAG',
                  'HTHG', 'HTAG', 'HTR', 'Referee', 'HS', 'AS', 'HST', 'AST',
                  'HF', 'AF', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR'] + \
                 [BETTING_MARKETS[m]['target_column'] for m in BETTING_MARKETS]
        
        feature_cols = [col for col in df.columns 
                       if col not in exclude and not col.startswith('y_')]
        
        # Remove any remaining target columns
        feature_cols = [col for col in feature_cols 
                       if not any(x in col for x in ['Over', 'BTTS', 'DC_', 'AH_', 
                                                     'CS_', 'WTN_', 'Class'])]
        
        return feature_cols
    
    def _save_models(self):
        """Save all trained models"""
        
        output_dir = Path("models") / "optimized"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save each model
        for market_name, model in self.models.items():
            # Save model
            model_path = output_dir / f"{market_name}_model.pkl"
            joblib.dump(model, model_path)
            
            # Save scaler
            scaler_path = output_dir / f"{market_name}_scaler.pkl"
            joblib.dump(self.scalers[market_name], scaler_path)
            
            # Save configuration
            config_path = output_dir / f"{market_name}_config.json"
            with open(config_path, 'w') as f:
                json.dump(self.feature_configs[market_name], f, indent=2)
        
        # Save master configuration
        master_config = {
            'version': '2.0',
            'created': datetime.now().isoformat(),
            'markets': list(self.models.keys()),
            'feature_configs': self.feature_configs
        }
        
        master_path = output_dir / "master_config.json"
        with open(master_path, 'w') as f:
            json.dump(master_config, f, indent=2)
        
        logger.info(f"\n💾 Models saved to {output_dir}")
        logger.info(f"   {len(self.models)} models saved")

# ============================================================================
# ENSEMBLE MODEL WRAPPER
# ============================================================================

class EnsembleModel:
    """Wrapper for ensemble of models"""
    
    def __init__(self, models: Dict[str, Tuple[Any, float]]):
        """
        Initialize ensemble
        
        Args:
            models: Dictionary of (model, weight) tuples
        """
        self.models = models
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using weighted ensemble"""
        
        predictions = []
        weights = []
        
        for model_name, (model, weight) in self.models.items():
            pred = model.predict(X)
            predictions.append(pred)
            weights.append(weight)
        
        # Weighted average for binary/regression
        # For multiclass, would need different approach
        weighted_pred = np.average(predictions, axis=0, weights=weights)
        
        # Threshold for binary classification
        if len(np.unique(weighted_pred)) > 2:
            return weighted_pred
        else:
            return (weighted_pred > 0.5).astype(int)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities"""
        
        probas = []
        weights = []
        
        for model_name, (model, weight) in self.models.items():
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(X)
                probas.append(proba)
                weights.append(weight)
        
        if not probas:
            # Fallback to predict
            pred = self.predict(X)
            # Convert to probability-like format
            if len(pred.shape) == 1:
                proba = np.zeros((len(pred), 2))
                proba[:, 1] = pred
                proba[:, 0] = 1 - pred
                return proba
            return pred
        
        # Weighted average of probabilities
        return np.average(probas, axis=0, weights=weights)

# ============================================================================
# AUTO-TUNER
# ============================================================================

class AutoTuner:
    """Automated tuning system that continuously improves models"""
    
    def __init__(self):
        """Initialize auto-tuner"""
        self.tune_history = []
        self.best_configs = {}
        
    def auto_tune_pipeline(self, 
                          data_path: str,
                          n_iterations: int = 5,
                          target_accuracy: float = 0.65) -> Dict:
        """
        Automatically tune the entire pipeline
        
        Args:
            data_path: Path to historical data
            n_iterations: Number of tuning iterations
            target_accuracy: Target accuracy to achieve
        """
        
        logger.info("="*60)
        logger.info("STARTING AUTO-TUNING PIPELINE")
        logger.info("="*60)
        logger.info(f"Iterations: {n_iterations}")
        logger.info(f"Target accuracy: {target_accuracy:.1%}")
        
        results = []
        
        for iteration in range(n_iterations):
            logger.info(f"\n{'='*40}")
            logger.info(f"ITERATION {iteration + 1}/{n_iterations}")
            logger.info(f"{'='*40}")
            
            # Run backtest with different settings
            engine = AdvancedBacktestEngine(data_path)
            engine.load_data()
            
            # Vary parameters for each iteration
            test_size = 0.15 + (iteration * 0.02)  # 15% to 25%
            n_splits = 3 + iteration  # 3 to 7 splits
            
            logger.info(f"Test size: {test_size:.1%}")
            logger.info(f"CV splits: {n_splits}")
            
            # Run optimization
            backtest_results = engine.run_complete_backtest(
                test_size=test_size,
                n_splits=n_splits,
                optimize_hyperparameters=True,
                n_jobs=-1
            )
            
            # Calculate average accuracy
            avg_accuracy = np.mean([opt.expected_accuracy for opt in backtest_results.values()])
            
            results.append({
                'iteration': iteration + 1,
                'test_size': test_size,
                'n_splits': n_splits,
                'avg_accuracy': avg_accuracy,
                'results': backtest_results
            })
            
            logger.info(f"\nIteration {iteration + 1} Results:")
            logger.info(f"  Average accuracy: {avg_accuracy:.1%}")
            
            # Check if target reached
            if avg_accuracy >= target_accuracy:
                logger.info(f"✅ Target accuracy reached!")
                break
            
            # Update best configs
            if not self.best_configs or avg_accuracy > max(r['avg_accuracy'] for r in results[:-1]):
                self.best_configs = backtest_results
                logger.info(f"  🎯 New best configuration found!")
        
        # Generate final optimized configuration
        if self.best_configs:
            config_gen = OptimizedConfigGenerator()
            config_gen.generate_production_config(self.best_configs)
        
        # Train final models
        logger.info("\n" + "="*60)
        logger.info("TRAINING FINAL OPTIMIZED MODELS")
        logger.info("="*60)
        
        trainer = OptimizedModelTrainer()
        trainer.train_all_markets(data_path, save_models=True)
        
        # Generate report
        self._generate_tuning_report(results)
        
        return {
            'iterations': len(results),
            'best_accuracy': max(r['avg_accuracy'] for r in results),
            'target_reached': max(r['avg_accuracy'] for r in results) >= target_accuracy,
            'results': results
        }
    
    def _generate_tuning_report(self, results: List[Dict]):
        """Generate tuning report"""
        
        output_path = Path("outputs") / f"tuning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Auto-Tuning Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
                .container { max-width: 1200px; margin: auto; background: white; padding: 30px; border-radius: 10px; }
                h1 { color: #333; text-align: center; }
                .chart { margin: 30px 0; padding: 20px; background: #f9f9f9; border-radius: 5px; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th { background: #4CAF50; color: white; padding: 10px; }
                td { padding: 8px; border-bottom: 1px solid #ddd; }
                .best { background: #d4edda; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Auto-Tuning Report</h1>
                <p>Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """</p>
                
                <h2>Tuning Progress</h2>
                <table>
                    <tr>
                        <th>Iteration</th>
                        <th>Test Size</th>
                        <th>CV Splits</th>
                        <th>Avg Accuracy</th>
                    </tr>
        """
        
        best_iteration = max(results, key=lambda x: x['avg_accuracy'])
        
        for result in results:
            is_best = result == best_iteration
            row_class = 'class="best"' if is_best else ''
            
            html += f"""
                    <tr {row_class}>
                        <td>{result['iteration']}</td>
                        <td>{result['test_size']:.1%}</td>
                        <td>{result['n_splits']}</td>
                        <td>{result['avg_accuracy']:.1%}</td>
                    </tr>
            """
        
        html += f"""
                </table>
                
                <h2>Best Configuration</h2>
                <p>Achieved in iteration {best_iteration['iteration']} with {best_iteration['avg_accuracy']:.1%} average accuracy</p>
                
                <h2>Market Performance</h2>
                <table>
                    <tr>
                        <th>Market</th>
                        <th>Expected Accuracy</th>
                        <th>Expected ROI</th>
                        <th>Best Model</th>
                    </tr>
        """
        
        if best_iteration.get('results'):
            for market_name, opt in best_iteration['results'].items():
                html += f"""
                    <tr>
                        <td>{BETTING_MARKETS.get(market_name, {}).get('description', market_name)}</td>
                        <td>{opt.expected_accuracy:.1%}</td>
                        <td>{opt.expected_roi:.1f}%</td>
                        <td>{opt.best_model}</td>
                    </tr>
                """
        
        html += """
                </table>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"\n📄 Tuning report saved to {output_path}")

# ============================================================================
# QUICK TUNER
# ============================================================================

def quick_tune_single_market(market_name: str, data_path: str) -> Dict:
    """Quick tune a single market"""
    
    logger.info(f"Quick tuning {market_name}...")
    
    # Run focused backtest
    engine = AdvancedBacktestEngine(data_path)
    engine.load_data()
    
    # Modify BETTING_MARKETS to only include target market
    original_markets = BETTING_MARKETS.copy()
    BETTING_MARKETS.clear()
    BETTING_MARKETS[market_name] = original_markets[market_name]
    
    # Run optimization
    results = engine.run_complete_backtest(
        test_size=0.2,
        n_splits=5,
        optimize_hyperparameters=True,
        n_jobs=-1
    )
    
    # Restore markets
    BETTING_MARKETS.clear()
    BETTING_MARKETS.update(original_markets)
    
    if market_name in results:
        logger.info(f"✅ Optimization complete!")
        logger.info(f"   Expected accuracy: {results[market_name].expected_accuracy:.1%}")
        logger.info(f"   Expected ROI: {results[market_name].expected_roi:.1f}%")
        
        return {
            'market': market_name,
            'optimization': results[market_name],
            'success': True
        }
    
    return {'success': False}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution"""
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║           AUTOMATED MODEL TUNING & OPTIMIZATION               ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    print("\n1. Run full auto-tuning pipeline")
    print("2. Train models with existing config")
    print("3. Quick tune single market")
    print("4. Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    # Find data file
    data_files = [
        Path("data/processed/features.parquet"),
        Path("features.parquet"),
        Path("historical_data.parquet"),
        Path("historical_data.csv")
    ]
    
    data_path = None
    for file in data_files:
        if file.exists():
            data_path = str(file)
            break
    
    if not data_path:
        print("❌ No data file found!")
        return
    
    print(f"\n✅ Using data: {data_path}")
    
    if choice == "1":
        # Full auto-tuning
        tuner = AutoTuner()
        
        n_iterations = input("Number of iterations (default=5): ").strip()
        n_iterations = int(n_iterations) if n_iterations else 5
        
        target = input("Target accuracy (default=0.65): ").strip()
        target = float(target) if target else 0.65
        
        results = tuner.auto_tune_pipeline(
            data_path=data_path,
            n_iterations=n_iterations,
            target_accuracy=target
        )
        
        print("\n✅ Auto-tuning complete!")
        print(f"   Best accuracy: {results['best_accuracy']:.1%}")
        print(f"   Target reached: {results['target_reached']}")
        
    elif choice == "2":
        # Train with existing config
        trainer = OptimizedModelTrainer()
        
        if not trainer.config:
            print("❌ No configuration found!")
            print("   Run backtest_engine_advanced.py first")
            return
        
        results = trainer.train_all_markets(data_path, save_models=True)
        
        print("\n✅ Training complete!")
        print(f"   Models trained: {len(results)}")
        
    elif choice == "3":
        # Quick tune single market
        print("\nAvailable markets:")
        for i, (market_name, config) in enumerate(BETTING_MARKETS.items(), 1):
            print(f"{i}. {config['description']}")
        
        selection = input("\nSelect market number: ").strip()
        
        try:
            market_idx = int(selection) - 1
            market_name = list(BETTING_MARKETS.keys())[market_idx]
            
            result = quick_tune_single_market(market_name, data_path)
            
            if result['success']:
                print(f"\n✅ {market_name} tuned successfully!")
            else:
                print(f"\n❌ Tuning failed for {market_name}")
                
        except (ValueError, IndexError):
            print("❌ Invalid selection")
    
    print("\n📁 Check outputs/ folder for results and reports")

if __name__ == "__main__":
    main()

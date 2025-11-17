#!/usr/bin/env python3
"""
NFL Backtesting Engine - Walk-Forward Validation

Tests prediction system on historical NFL data with NO data leakage.
Trains models on past data only, predicts future weeks.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import tempfile
import shutil

from config import (
    PROCESSED_DIR, OUTPUT_DIR, MODEL_ARTIFACTS_DIR,
    log_header
)
from progress_utils import Timer


class NFLBacktestEngine:
    """Walk-forward backtesting for NFL predictions"""

    def __init__(self,
                 start_season: int,
                 end_season: int,
                 test_window_weeks: int = 1,
                 min_training_games: int = 100):
        """
        Initialize backtest engine

        Args:
            start_season: First season to test (e.g., 2022)
            end_season: Last season to test (e.g., 2024)
            test_window_weeks: Weeks per test period (default 1 = weekly)
            min_training_games: Minimum training data required
        """
        self.start_season = start_season
        self.end_season = end_season
        self.test_window_weeks = test_window_weeks
        self.min_training_games = min_training_games

        self.results = []
        self.predictions_log = []

    def load_historical_data(self) -> pd.DataFrame:
        """Load full historical games dataset"""
        data_path = PROCESSED_DIR / "historical_games.parquet"

        if not data_path.exists():
            raise FileNotFoundError(
                f"Historical data not found at {data_path}. "
                "Run data ingestion first."
            )

        print(f"📂 Loading historical data from {data_path}")
        df = pd.read_parquet(data_path)

        # Ensure we have completed games with results
        df = df[df['home_score'].notna() & df['away_score'].notna()].copy()

        print(f"   ✅ Loaded {len(df)} completed games")
        print(f"   Seasons: {df['season'].min()} - {df['season'].max()}")
        print(f"   Weeks: {df['week'].min()} - {df['week'].max()}")

        return df

    def get_test_periods(self) -> List[Tuple[int, int, int, int]]:
        """
        Generate list of test periods (season, start_week, end_week)

        Returns:
            List of (season, start_week, end_week, test_period_id)
        """
        periods = []
        period_id = 1

        for season in range(self.start_season, self.end_season + 1):
            # NFL regular season: weeks 1-18
            for week in range(1, 19, self.test_window_weeks):
                end_week = min(week + self.test_window_weeks - 1, 18)
                periods.append((season, week, end_week, period_id))
                period_id += 1

        return periods

    def split_data(self,
                   df: pd.DataFrame,
                   test_season: int,
                   test_week_start: int,
                   test_week_end: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split into train/test ensuring NO data leakage

        Args:
            df: Full dataset
            test_season: Season to test
            test_week_start: First week of test period
            test_week_end: Last week of test period

        Returns:
            (train_df, test_df)
        """
        # Training: all games BEFORE test period
        train_df = df[
            (df['season'] < test_season) |
            ((df['season'] == test_season) & (df['week'] < test_week_start))
        ].copy()

        # Test: only games in test period
        test_df = df[
            (df['season'] == test_season) &
            (df['week'] >= test_week_start) &
            (df['week'] <= test_week_end)
        ].copy()

        return train_df, test_df

    def train_models_on_period(self, train_df: pd.DataFrame) -> bool:
        """
        Train models using only training data

        Args:
            train_df: Training data

        Returns:
            True if training succeeded
        """
        print("   🔧 Building features for training data...")

        try:
            # Build features from training data only
            from features import NFLFeatureEngineer

            engineer = NFLFeatureEngineer(train_df)
            features_df = engineer.create_features()

            if features_df.empty:
                print("   ⚠️ No features created")
                return False

            # Save temporary features
            temp_features = PROCESSED_DIR / "temp_backtest_features.parquet"
            features_df.to_parquet(temp_features)

            print("   🤖 Training models...")

            # Train models
            from models import NFLModelTrainer

            trainer = NFLModelTrainer(features_df)
            results = trainer.train_all_markets()

            if not results:
                print("   ⚠️ No models trained")
                return False

            # Save models to temporary directory
            temp_models_dir = MODEL_ARTIFACTS_DIR / "backtest_temp"
            temp_models_dir.mkdir(exist_ok=True)

            trainer.save_models(temp_models_dir)

            # Cleanup temp features
            temp_features.unlink(missing_ok=True)

            return True

        except Exception as e:
            print(f"   ⚠️ Training failed: {e}")
            return False

    def generate_predictions(self, test_df: pd.DataFrame, train_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate predictions for test period

        Args:
            test_df: Test data (fixtures)
            train_df: Training data (for feature engineering)

        Returns:
            DataFrame with predictions
        """
        print("   🔮 Generating predictions...")

        try:
            # Build features for test data
            from features import NFLFeatureEngineer

            # Combine train + test for feature engineering (ELO, rolling stats)
            combined_df = pd.concat([train_df, test_df], ignore_index=True)

            engineer = NFLFeatureEngineer(combined_df)
            features_df = engineer.create_features()

            # Get only test period features
            test_features = features_df[
                (features_df['season'] == test_df['season'].iloc[0]) &
                (features_df['week'].isin(test_df['week'].unique()))
            ].copy()

            if test_features.empty:
                print("   ⚠️ No test features created")
                return pd.DataFrame()

            # Load models and predict
            from models import NFLModelTrainer, NFLEnsemblePredictor
            import joblib

            temp_models_dir = MODEL_ARTIFACTS_DIR / "backtest_temp"

            if not temp_models_dir.exists():
                print("   ⚠️ No models found")
                return pd.DataFrame()

            # Load models
            models = {}
            for model_file in temp_models_dir.glob("*.pkl"):
                model_name = model_file.stem
                models[model_name] = joblib.load(model_file)

            # Create ensemble predictor
            ensemble = NFLEnsemblePredictor(models)

            # Prepare features
            exclude_cols = ['season', 'week', 'home_team', 'away_team',
                          'result', 'home_score', 'away_score', 'total_score', 'spread_result']
            feature_cols = [col for col in test_features.columns if col not in exclude_cols]

            X_test = test_features[feature_cols].fillna(0).values

            # Generate predictions
            predictions = []

            for i, (idx, game) in enumerate(test_features.iterrows()):
                pred = {
                    'season': game['season'],
                    'week': game['week'],
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'actual_home_score': test_df[
                        (test_df['home_team'] == game['home_team']) &
                        (test_df['away_team'] == game['away_team'])
                    ]['home_score'].iloc[0] if len(test_df) > 0 else None,
                    'actual_away_score': test_df[
                        (test_df['home_team'] == game['home_team']) &
                        (test_df['away_team'] == game['away_team'])
                    ]['away_score'].iloc[0] if len(test_df) > 0 else None,
                }

                X_game = X_test[i:i+1]

                # Predict each market
                try:
                    # Moneyline
                    ml_proba = ensemble.predict(X_game, 'MONEYLINE', method='average')
                    pred['ml_home_prob'] = ml_proba[0][1]
                    pred['ml_away_prob'] = ml_proba[0][0]
                    pred['ml_pick'] = 'HOME' if ml_proba[0][1] > 0.5 else 'AWAY'

                    # Spread
                    spread_proba = ensemble.predict(X_game, 'SPREAD', method='average')
                    pred['spread_cover_prob'] = spread_proba[0][1]
                    pred['spread_pick'] = 'COVER' if spread_proba[0][1] > 0.5 else 'NO_COVER'

                    # Total
                    total_proba = ensemble.predict(X_game, 'TOTAL', method='average')
                    pred['total_over_prob'] = total_proba[0][1]
                    pred['total_pick'] = 'OVER' if total_proba[0][1] > 0.5 else 'UNDER'

                except Exception as e:
                    print(f"   ⚠️ Prediction error: {e}")

                predictions.append(pred)

            return pd.DataFrame(predictions)

        except Exception as e:
            print(f"   ⚠️ Prediction generation failed: {e}")
            return pd.DataFrame()

    def evaluate_predictions(self, predictions: pd.DataFrame) -> Dict:
        """
        Evaluate prediction accuracy

        Args:
            predictions: DataFrame with predictions and actual results

        Returns:
            Dict with evaluation metrics
        """
        if predictions.empty:
            return {}

        results = {
            'total_games': len(predictions),
            'markets': {}
        }

        # Evaluate Moneyline
        if 'ml_pick' in predictions.columns and 'actual_home_score' in predictions.columns:
            ml_actual = []
            ml_pred = []

            for _, game in predictions.iterrows():
                if pd.notna(game['actual_home_score']) and pd.notna(game['actual_away_score']):
                    actual = 'HOME' if game['actual_home_score'] > game['actual_away_score'] else 'AWAY'
                    ml_actual.append(actual)
                    ml_pred.append(game['ml_pick'])

            if ml_actual:
                correct = sum(a == p for a, p in zip(ml_actual, ml_pred))
                results['markets']['MONEYLINE'] = {
                    'total': len(ml_actual),
                    'correct': correct,
                    'accuracy': correct / len(ml_actual),
                    'profit_units': correct - len(ml_actual)  # Simplified
                }

        # Evaluate Spread (simplified - would need actual spread lines)
        # Skipping for now as it requires spread data

        # Evaluate Total (simplified - would need actual totals)
        # Skipping for now as it requires total lines

        return results

    def run_backtest(self) -> pd.DataFrame:
        """
        Run full walk-forward backtest

        Returns:
            Summary DataFrame
        """
        log_header(f"NFL Backtest: {self.start_season}-{self.end_season}")

        # Load data
        full_df = self.load_historical_data()

        # Filter to backtest seasons
        full_df = full_df[
            (full_df['season'] >= self.start_season) &
            (full_df['season'] <= self.end_season)
        ]

        # Get test periods
        test_periods = self.get_test_periods()
        print(f"\n📅 Testing {len(test_periods)} periods\n")

        all_results = []

        for season, week_start, week_end, period_id in test_periods:
            print(f"\n{'='*60}")
            print(f"Period {period_id}: Season {season}, Week {week_start}-{week_end}")
            print('='*60)

            # Split data
            train_df, test_df = self.split_data(full_df, season, week_start, week_end)

            if len(train_df) < self.min_training_games:
                print(f"   ⚠️ Skipping: insufficient training data ({len(train_df)} games)")
                continue

            if len(test_df) == 0:
                print(f"   ⚠️ Skipping: no test games")
                continue

            print(f"   📊 Training: {len(train_df)} games | Testing: {len(test_df)} games")

            # Train models
            if not self.train_models_on_period(train_df):
                print(f"   ⚠️ Training failed, skipping period")
                continue

            # Generate predictions
            predictions = self.generate_predictions(test_df, train_df)

            if predictions.empty:
                print(f"   ⚠️ No predictions generated")
                continue

            # Evaluate
            period_results = self.evaluate_predictions(predictions)
            period_results['season'] = season
            period_results['week_start'] = week_start
            period_results['week_end'] = week_end
            period_results['period_id'] = period_id

            all_results.append(period_results)

            # Store predictions
            self.predictions_log.extend(predictions.to_dict('records'))

            # Print summary
            for market, stats in period_results.get('markets', {}).items():
                acc = stats.get('accuracy', 0)
                print(f"   • {market}: {acc:.1%} ({stats['correct']}/{stats['total']})")

        self.results = all_results
        return self.generate_summary()

    def generate_summary(self) -> pd.DataFrame:
        """Generate summary statistics"""
        if not self.results:
            print("⚠️ No results to summarize")
            return pd.DataFrame()

        log_header("Backtest Summary")

        # Aggregate by market
        market_summary = {}
        all_markets = set()

        for result in self.results:
            all_markets.update(result.get('markets', {}).keys())

        for market in all_markets:
            total_games = 0
            total_correct = 0
            total_profit = 0

            for result in self.results:
                if market in result.get('markets', {}):
                    stats = result['markets'][market]
                    total_games += stats['total']
                    total_correct += stats['correct']
                    total_profit += stats.get('profit_units', 0)

            market_summary[market] = {
                'Total_Games': total_games,
                'Correct': total_correct,
                'Accuracy': total_correct / total_games if total_games > 0 else 0,
                'Profit_Units': total_profit,
                'ROI': (total_profit / total_games * 100) if total_games > 0 else 0
            }

        summary_df = pd.DataFrame.from_dict(market_summary, orient='index')

        print("\n" + summary_df.to_string())

        # Save results
        output_path = OUTPUT_DIR / "backtest_summary.csv"
        summary_df.to_csv(output_path)
        print(f"\n✅ Saved summary to {output_path}")

        return summary_df

    def export_detailed_results(self) -> Path:
        """Export detailed predictions log"""
        if not self.predictions_log:
            print("⚠️ No predictions to export")
            return None

        predictions_df = pd.DataFrame(self.predictions_log)
        output_path = OUTPUT_DIR / "backtest_predictions.csv"
        predictions_df.to_csv(output_path, index=False)

        print(f"✅ Saved {len(predictions_df)} predictions to {output_path}")
        return output_path

    def cleanup(self):
        """Clean up temporary files"""
        temp_models_dir = MODEL_ARTIFACTS_DIR / "backtest_temp"
        if temp_models_dir.exists():
            shutil.rmtree(temp_models_dir)


def main():
    """Main backtest runner"""
    import argparse

    parser = argparse.ArgumentParser(description='Backtest NFL prediction system')
    parser.add_argument('--start', type=int, default=2022,
                       help='Start season (default: 2022)')
    parser.add_argument('--end', type=int, default=2024,
                       help='End season (default: 2024)')
    parser.add_argument('--weeks', type=int, default=1,
                       help='Test window in weeks (default: 1)')

    args = parser.parse_args()

    engine = NFLBacktestEngine(
        start_season=args.start,
        end_season=args.end,
        test_window_weeks=args.weeks
    )

    try:
        engine.run_backtest()
        engine.export_detailed_results()
    finally:
        engine.cleanup()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
NFL Game Predictions

Generates predictions for upcoming NFL games using trained models.
Outputs probabilities for Moneyline, Spread, and Totals markets.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, List
from config import (
    BASE_DIR, MODEL_ARTIFACTS_DIR, PROCESSED_DIR, OUTPUT_DIR,
    PRIMARY_MARKETS, NFL_TEAMS, log_header
)
from progress_utils import Timer, heartbeat
from features import NFLFeatureEngineer
from models import NFLEnsemblePredictor


class NFLPredictor:
    """Generate predictions for NFL games"""

    def __init__(self, models_dir: Path = MODEL_ARTIFACTS_DIR):
        """
        Initialize predictor

        Args:
            models_dir: Directory containing trained models
        """
        self.models_dir = models_dir
        self.models = {}
        self.feature_names = []
        self.load_models()

    def load_models(self):
        """Load all trained models"""
        heartbeat("Loading trained models")

        model_files = list(self.models_dir.glob("*.pkl"))

        if not model_files:
            raise FileNotFoundError(f"No models found in {self.models_dir}")

        for model_path in model_files:
            model_name = model_path.stem
            self.models[model_name] = joblib.load(model_path)
            print(f"  ✅ Loaded {model_name}")

    def prepare_fixtures(self, fixtures_path: str) -> pd.DataFrame:
        """
        Load and prepare upcoming fixtures

        Args:
            fixtures_path: Path to upcoming_fixtures.csv

        Returns:
            DataFrame with fixtures
        """
        heartbeat("Loading upcoming fixtures")

        fixtures = pd.read_csv(fixtures_path)
        print(f"  ✅ Loaded {len(fixtures)} upcoming games")

        return fixtures

    def create_fixture_features(self, fixtures: pd.DataFrame,
                                historical_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create features for upcoming fixtures based on historical data

        Args:
            fixtures: Upcoming games
            historical_df: Historical game data with features

        Returns:
            DataFrame with features for each fixture
        """
        heartbeat("Creating features for fixtures")

        # Initialize feature engineer with historical data
        engineer = NFLFeatureEngineer(historical_df)

        # Update ELO ratings with all historical games
        engineer.update_elo_ratings()

        fixture_features = []

        for idx, game in fixtures.iterrows():
            home_team = game['home_team']
            away_team = game['away_team']

            # Create features for this matchup
            features = {
                'home_team': home_team,
                'away_team': away_team,
                'date': game.get('date', ''),
            }

            # Get current ELO ratings
            features['home_elo'] = engineer.elo_ratings.get(home_team, 1500)
            features['away_elo'] = engineer.elo_ratings.get(away_team, 1500)
            features['elo_diff'] = features['home_elo'] - features['away_elo']

            # Get rolling stats
            for n in [3, 5, 10]:
                home_stats = engineer.get_team_rolling_stats(home_team, historical_df, n)
                away_stats = engineer.get_team_rolling_stats(away_team, historical_df, n)

                for stat, value in home_stats.items():
                    features[f'home_{stat}_L{n}'] = value

                for stat, value in away_stats.items():
                    features[f'away_{stat}_L{n}'] = value

            # Head-to-head
            h2h = historical_df[
                ((historical_df['home_team'] == home_team) & (historical_df['away_team'] == away_team)) |
                ((historical_df['home_team'] == away_team) & (historical_df['away_team'] == home_team))
            ]

            if len(h2h) > 0:
                h2h_wins = sum(
                    (h2h['home_team'] == home_team) & (h2h['home_score'] > h2h['away_score']) |
                    (h2h['away_team'] == home_team) & (h2h['away_score'] > h2h['home_score'])
                )
                features['h2h_win_pct'] = h2h_wins / len(h2h)
                features['h2h_games'] = len(h2h)
            else:
                features['h2h_win_pct'] = 0.5
                features['h2h_games'] = 0

            # Division/Conference
            features['is_divisional'] = engineer._is_divisional(home_team, away_team)
            features['is_conference'] = engineer._is_conference(home_team, away_team)

            # Add any fixture-specific data (spread, total)
            if 'spread' in game and pd.notna(game['spread']):
                features['market_spread'] = game['spread']

            if 'over_under' in game and pd.notna(game['over_under']):
                features['market_total'] = game['over_under']

            fixture_features.append(features)

        features_df = pd.DataFrame(fixture_features)

        # Fill missing values
        numeric_cols = features_df.select_dtypes(include=[np.number]).columns
        features_df[numeric_cols] = features_df[numeric_cols].fillna(
            features_df[numeric_cols].median()
        )

        print(f"  ✅ Created {len(features_df.columns)} features")

        return features_df

    def predict_games(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate predictions for games

        Args:
            features_df: Features for each game

        Returns:
            DataFrame with predictions
        """
        heartbeat("Generating predictions")

        # Prepare feature matrix (exclude identifiers)
        exclude_cols = ['home_team', 'away_team', 'date', 'market_spread', 'market_total']
        feature_cols = [col for col in features_df.columns if col not in exclude_cols]

        X = features_df[feature_cols].values

        # Initialize ensemble predictor
        ensemble = NFLEnsemblePredictor(self.models)

        predictions = []

        for i, (idx, game) in enumerate(features_df.iterrows()):
            game_pred = {
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'home_team_full': NFL_TEAMS.get(game['home_team'], game['home_team']),
                'away_team_full': NFL_TEAMS.get(game['away_team'], game['away_team']),
            }

            # Get feature row
            X_game = X[i:i+1]

            # Predict each market
            for market in PRIMARY_MARKETS:
                try:
                    proba = ensemble.predict(X_game, market, method='average')

                    if market == "MONEYLINE":
                        # proba[:,1] = probability of home win
                        game_pred['moneyline_home_prob'] = proba[0][1]
                        game_pred['moneyline_away_prob'] = proba[0][0]
                        game_pred['moneyline_pick'] = 'HOME' if proba[0][1] > 0.5 else 'AWAY'
                        game_pred['moneyline_confidence'] = max(proba[0])

                    elif market == "SPREAD":
                        # proba[:,1] = probability of covering spread
                        game_pred['spread_cover_prob'] = proba[0][1]
                        game_pred['spread_nocover_prob'] = proba[0][0]
                        if 'market_spread' in game:
                            game_pred['spread_line'] = game['market_spread']
                        game_pred['spread_pick'] = 'COVER' if proba[0][1] > 0.5 else 'NO_COVER'
                        game_pred['spread_confidence'] = max(proba[0])

                    elif market == "TOTAL":
                        # proba[:,1] = probability of over
                        game_pred['total_over_prob'] = proba[0][1]
                        game_pred['total_under_prob'] = proba[0][0]
                        if 'market_total' in game:
                            game_pred['total_line'] = game['market_total']
                        game_pred['total_pick'] = 'OVER' if proba[0][1] > 0.5 else 'UNDER'
                        game_pred['total_confidence'] = max(proba[0])

                except Exception as e:
                    print(f"  ⚠️  Error predicting {market}: {e}")

            predictions.append(game_pred)

        predictions_df = pd.DataFrame(predictions)
        print(f"  ✅ Generated predictions for {len(predictions_df)} games")

        return predictions_df

    def save_predictions(self, predictions: pd.DataFrame, output_file: str = None):
        """Save predictions to file"""
        if output_file is None:
            output_file = OUTPUT_DIR / "weekly_predictions.csv"

        predictions.to_csv(output_file, index=False)
        print(f"  ✅ Saved predictions to {output_file}")

        # Also create Excel version
        try:
            excel_file = str(output_file).replace('.csv', '.xlsx')
            predictions.to_excel(excel_file, index=False)
            print(f"  ✅ Saved to {excel_file}")
        except ImportError:
            pass


def predict_upcoming_games(
    fixtures_path: str = None,
    historical_path: str = None,
    output_path: str = None
):
    """
    Main prediction function

    Args:
        fixtures_path: Path to upcoming_fixtures.csv
        historical_path: Path to historical games
        output_path: Where to save predictions
    """
    if fixtures_path is None:
        fixtures_path = BASE_DIR / "upcoming_fixtures.csv"

    if historical_path is None:
        historical_path = PROCESSED_DIR / "historical_games.parquet"

    log_header("NFL Game Predictions")

    with Timer("Generating predictions"):
        # Initialize predictor
        predictor = NFLPredictor()

        # Load fixtures
        fixtures = predictor.prepare_fixtures(fixtures_path)

        # Load historical data
        print(f"📂 Loading historical data from {historical_path}")
        historical_df = pd.read_parquet(historical_path)
        print(f"  ✅ Loaded {len(historical_df)} historical games")

        # Create features
        features_df = predictor.create_fixture_features(fixtures, historical_df)

        # Generate predictions
        predictions = predictor.predict_games(features_df)

        # Save
        predictor.save_predictions(predictions, output_path)

    print("\n✅ Predictions complete!")
    print(f"📁 Output: {output_path or OUTPUT_DIR / 'weekly_predictions.csv'}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Predict NFL games')
    parser.add_argument('--fixtures', type=str,
                       help='Path to upcoming fixtures CSV')
    parser.add_argument('--historical', type=str,
                       help='Path to historical games parquet')
    parser.add_argument('--output', type=str,
                       help='Output file path')

    args = parser.parse_args()

    predict_upcoming_games(
        fixtures_path=args.fixtures,
        historical_path=args.historical,
        output_path=args.output
    )

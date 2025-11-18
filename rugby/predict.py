#!/usr/bin/env python3
"""
Rugby Union Match Predictions

Makes predictions for upcoming rugby matches.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from config import (
    RAW_DIR, OUTPUT_DIR,
    PRIMARY_MARKETS, log_header
)
from features import RugbyFeatureEngineer
from models import RugbyModelTrainer
from progress_utils import Timer

class RugbyPredictor:
    """Makes predictions for rugby matches"""

    def __init__(self):
        self.feature_engineer = RugbyFeatureEngineer()
        self.model_trainer = RugbyModelTrainer()
        self.models_loaded = False

    def load_historical_data(self) -> pd.DataFrame:
        """Load historical data to build context"""
        print("Loading historical data for context...")

        raw_files = list(RAW_DIR.glob("rugby_*.csv"))

        if not raw_files:
            print("⚠️  No historical data found")
            return pd.DataFrame()

        all_data = []
        for file in raw_files:
            df = pd.read_csv(file)
            all_data.append(df)

        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"  Loaded {len(combined_df):,} historical matches")

        # Build ELO and H2H from historical data
        if 'date' in combined_df.columns:
            combined_df['date'] = pd.to_datetime(combined_df['date'], errors='coerce')
            combined_df = combined_df.sort_values('date').reset_index(drop=True)

            for idx, match in combined_df.iterrows():
                if 'home_score' in match and 'away_score' in match:
                    home_score = match['home_score']
                    away_score = match['away_score']

                    if home_score > away_score:
                        self.feature_engineer.update_elo(match['home_team'], match['away_team'],
                                                        home_score - away_score)
                        self.feature_engineer.update_h2h(match['home_team'], match['away_team'],
                                                        match['home_team'])
                    elif away_score > home_score:
                        self.feature_engineer.update_elo(match['away_team'], match['home_team'],
                                                        away_score - home_score)
                        self.feature_engineer.update_h2h(match['home_team'], match['away_team'],
                                                        match['away_team'])
                    else:  # Draw
                        self.feature_engineer.update_h2h(match['home_team'], match['away_team'], 'draw')

        print("  ✅ Built ELO and H2H from historical data")
        return combined_df

    def load_models(self, market: str = "MATCH_WINNER"):
        """Load trained models"""
        if not self.models_loaded:
            print(f"Loading models for {market}...")
            self.model_trainer.load_models(market)
            self.models_loaded = True

    def predict_match(self, match: pd.Series, market: str = "MATCH_WINNER") -> Dict:
        """Predict outcome for a single match"""
        # Calculate features
        features = self.feature_engineer.calculate_match_features(match, is_home=True)

        # Convert to DataFrame for model
        feature_df = pd.DataFrame([features])

        exclude_cols = ['match_id', 'date', 'home_team', 'away_team',
                       'target_winner', 'target_total_points', 'target_points_diff']
        feature_cols = [col for col in feature_df.columns if col not in exclude_cols]
        X = feature_df[feature_cols].fillna(0)

        # Make prediction
        probas = self.model_trainer.predict(X, market=market)

        # For 3-way classification: [prob_away_win, prob_draw, prob_home_win]
        prediction = {
            'home_team': match.get('home_team', 'Home'),
            'away_team': match.get('away_team', 'Away'),
            'date': match.get('date', ''),
            'venue': match.get('venue', ''),
            'competition': match.get('competition', ''),
            'away_win_prob': probas[0][0],
            'draw_prob': probas[0][1] if probas.shape[1] > 2 else 0.0,
            'home_win_prob': probas[0][2] if probas.shape[1] > 2 else probas[0][1],
            'predicted_outcome': ['Away Win', 'Draw', 'Home Win'][np.argmax(probas[0])],
            'confidence': max(probas[0]),
            'market': market,
        }

        return prediction

    def predict_upcoming_matches(self, upcoming_file: Path = None,
                                market: str = "MATCH_WINNER") -> pd.DataFrame:
        """Predict all upcoming matches"""
        log_header(f"Rugby Match Predictions - {market}")

        with Timer("Loading historical context"):
            self.load_historical_data()

        self.load_models(market)

        if upcoming_file is None:
            upcoming_file = RAW_DIR / "upcoming_rugby_matches.csv"

        if not upcoming_file.exists():
            print(f"⚠️  Upcoming matches file not found: {upcoming_file}")
            print("  Using sample data for demonstration...")
            # Create sample upcoming matches
            sample_data = pd.DataFrame([
                {'home_team': 'IRE', 'away_team': 'ENG', 'date': '2024-02-10',
                 'venue': 'Aviva Stadium', 'competition': 'Six Nations'},
                {'home_team': 'NZL', 'away_team': 'RSA', 'date': '2024-08-15',
                 'venue': 'Eden Park', 'competition': 'Rugby Championship'},
            ])
            upcoming_df = sample_data
        else:
            upcoming_df = pd.read_csv(upcoming_file)

        print(f"\nPredicting {len(upcoming_df)} upcoming matches...")

        predictions = []
        for idx, match in upcoming_df.iterrows():
            pred = self.predict_match(match, market)
            predictions.append(pred)

        predictions_df = pd.DataFrame(predictions)

        output_file = OUTPUT_DIR / f"rugby_predictions_{market.lower()}.csv"
        predictions_df.to_csv(output_file, index=False)
        print(f"\n✅ Saved {len(predictions_df)} predictions to: {output_file}")

        return predictions_df


def main():
    """Generate predictions"""
    import argparse

    parser = argparse.ArgumentParser(description='Predict rugby matches')
    parser.add_argument('--market', type=str, default='MATCH_WINNER',
                       choices=PRIMARY_MARKETS,
                       help='Market to predict')
    parser.add_argument('--upcoming-file', type=str, default=None,
                       help='Path to upcoming matches CSV')

    args = parser.parse_args()

    upcoming_file = Path(args.upcoming_file) if args.upcoming_file else None

    predictor = RugbyPredictor()
    predictions = predictor.predict_upcoming_matches(upcoming_file, args.market)

    if not predictions.empty:
        print("\n📊 Predictions:")
        print(predictions[[
            'home_team', 'away_team', 'home_win_prob', 'draw_prob',
            'away_win_prob', 'predicted_outcome', 'confidence'
        ]].to_string(index=False))


if __name__ == "__main__":
    main()

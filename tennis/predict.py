#!/usr/bin/env python3
"""
Tennis Match Predictions

Makes predictions for upcoming tennis matches.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from config import (
    RAW_DIR, OUTPUT_DIR, MODEL_ARTIFACTS_DIR,
    PRIMARY_MARKETS, log_header
)
from features import TennisFeatureEngineer
from models import TennisModelTrainer
from progress_utils import Timer

class TennisPredictor:
    """Makes predictions for tennis matches"""

    def __init__(self):
        self.feature_engineer = TennisFeatureEngineer()
        self.model_trainer = TennisModelTrainer()
        self.models_loaded = False

    def load_historical_data(self) -> pd.DataFrame:
        """Load historical data to build context (ELO, H2H, etc.)"""
        print("Loading historical data for context...")

        raw_files = list(RAW_DIR.glob("tennis_*.csv"))

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
        if 'tourney_date' in combined_df.columns:
            combined_df = combined_df.sort_values('tourney_date').reset_index(drop=True)

            for idx, match in combined_df.iterrows():
                if 'winner_id' in match and 'loser_id' in match:
                    winner = match['winner_id'] if match['winner_id'] else match.get('winner_name', '')
                    loser = match['loser_id'] if match['loser_id'] else match.get('loser_name', '')
                    surface = match.get('surface', 'Hard')

                    self.feature_engineer.update_elo(winner, loser, surface)
                    self.feature_engineer.update_h2h(winner, loser, winner)

        print("  ✅ Built ELO and H2H from historical data")
        return combined_df

    def load_models(self, market: str = "MATCH_WINNER"):
        """Load trained models"""
        if not self.models_loaded:
            print(f"Loading models for {market}...")
            self.model_trainer.load_models(market)
            self.models_loaded = True

    def predict_match(self, match: pd.Series, market: str = "MATCH_WINNER") -> Dict:
        """
        Predict outcome for a single match

        Args:
            match: Match data
            market: Market type

        Returns:
            Dictionary with predictions
        """
        # Calculate features
        features = self.feature_engineer.calculate_match_features(match)

        # Convert to DataFrame for model
        feature_df = pd.DataFrame([features])

        # Remove non-feature columns
        exclude_cols = ['match_id', 'date', 'player1', 'player2', 'target']
        feature_cols = [col for col in feature_df.columns if col not in exclude_cols]
        X = feature_df[feature_cols].fillna(0)

        # Make prediction
        probas = self.model_trainer.predict(X, market=market)

        prediction = {
            'player1': match.get('player1_name', match.get('winner_name', 'Player 1')),
            'player2': match.get('player2_name', match.get('loser_name', 'Player 2')),
            'date': match.get('tourney_date', match.get('date', '')),
            'surface': match.get('surface', 'Hard'),
            'tournament': match.get('tourney_name', match.get('tournament', '')),
            'player1_win_prob': probas[0][1],  # Probability player 1 wins
            'player2_win_prob': probas[0][0],  # Probability player 2 wins
            'predicted_winner': match.get('player1_name', 'Player 1') if probas[0][1] > 0.5 else match.get('player2_name', 'Player 2'),
            'confidence': max(probas[0]),
            'market': market,
        }

        return prediction

    def find_value_bets(self, predictions: List[Dict], odds: pd.DataFrame = None,
                       min_edge: float = 0.05) -> List[Dict]:
        """
        Find value bets by comparing model probabilities to market odds

        Args:
            predictions: List of predictions
            odds: DataFrame with betting odds (optional)
            min_edge: Minimum edge required to recommend bet

        Returns:
            List of value bets
        """
        value_bets = []

        for pred in predictions:
            player1_model_prob = pred['player1_win_prob']
            player2_model_prob = pred['player2_win_prob']

            # If we have odds data, calculate value
            if odds is not None:
                # Find matching match in odds data
                match_odds = odds[
                    (odds['player1'] == pred['player1']) &
                    (odds['player2'] == pred['player2'])
                ]

                if not match_odds.empty:
                    player1_odds = match_odds.iloc[0].get('player1_odds', None)
                    player2_odds = match_odds.iloc[0].get('player2_odds', None)

                    if player1_odds:
                        implied_prob_p1 = 1 / player1_odds
                        edge_p1 = player1_model_prob - implied_prob_p1

                        if edge_p1 > min_edge:
                            value_bets.append({
                                **pred,
                                'bet_on': pred['player1'],
                                'model_prob': player1_model_prob,
                                'market_odds': player1_odds,
                                'implied_prob': implied_prob_p1,
                                'edge': edge_p1,
                                'kelly_fraction': edge_p1 / (player1_odds - 1),
                            })

                    if player2_odds:
                        implied_prob_p2 = 1 / player2_odds
                        edge_p2 = player2_model_prob - implied_prob_p2

                        if edge_p2 > min_edge:
                            value_bets.append({
                                **pred,
                                'bet_on': pred['player2'],
                                'model_prob': player2_model_prob,
                                'market_odds': player2_odds,
                                'implied_prob': implied_prob_p2,
                                'edge': edge_p2,
                                'kelly_fraction': edge_p2 / (player2_odds - 1),
                            })

        return value_bets

    def predict_upcoming_matches(self, upcoming_file: Path = None,
                                market: str = "MATCH_WINNER") -> pd.DataFrame:
        """
        Predict all upcoming matches

        Args:
            upcoming_file: Path to upcoming matches CSV
            market: Market type

        Returns:
            DataFrame with predictions
        """
        log_header(f"Tennis Match Predictions - {market}")

        # Load historical data for context
        with Timer("Loading historical context"):
            self.load_historical_data()

        # Load models
        self.load_models(market)

        # Load upcoming matches
        if upcoming_file is None:
            upcoming_file = RAW_DIR / "upcoming_tennis_matches.csv"

        if not upcoming_file.exists():
            print(f"⚠️  Upcoming matches file not found: {upcoming_file}")
            return pd.DataFrame()

        upcoming_df = pd.read_csv(upcoming_file)
        print(f"\nPredicting {len(upcoming_df)} upcoming matches...")

        # Make predictions
        predictions = []
        for idx, match in upcoming_df.iterrows():
            pred = self.predict_match(match, market)
            predictions.append(pred)

        predictions_df = pd.DataFrame(predictions)

        # Try to load odds and find value bets
        odds_file = RAW_DIR / "upcoming_tennis_odds.csv"
        if odds_file.exists():
            odds_df = pd.read_csv(odds_file)
            print(f"\nFinding value bets...")
            value_bets = self.find_value_bets(predictions, odds_df, min_edge=0.05)

            if value_bets:
                print(f"\n🎯 Found {len(value_bets)} value bets!")
                value_df = pd.DataFrame(value_bets)
                value_file = OUTPUT_DIR / "tennis_value_bets.csv"
                value_df.to_csv(value_file, index=False)
                print(f"  Saved to: {value_file}")

        # Save predictions
        output_file = OUTPUT_DIR / f"tennis_predictions_{market.lower()}.csv"
        predictions_df.to_csv(output_file, index=False)
        print(f"\n✅ Saved {len(predictions_df)} predictions to: {output_file}")

        return predictions_df


def main():
    """Generate predictions for upcoming matches"""
    import argparse

    parser = argparse.ArgumentParser(description='Predict tennis matches')
    parser.add_argument('--market', type=str, default='MATCH_WINNER',
                       choices=PRIMARY_MARKETS,
                       help='Market to predict')
    parser.add_argument('--upcoming-file', type=str, default=None,
                       help='Path to upcoming matches CSV')

    args = parser.parse_args()

    upcoming_file = Path(args.upcoming_file) if args.upcoming_file else None

    predictor = TennisPredictor()
    predictions = predictor.predict_upcoming_matches(upcoming_file, args.market)

    if not predictions.empty:
        print("\n📊 Top Predictions:")
        print(predictions.nlargest(10, 'confidence')[
            ['player1', 'player2', 'predicted_winner', 'confidence', 'surface']
        ].to_string(index=False))


if __name__ == "__main__":
    main()

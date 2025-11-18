#!/usr/bin/env python3
"""
Tennis Feature Engineering

Creates tennis-specific features including:
- Surface-specific ELO ratings (critical!)
- Head-to-head records
- Recent form on specific surfaces
- Player ranking trends
- Tournament tier performance
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
from config import SURFACES, USE_ELO, USE_SURFACE_ELO, USE_H2H, log_header
from progress_utils import Timer

class TennisFeatureEngineer:
    """Creates features for tennis match prediction"""

    def __init__(self, k_factor: int = 32):
        self.k_factor = k_factor
        self.player_elo = {}  # Overall ELO
        self.surface_elo = {surface: {} for surface in SURFACES.keys()}  # ELO per surface
        self.h2h_records = {}  # Head-to-head records

    def update_elo(self, winner: str, loser: str, surface: str = None):
        """
        Update ELO ratings after a match

        Args:
            winner: Winner player ID/name
            loser: Loser player ID/name
            surface: Surface type (for surface-specific ELO)
        """
        # Overall ELO
        if USE_ELO:
            winner_elo = self.player_elo.get(winner, 1500)
            loser_elo = self.player_elo.get(loser, 1500)

            # Expected scores
            expected_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
            expected_loser = 1 / (1 + 10 ** ((winner_elo - loser_elo) / 400))

            # Update ELOs
            self.player_elo[winner] = winner_elo + self.k_factor * (1 - expected_winner)
            self.player_elo[loser] = loser_elo + self.k_factor * (0 - expected_loser)

        # Surface-specific ELO (CRITICAL for tennis!)
        if USE_SURFACE_ELO and surface and surface in self.surface_elo:
            winner_surface_elo = self.surface_elo[surface].get(winner, 1500)
            loser_surface_elo = self.surface_elo[surface].get(loser, 1500)

            expected_winner_surface = 1 / (1 + 10 ** ((loser_surface_elo - winner_surface_elo) / 400))
            expected_loser_surface = 1 / (1 + 10 ** ((winner_surface_elo - loser_surface_elo) / 400))

            self.surface_elo[surface][winner] = winner_surface_elo + self.k_factor * (1 - expected_winner_surface)
            self.surface_elo[surface][loser] = loser_surface_elo + self.k_factor * (0 - expected_loser_surface)

    def update_h2h(self, player1: str, player2: str, winner: str):
        """Update head-to-head record"""
        if not USE_H2H:
            return

        key = tuple(sorted([player1, player2]))
        if key not in self.h2h_records:
            self.h2h_records[key] = {player1: 0, player2: 0}

        self.h2h_records[key][winner] += 1

    def get_h2h_features(self, player1: str, player2: str) -> Dict[str, float]:
        """Get head-to-head features"""
        key = tuple(sorted([player1, player2]))

        if key not in self.h2h_records:
            return {
                'p1_h2h_wins': 0,
                'p2_h2h_wins': 0,
                'h2h_total_matches': 0,
                'p1_h2h_win_pct': 0.5,
            }

        p1_wins = self.h2h_records[key].get(player1, 0)
        p2_wins = self.h2h_records[key].get(player2, 0)
        total = p1_wins + p2_wins

        return {
            'p1_h2h_wins': p1_wins,
            'p2_h2h_wins': p2_wins,
            'h2h_total_matches': total,
            'p1_h2h_win_pct': p1_wins / total if total > 0 else 0.5,
        }

    def calculate_match_features(self, match: pd.Series, historical_data: pd.DataFrame = None) -> Dict[str, float]:
        """
        Calculate features for a single match

        Args:
            match: Match data row
            historical_data: Historical matches for context

        Returns:
            Dictionary of features
        """
        player1 = match.get('player1_id', match.get('player1_name', ''))
        player2 = match.get('player2_id', match.get('player2_name', ''))
        surface = match.get('surface', 'Hard')

        features = {}

        # ELO Features
        if USE_ELO:
            features['p1_elo'] = self.player_elo.get(player1, 1500)
            features['p2_elo'] = self.player_elo.get(player2, 1500)
            features['elo_diff'] = features['p1_elo'] - features['p2_elo']

        # Surface-specific ELO (VERY IMPORTANT!)
        if USE_SURFACE_ELO and surface in self.surface_elo:
            features['p1_surface_elo'] = self.surface_elo[surface].get(player1, 1500)
            features['p2_surface_elo'] = self.surface_elo[surface].get(player2, 1500)
            features['surface_elo_diff'] = features['p1_surface_elo'] - features['p2_surface_elo']

        # Ranking features (if available)
        if 'player1_rank' in match and match['player1_rank']:
            features['p1_rank'] = match['player1_rank']
            features['p2_rank'] = match.get('player2_rank', 999)
            features['rank_diff'] = features['p2_rank'] - features['p1_rank']  # Lower rank is better

        # H2H Features
        if USE_H2H:
            h2h_features = self.get_h2h_features(player1, player2)
            features.update(h2h_features)

        # Surface encoding (one-hot)
        for surf in SURFACES.keys():
            features[f'surface_{surf.lower()}'] = 1.0 if surface == surf else 0.0

        # Tournament features
        if 'tourney_level' in match:
            for level in ['G', 'M', 'A', 'D']:  # Grand Slam, Masters, ATP 500/250, Davis Cup
                features[f'tourney_{level}'] = 1.0 if match['tourney_level'] == level else 0.0

        # Match format (Best of 3 vs Best of 5)
        features['best_of_5'] = 1.0 if match.get('best_of', 3) == 5 else 0.0

        # Seed features
        features['p1_seeded'] = 1.0 if match.get('player1_seed') else 0.0
        features['p2_seeded'] = 1.0 if match.get('player2_seed') else 0.0

        # Round features (early rounds vs later rounds)
        round_val = match.get('round', '')
        features['round_final'] = 1.0 if 'F' in round_val else 0.0
        features['round_semi'] = 1.0 if 'SF' in round_val else 0.0
        features['round_quarter'] = 1.0 if 'QF' in round_val else 0.0

        return features

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer all features for a dataset

        Args:
            df: DataFrame with match data

        Returns:
            DataFrame with engineered features
        """
        log_header("Engineering Tennis Features")

        # Ensure data is sorted by date
        if 'tourney_date' in df.columns:
            df = df.sort_values('tourney_date').reset_index(drop=True)
        elif 'date' in df.columns:
            df = df.sort_values('date').reset_index(drop=True)

        feature_rows = []

        with Timer("Processing matches"):
            for idx, match in df.iterrows():
                # Calculate features based on current state
                features = self.calculate_match_features(match, df[:idx] if idx > 0 else None)

                # Determine player IDs/names
                if 'winner_name' in match and 'loser_name' in match:
                    # Historical data format: winner and loser are known
                    # Randomly assign who is player1 vs player2 to avoid bias
                    import random
                    if random.random() < 0.5:
                        player1 = match.get('winner_id', match.get('winner_name', ''))
                        player2 = match.get('loser_id', match.get('loser_name', ''))
                        target = 1  # Player 1 (winner) won
                    else:
                        player1 = match.get('loser_id', match.get('loser_name', ''))
                        player2 = match.get('winner_id', match.get('winner_name', ''))
                        target = 0  # Player 1 (loser) lost

                    features['player1'] = player1
                    features['player2'] = player2
                    features['target'] = target

                    winner = match.get('winner_id', match.get('winner_name', ''))
                    loser = match.get('loser_id', match.get('loser_name', ''))
                    surface = match.get('surface', 'Hard')

                    # Update ELO and H2H after match
                    self.update_elo(winner, loser, surface)
                    self.update_h2h(winner, loser, winner)
                else:
                    # Prediction format: player1 and player2 provided
                    features['player1'] = match.get('player1_id', match.get('player1_name', ''))
                    features['player2'] = match.get('player2_id', match.get('player2_name', ''))

                # Add match identifiers
                features['match_id'] = idx
                features['date'] = match.get('tourney_date', match.get('date', ''))

                feature_rows.append(features)

                if idx > 0 and idx % 1000 == 0:
                    print(f"  Processed {idx:,} matches...")

        features_df = pd.DataFrame(feature_rows)
        print(f"\n✅ Generated {len(features_df)} feature rows with {len(features_df.columns)} columns")

        return features_df


def main():
    """Test feature engineering"""
    from pathlib import Path
    import glob

    # Find historical data files
    raw_files = list(Path("data/raw").glob("tennis_*.csv"))

    if not raw_files:
        print("⚠️  No tennis data files found. Run download_tennis_data.py first.")
        return

    print(f"Found {len(raw_files)} data files")

    # Load and combine data
    all_data = []
    for file in raw_files:
        df = pd.read_csv(file)
        all_data.append(df)

    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Loaded {len(combined_df):,} total matches")

    # Engineer features
    engineer = TennisFeatureEngineer()
    features_df = engineer.engineer_features(combined_df)

    # Save features
    from config import FEATURES_PARQUET
    features_df.to_parquet(FEATURES_PARQUET, index=False)
    print(f"\n✅ Features saved to: {FEATURES_PARQUET}")


if __name__ == "__main__":
    main()

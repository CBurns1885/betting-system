#!/usr/bin/env python3
"""
Rugby Union Feature Engineering

Creates rugby-specific features including:
- ELO ratings
- Home advantage (significant in rugby!)
- Head-to-head records
- Recent form
- Weather impact on scoring
- Altitude advantage
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
from config import (
    USE_ELO, USE_HOME_ADVANTAGE, USE_HEAD_TO_HEAD,
    HOME_ADVANTAGE_FACTOR, ALTITUDE_TEAMS, ALTITUDE_BONUS,
    log_header
)
from progress_utils import Timer

class RugbyFeatureEngineer:
    """Creates features for rugby match prediction"""

    def __init__(self, k_factor: int = 32):
        self.k_factor = k_factor
        self.team_elo = {}  # Overall ELO
        self.h2h_records = {}  # Head-to-head records
        self.recent_form = {}  # Last 5 matches

    def update_elo(self, winner: str, loser: str, points_diff: int = None):
        """
        Update ELO ratings after a match

        Args:
            winner: Winning team code
            loser: Losing team code
            points_diff: Point differential (affects ELO change)
        """
        if not USE_ELO:
            return

        winner_elo = self.team_elo.get(winner, 1500)
        loser_elo = self.team_elo.get(loser, 1500)

        # Expected scores
        expected_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
        expected_loser = 1 / (1 + 10 ** ((winner_elo - loser_elo) / 400))

        # K-factor adjustment based on point differential
        # Larger wins -> bigger ELO change
        k_adjusted = self.k_factor
        if points_diff:
            if points_diff > 20:
                k_adjusted = self.k_factor * 1.5
            elif points_diff > 40:
                k_adjusted = self.k_factor * 2.0

        # Update ELOs
        self.team_elo[winner] = winner_elo + k_adjusted * (1 - expected_winner)
        self.team_elo[loser] = loser_elo + k_adjusted * (0 - expected_loser)

    def update_h2h(self, team1: str, team2: str, winner: str):
        """Update head-to-head record"""
        if not USE_HEAD_TO_HEAD:
            return

        key = tuple(sorted([team1, team2]))
        if key not in self.h2h_records:
            self.h2h_records[key] = {team1: 0, team2: 0, 'draws': 0}

        if winner == 'draw':
            self.h2h_records[key]['draws'] += 1
        else:
            self.h2h_records[key][winner] += 1

    def update_recent_form(self, team: str, won: bool):
        """Track recent form (last 5 matches)"""
        if team not in self.recent_form:
            self.recent_form[team] = []

        self.recent_form[team].append(1 if won else 0)

        # Keep only last 5 matches
        if len(self.recent_form[team]) > 5:
            self.recent_form[team] = self.recent_form[team][-5:]

    def get_h2h_features(self, team1: str, team2: str) -> Dict[str, float]:
        """Get head-to-head features"""
        key = tuple(sorted([team1, team2]))

        if key not in self.h2h_records:
            return {
                'h2h_team1_wins': 0,
                'h2h_team2_wins': 0,
                'h2h_draws': 0,
                'h2h_total_matches': 0,
                'h2h_team1_win_pct': 0.5,
            }

        team1_wins = self.h2h_records[key].get(team1, 0)
        team2_wins = self.h2h_records[key].get(team2, 0)
        draws = self.h2h_records[key].get('draws', 0)
        total = team1_wins + team2_wins + draws

        return {
            'h2h_team1_wins': team1_wins,
            'h2h_team2_wins': team2_wins,
            'h2h_draws': draws,
            'h2h_total_matches': total,
            'h2h_team1_win_pct': team1_wins / total if total > 0 else 0.333,  # Accounting for draws
        }

    def get_form_features(self, team: str) -> Dict[str, float]:
        """Get recent form features"""
        if team not in self.recent_form or not self.recent_form[team]:
            return {
                'recent_wins': 0,
                'recent_form_pct': 0.5,
                'form_streak': 0,
            }

        recent = self.recent_form[team]
        return {
            'recent_wins': sum(recent),
            'recent_form_pct': sum(recent) / len(recent),
            'form_streak': len([x for x in recent if x == recent[-1]]),  # Current streak
        }

    def calculate_match_features(self, match: pd.Series, is_home: bool = True) -> Dict[str, float]:
        """
        Calculate features for a single match

        Args:
            match: Match data row
            is_home: Whether this is home team perspective

        Returns:
            Dictionary of features
        """
        home_team = match.get('home_team', '')
        away_team = match.get('away_team', '')

        features = {}

        # ELO Features
        if USE_ELO:
            home_elo = self.team_elo.get(home_team, 1500)
            away_elo = self.team_elo.get(away_team, 1500)
            features['home_elo'] = home_elo
            features['away_elo'] = away_elo
            features['elo_diff'] = home_elo - away_elo

        # Home advantage (VERY IMPORTANT in rugby)
        if USE_HOME_ADVANTAGE:
            features['home_advantage'] = HOME_ADVANTAGE_FACTOR
            features['is_home'] = 1.0 if is_home else 0.0

        # Altitude advantage (for teams like South Africa)
        if home_team in ALTITUDE_TEAMS:
            features['altitude_advantage'] = ALTITUDE_BONUS
        else:
            features['altitude_advantage'] = 1.0

        # H2H Features
        if USE_HEAD_TO_HEAD:
            h2h_features = self.get_h2h_features(home_team, away_team)
            features.update(h2h_features)

        # Recent form
        home_form = self.get_form_features(home_team)
        away_form = self.get_form_features(away_team)
        features['home_recent_wins'] = home_form['recent_wins']
        features['away_recent_wins'] = away_form['recent_wins']
        features['home_form_pct'] = home_form['recent_form_pct']
        features['away_form_pct'] = away_form['recent_form_pct']

        # Competition tier
        competition = match.get('competition', '')
        features['is_world_cup'] = 1.0 if 'world cup' in competition.lower() else 0.0
        features['is_six_nations'] = 1.0 if 'six nations' in competition.lower() else 0.0
        features['is_rugby_champ'] = 1.0 if 'championship' in competition.lower() else 0.0

        return features

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer all features for a dataset

        Args:
            df: DataFrame with match data

        Returns:
            DataFrame with engineered features
        """
        log_header("Engineering Rugby Features")

        # Ensure data is sorted by date
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.sort_values('date').reset_index(drop=True)

        feature_rows = []

        with Timer("Processing matches"):
            for idx, match in df.iterrows():
                # Calculate features based on current state
                features = self.calculate_match_features(match, is_home=True)

                # Add match identifiers
                features['match_id'] = idx
                features['date'] = match.get('date', '')
                features['home_team'] = match.get('home_team', '')
                features['away_team'] = match.get('away_team', '')

                # Add target variables (if available)
                if 'home_score' in match and 'away_score' in match:
                    home_score = match['home_score']
                    away_score = match['away_score']

                    # Match winner (0=away, 1=draw, 2=home)
                    if home_score > away_score:
                        features['target_winner'] = 2
                    elif home_score < away_score:
                        features['target_winner'] = 0
                    else:
                        features['target_winner'] = 1  # Draw

                    features['target_total_points'] = home_score + away_score
                    features['target_points_diff'] = home_score - away_score

                    # Update ELO and records after match
                    if home_score > away_score:
                        self.update_elo(match['home_team'], match['away_team'], home_score - away_score)
                        self.update_h2h(match['home_team'], match['away_team'], match['home_team'])
                        self.update_recent_form(match['home_team'], won=True)
                        self.update_recent_form(match['away_team'], won=False)
                    elif away_score > home_score:
                        self.update_elo(match['away_team'], match['home_team'], away_score - home_score)
                        self.update_h2h(match['home_team'], match['away_team'], match['away_team'])
                        self.update_recent_form(match['home_team'], won=False)
                        self.update_recent_form(match['away_team'], won=True)
                    else:  # Draw
                        self.update_h2h(match['home_team'], match['away_team'], 'draw')

                feature_rows.append(features)

                if idx > 0 and idx % 100 == 0:
                    print(f"  Processed {idx:,} matches...")

        features_df = pd.DataFrame(feature_rows)
        print(f"\n✅ Generated {len(features_df)} feature rows with {len(features_df.columns)} columns")

        return features_df


def main():
    """Test feature engineering"""
    from pathlib import Path

    # Find historical data files
    raw_files = list(Path("data/raw").glob("rugby_*.csv"))

    if not raw_files:
        print("⚠️  No rugby data files found. Run download_rugby_data.py first.")
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
    engineer = RugbyFeatureEngineer()
    features_df = engineer.engineer_features(combined_df)

    # Save features
    from config import FEATURES_PARQUET
    features_df.to_parquet(FEATURES_PARQUET, index=False)
    print(f"\n✅ Features saved to: {FEATURES_PARQUET}")


if __name__ == "__main__":
    main()

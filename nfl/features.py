#!/usr/bin/env python3
"""
NFL Feature Engineering

Creates predictive features for NFL games including:
- Team offensive/defensive stats (passing, rushing, total yards)
- Recent form (rolling averages over last N games)
- Head-to-head history
- Situational factors (home/away, divisional games, rest days)
- Advanced metrics (yards per play, turnover differential, 3rd down %)
- ELO ratings
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from config import USE_ELO, USE_ROLLING_FORM, DIVISIONS, CONFERENCES


class NFLFeatureEngineer:
    """Create features for NFL game prediction"""

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with historical game data

        Args:
            df: DataFrame with columns like season, week, home_team, away_team,
                home_score, away_score, and stat columns
        """
        self.df = df.copy()
        self.elo_ratings = {}  # Team ELO ratings
        self.initialize_elo()

    def initialize_elo(self, base_rating: float = 1500.0):
        """Initialize ELO ratings for all teams"""
        from config import NFL_TEAMS

        for team_abbr in NFL_TEAMS.keys():
            self.elo_ratings[team_abbr] = base_rating

    def calculate_elo_change(self, winner_elo: float, loser_elo: float,
                            margin: int, k: float = 20.0) -> tuple[float, float]:
        """
        Calculate ELO rating changes after a game

        Args:
            winner_elo: Winner's current ELO
            loser_elo: Loser's current ELO
            margin: Point differential
            k: K-factor (sensitivity to upsets)

        Returns:
            (new_winner_elo, new_loser_elo)
        """
        # Expected score
        expected_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))

        # Margin multiplier (bigger wins = bigger rating changes)
        margin_mult = np.log(max(margin, 1) + 1) * 2.2

        # Calculate change
        change = k * margin_mult * (1 - expected_winner)

        return (winner_elo + change, loser_elo - change)

    def update_elo_ratings(self):
        """Update ELO ratings based on all historical games"""
        # Sort by season and week
        df_sorted = self.df.sort_values(['season', 'week']).copy()

        elo_history = []

        for idx, row in df_sorted.iterrows():
            if pd.isna(row['home_score']) or pd.isna(row['away_score']):
                continue

            home_team = row['home_team']
            away_team = row['away_team']
            home_score = int(row['home_score'])
            away_score = int(row['away_score'])

            # Get current ELOs
            home_elo = self.elo_ratings.get(home_team, 1500)
            away_elo = self.elo_ratings.get(away_team, 1500)

            # Record before update
            elo_history.append({
                'season': row['season'],
                'week': row['week'],
                'home_team': home_team,
                'away_team': away_team,
                'home_elo_before': home_elo,
                'away_elo_before': away_elo,
            })

            # Update based on result
            if home_score > away_score:
                margin = home_score - away_score
                new_home, new_away = self.calculate_elo_change(home_elo, away_elo, margin)
            elif away_score > home_score:
                margin = away_score - home_score
                new_away, new_home = self.calculate_elo_change(away_elo, home_elo, margin)
            else:
                # Tie (rare in NFL due to OT)
                new_home = home_elo
                new_away = away_elo

            self.elo_ratings[home_team] = new_home
            self.elo_ratings[away_team] = new_away

        return pd.DataFrame(elo_history)

    def get_team_rolling_stats(self, team: str, games: pd.DataFrame,
                               n_games: int = 5) -> Dict[str, float]:
        """
        Calculate rolling averages for a team's recent games

        Args:
            team: Team abbreviation
            games: DataFrame of games (must be sorted by date)
            n_games: Number of recent games to average

        Returns:
            Dict of stat_name -> value
        """
        # Get team's recent games (as home or away)
        team_games = games[
            (games['home_team'] == team) | (games['away_team'] == team)
        ].tail(n_games)

        if len(team_games) == 0:
            return {}

        stats = {}

        # Points scored/allowed
        points_for = []
        points_against = []

        for _, game in team_games.iterrows():
            if game['home_team'] == team:
                points_for.append(game.get('home_score', 0))
                points_against.append(game.get('away_score', 0))
            else:
                points_for.append(game.get('away_score', 0))
                points_against.append(game.get('home_score', 0))

        stats['avg_points_for'] = np.mean(points_for)
        stats['avg_points_against'] = np.mean(points_against)
        stats['avg_point_diff'] = stats['avg_points_for'] - stats['avg_points_against']

        # Win percentage
        wins = sum(1 for pf, pa in zip(points_for, points_against) if pf > pa)
        stats['win_pct'] = wins / len(team_games)

        # Additional stats if available
        stat_columns = [
            'total_yards', 'passing_yards', 'rushing_yards',
            'turnovers', 'first_downs', 'third_down_pct',
            'red_zone_pct', 'time_of_possession'
        ]

        for stat in stat_columns:
            home_col = f'home_{stat}'
            away_col = f'away_{stat}'

            if home_col in team_games.columns:
                team_stats = []
                for _, game in team_games.iterrows():
                    if game['home_team'] == team:
                        val = game.get(home_col)
                    else:
                        val = game.get(away_col)

                    if pd.notna(val):
                        team_stats.append(float(val))

                if team_stats:
                    stats[f'avg_{stat}'] = np.mean(team_stats)

        return stats

    def create_features(self) -> pd.DataFrame:
        """
        Create full feature set for all games

        Returns:
            DataFrame with features for each game
        """
        features = []

        # Update ELO ratings
        if USE_ELO:
            elo_df = self.update_elo_ratings()
            self.df = self.df.merge(
                elo_df,
                on=['season', 'week', 'home_team', 'away_team'],
                how='left'
            )

        # Sort by date for rolling stats
        df_sorted = self.df.sort_values(['season', 'week']).copy()

        for idx, row in df_sorted.iterrows():
            home_team = row['home_team']
            away_team = row['away_team']
            season = row['season']
            week = row['week']

            # Get historical games before this game
            past_games = df_sorted[
                (df_sorted['season'] < season) |
                ((df_sorted['season'] == season) & (df_sorted['week'] < week))
            ]

            game_features = {
                'season': season,
                'week': week,
                'home_team': home_team,
                'away_team': away_team,
            }

            # ELO features
            if USE_ELO:
                game_features['home_elo'] = row.get('home_elo_before', 1500)
                game_features['away_elo'] = row.get('away_elo_before', 1500)
                game_features['elo_diff'] = game_features['home_elo'] - game_features['away_elo']

            # Rolling form features
            if USE_ROLLING_FORM:
                for n in [3, 5, 10]:
                    home_stats = self.get_team_rolling_stats(home_team, past_games, n)
                    away_stats = self.get_team_rolling_stats(away_team, past_games, n)

                    for stat, value in home_stats.items():
                        game_features[f'home_{stat}_L{n}'] = value

                    for stat, value in away_stats.items():
                        game_features[f'away_{stat}_L{n}'] = value

            # Head-to-head history
            h2h = past_games[
                ((past_games['home_team'] == home_team) & (past_games['away_team'] == away_team)) |
                ((past_games['home_team'] == away_team) & (past_games['away_team'] == home_team))
            ]

            if len(h2h) > 0:
                h2h_wins_home = sum(
                    (h2h['home_team'] == home_team) & (h2h['home_score'] > h2h['away_score']) |
                    (h2h['away_team'] == home_team) & (h2h['away_score'] > h2h['home_score'])
                )
                game_features['h2h_win_pct'] = h2h_wins_home / len(h2h)
                game_features['h2h_games'] = len(h2h)
            else:
                game_features['h2h_win_pct'] = 0.5
                game_features['h2h_games'] = 0

            # Division/Conference indicators
            game_features['is_divisional'] = self._is_divisional(home_team, away_team)
            game_features['is_conference'] = self._is_conference(home_team, away_team)

            # Target variables (if game completed)
            if pd.notna(row.get('home_score')) and pd.notna(row.get('away_score')):
                home_score = int(row['home_score'])
                away_score = int(row['away_score'])

                # Result
                if home_score > away_score:
                    game_features['result'] = 'H'  # Home win
                elif away_score > home_score:
                    game_features['result'] = 'A'  # Away win
                else:
                    game_features['result'] = 'T'  # Tie (rare)

                # Scores
                game_features['home_score'] = home_score
                game_features['away_score'] = away_score
                game_features['total_score'] = home_score + away_score

                # Spread (from home perspective)
                game_features['spread_result'] = home_score - away_score

            features.append(game_features)

        return pd.DataFrame(features)

    def _is_divisional(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same division"""
        for division, teams in DIVISIONS.items():
            if team1 in teams and team2 in teams:
                return True
        return False

    def _is_conference(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same conference"""
        for conference, teams in CONFERENCES.items():
            if team1 in teams and team2 in teams:
                return True
        return False


def build_features_from_raw(raw_data_path: str, output_path: str = None):
    """
    Build features from raw game data

    Args:
        raw_data_path: Path to raw CSV with game data
        output_path: Where to save features (default: data/processed/features.parquet)
    """
    from config import PROCESSED_DIR, log_header

    log_header("Building NFL Features")

    # Load raw data
    print(f"📂 Loading data from {raw_data_path}")
    df = pd.read_csv(raw_data_path)

    print(f"  ✅ Loaded {len(df)} games")

    # Create features
    engineer = NFLFeatureEngineer(df)
    features_df = engineer.create_features()

    print(f"  ✅ Created {len(features_df.columns)} features")

    # Save
    if output_path is None:
        output_path = PROCESSED_DIR / "features.parquet"

    features_df.to_parquet(output_path, index=False)
    print(f"✅ Saved features to {output_path}")

    return features_df


if __name__ == "__main__":
    import argparse
    from config import RAW_DIR

    parser = argparse.ArgumentParser(description='Build NFL features')
    parser.add_argument('--input', type=str,
                       help='Input CSV file (default: combined raw data)')
    parser.add_argument('--output', type=str,
                       help='Output parquet file (default: data/processed/features.parquet)')

    args = parser.parse_args()

    # If no input specified, try to find combined data
    if args.input:
        input_file = args.input
    else:
        # Look for combined CSV in raw directory
        input_file = RAW_DIR / "combined_games.csv"

        if not input_file.exists():
            print("⚠️  No combined data found. Run data_ingest.py first.")
            exit(1)

    build_features_from_raw(str(input_file), args.output)

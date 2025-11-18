#!/usr/bin/env python3
"""
MLB Historical Data Downloader

Downloads historical MLB game data from:
1. MLB Stats API (official, free)
2. Baseball Reference (scraping fallback)
3. Statcast for advanced metrics

Saves data to data/raw/ directory for processing.
"""

from pathlib import Path
import requests
import json
import pandas as pd
from typing import List, Dict, Any
import time
from datetime import datetime, timedelta
from config import (
    DATA_DIR, RAW_DIR, SEASONS, MLB_STATS_API_BASE,
    BASEBALL_REF_BASE, log_header
)
from progress_utils import Timer, heartbeat

class MLBDataDownloader:
    """Downloads historical MLB game data"""

    def __init__(self):
        self.raw_dir = RAW_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download_mlb_stats_api_season(self, year: int) -> pd.DataFrame:
        """
        Download full season data from MLB Stats API

        Args:
            year: Season year (e.g., 2024)

        Returns:
            DataFrame with game data
        """
        heartbeat(f"Downloading {year} season from MLB Stats API")

        all_games = []

        try:
            # Get schedule for the season
            url = f"{MLB_STATS_API_BASE}/schedule"
            params = {
                'sportId': 1,  # MLB
                'season': year,
                'gameType': 'R',  # Regular season
                'hydrate': 'linescore,team'
            }

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()

                if 'dates' in data:
                    for date_entry in data['dates']:
                        for game in date_entry.get('games', []):
                            game_data = self._parse_mlb_api_game(game, year)
                            if game_data:
                                all_games.append(game_data)

                    heartbeat(f"  Found {len(all_games)} games")

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"  ⚠️  Error downloading {year} season: {e}")

        if all_games:
            df = pd.DataFrame(all_games)
            output_file = self.raw_dir / f"mlb_{year}.csv"
            df.to_csv(output_file, index=False)
            print(f"  ✅ Saved {len(all_games)} games to {output_file}")
            return df

        return pd.DataFrame()

    def _parse_mlb_api_game(self, game: Dict[str, Any], year: int) -> Dict[str, Any]:
        """Parse MLB API game data into standardized format"""
        try:
            game_date = game.get('officialDate', '')
            game_pk = game.get('gamePk', '')

            status = game.get('status', {}).get('detailedState', '')
            is_final = status in ['Final', 'Completed']

            teams = game.get('teams', {})
            home_team = teams.get('home', {}).get('team', {}).get('abbreviation', '')
            away_team = teams.get('away', {}).get('team', {}).get('abbreviation', '')

            game_data = {
                'season': year,
                'date': game_date,
                'game_pk': game_pk,
                'home_team': home_team,
                'away_team': away_team,
                'venue': game.get('venue', {}).get('name', ''),
                'completed': is_final,
            }

            # Extract scores if game is complete
            if is_final:
                home_score = teams.get('home', {}).get('score', None)
                away_score = teams.get('away', {}).get('score', None)

                game_data['home_score'] = home_score
                game_data['away_score'] = away_score

                # Extract linescore for first 5 innings
                linescore = game.get('linescore', {})
                if linescore:
                    innings = linescore.get('innings', [])

                    home_first_5 = 0
                    away_first_5 = 0

                    for inning in innings[:5]:  # First 5 innings
                        home_first_5 += inning.get('home', {}).get('runs', 0)
                        away_first_5 += inning.get('away', {}).get('runs', 0)

                    game_data['home_first_5_score'] = home_first_5
                    game_data['away_first_5_score'] = away_first_5

            return game_data

        except Exception as e:
            print(f"  ⚠️  Error parsing game: {e}")
            return None

    def download_all_seasons(self, seasons: List[int] = None):
        """Download data for multiple seasons"""
        if seasons is None:
            seasons = SEASONS

        with Timer(f"Downloading {len(seasons)} MLB seasons"):
            for year in seasons:
                try:
                    self.download_mlb_stats_api_season(year)
                except Exception as e:
                    print(f"⚠️  Failed to download {year} season: {e}")

    def download_baseball_reference(self, year: int):
        """
        Fallback: Scrape data from Baseball-Reference.com

        Note: This requires BeautifulSoup
        """
        heartbeat(f"Downloading {year} from Baseball Reference (fallback)")

        try:
            url = f"{BASEBALL_REF_BASE}/leagues/majors/{year}-schedule.shtml"

            # Use pandas to read HTML tables
            tables = pd.read_html(url)

            if tables:
                df = tables[0]  # First table is usually the games

                # Clean and standardize column names
                df.columns = [col.lower().replace(' ', '_') for col in df.columns]

                # Save raw data
                output_file = self.raw_dir / f"bbref_{year}.csv"
                df.to_csv(output_file, index=False)
                print(f"  ✅ Saved Baseball Reference data to {output_file}")
                return df

        except Exception as e:
            print(f"  ⚠️  Error scraping Baseball Reference: {e}")
            return None


def main():
    """Main download function"""
    import argparse

    parser = argparse.ArgumentParser(description='Download MLB historical data')
    parser.add_argument('--start', type=int, default=2018,
                       help='Start season year (default: 2018)')
    parser.add_argument('--end', type=int, default=datetime.now().year,
                       help='End season year (default: current year)')
    parser.add_argument('--source', choices=['mlb', 'bbref', 'both'],
                       default='mlb', help='Data source')

    args = parser.parse_args()

    seasons = list(range(args.start, args.end + 1))

    log_header(f"MLB Data Download: {seasons[0]}-{seasons[-1]}")

    downloader = MLBDataDownloader()

    if args.source in ['mlb', 'both']:
        downloader.download_all_seasons(seasons)

    if args.source in ['bbref', 'both']:
        for year in seasons:
            downloader.download_baseball_reference(year)

    print("\n✅ Download complete!")
    print(f"📁 Data saved to: {RAW_DIR}")


if __name__ == "__main__":
    main()

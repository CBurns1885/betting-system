#!/usr/bin/env python3
"""
NFL Historical Data Downloader

Downloads historical NFL game data from multiple sources:
1. ESPN API (primary, free)
2. Pro Football Reference (scraping fallback)
3. CSV exports (manual backup)

Saves data to data/raw/ directory for processing.
"""

from pathlib import Path
import requests
import json
import pandas as pd
from typing import List, Dict, Any
import time
from datetime import datetime, timedelta
from config import DATA_DIR, RAW_DIR, SEASONS, ESPN_API_BASE, log_header
from progress_utils import Timer, heartbeat

class NFLDataDownloader:
    """Downloads historical NFL game data"""

    def __init__(self):
        self.raw_dir = RAW_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download_espn_season(self, year: int) -> pd.DataFrame:
        """
        Download full season data from ESPN API

        Args:
            year: Season year (e.g., 2024 for 2024-25 season)

        Returns:
            DataFrame with game data
        """
        heartbeat(f"Downloading {year} season from ESPN API")

        all_games = []

        # NFL regular season: weeks 1-18
        # Playoffs: weeks 19-22 (Wild Card, Divisional, Conference, Super Bowl)
        for week in range(1, 23):
            try:
                url = f"{ESPN_API_BASE}/scoreboard"
                params = {
                    'dates': year,
                    'seasontype': 2 if week <= 18 else 3,  # 2=regular, 3=postseason
                    'week': week if week <= 18 else week - 18
                }

                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()

                    if 'events' in data:
                        for event in data['events']:
                            game = self._parse_espn_game(event, year, week)
                            if game:
                                all_games.append(game)

                        heartbeat(f"  Week {week}: {len(data['events'])} games")

                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                print(f"  ⚠️  Error downloading week {week}: {e}")
                continue

        if all_games:
            df = pd.DataFrame(all_games)
            output_file = self.raw_dir / f"nfl_{year}.csv"
            df.to_csv(output_file, index=False)
            print(f"  ✅ Saved {len(all_games)} games to {output_file}")
            return df

        return pd.DataFrame()

    def _parse_espn_game(self, event: Dict[str, Any], year: int, week: int) -> Dict[str, Any]:
        """Parse ESPN API game data into standardized format"""
        try:
            competitions = event.get('competitions', [])
            if not competitions:
                return None

            comp = competitions[0]
            competitors = comp.get('competitors', [])

            if len(competitors) != 2:
                return None

            # Determine home/away
            home = next((t for t in competitors if t.get('homeAway') == 'home'), None)
            away = next((t for t in competitors if t.get('homeAway') == 'away'), None)

            if not home or not away:
                return None

            # Extract game info
            game_date = event.get('date', '')
            status = event.get('status', {}).get('type', {}).get('completed', False)

            game_data = {
                'season': year,
                'week': week,
                'date': game_date,
                'home_team': home.get('team', {}).get('abbreviation', ''),
                'away_team': away.get('team', {}).get('abbreviation', ''),
                'home_score': int(home.get('score', 0)) if status else None,
                'away_score': int(away.get('score', 0)) if status else None,
                'completed': status,
            }

            # Extract detailed stats if available
            if status:
                home_stats = home.get('statistics', [])
                away_stats = away.get('statistics', [])

                # Parse common stats
                for stat in home_stats:
                    name = stat.get('name', '').lower().replace(' ', '_')
                    game_data[f'home_{name}'] = stat.get('displayValue')

                for stat in away_stats:
                    name = stat.get('name', '').lower().replace(' ', '_')
                    game_data[f'away_{name}'] = stat.get('displayValue')

            return game_data

        except Exception as e:
            print(f"  ⚠️  Error parsing game: {e}")
            return None

    def download_all_seasons(self, seasons: List[int] = None):
        """Download data for multiple seasons"""
        if seasons is None:
            seasons = SEASONS

        with Timer(f"Downloading {len(seasons)} NFL seasons"):
            for year in seasons:
                try:
                    self.download_espn_season(year)
                except Exception as e:
                    print(f"⚠️  Failed to download {year} season: {e}")

    def download_pro_football_reference(self, year: int):
        """
        Fallback: Scrape data from Pro-Football-Reference.com

        Note: This requires BeautifulSoup and should respect robots.txt
        """
        heartbeat(f"Downloading {year} from Pro Football Reference (fallback)")

        try:
            # Pro Football Reference URL pattern
            url = f"https://www.pro-football-reference.com/years/{year}/games.htm"

            # Use pandas to read HTML tables
            tables = pd.read_html(url)

            if tables:
                df = tables[0]  # First table is usually the games

                # Clean and standardize column names
                df.columns = [col.lower().replace(' ', '_') for col in df.columns]

                # Save raw data
                output_file = self.raw_dir / f"pfr_{year}.csv"
                df.to_csv(output_file, index=False)
                print(f"  ✅ Saved PFR data to {output_file}")
                return df

        except Exception as e:
            print(f"  ⚠️  Error scraping PFR: {e}")
            return None

    def combine_sources(self, year: int) -> pd.DataFrame:
        """Combine data from multiple sources for a single season"""
        dfs = []

        # Try ESPN first
        espn_file = self.raw_dir / f"nfl_{year}.csv"
        if espn_file.exists():
            dfs.append(pd.read_csv(espn_file))

        # Try PFR fallback
        pfr_file = self.raw_dir / f"pfr_{year}.csv"
        if pfr_file.exists():
            dfs.append(pd.read_csv(pfr_file))

        if dfs:
            # Merge and deduplicate
            combined = pd.concat(dfs, ignore_index=True)
            combined = combined.drop_duplicates(
                subset=['season', 'week', 'home_team', 'away_team'],
                keep='first'
            )
            return combined

        return pd.DataFrame()


def main():
    """Main download function"""
    import argparse

    parser = argparse.ArgumentParser(description='Download NFL historical data')
    parser.add_argument('--start', type=int, default=2018,
                       help='Start season year (default: 2018)')
    parser.add_argument('--end', type=int, default=datetime.now().year,
                       help='End season year (default: current year)')
    parser.add_argument('--source', choices=['espn', 'pfr', 'both'],
                       default='espn', help='Data source')

    args = parser.parse_args()

    seasons = list(range(args.start, args.end + 1))

    log_header(f"NFL Data Download: {seasons[0]}-{seasons[-1]}")

    downloader = NFLDataDownloader()

    if args.source in ['espn', 'both']:
        downloader.download_all_seasons(seasons)

    if args.source in ['pfr', 'both']:
        for year in seasons:
            downloader.download_pro_football_reference(year)

    print("\n✅ Download complete!")
    print(f"📁 Data saved to: {RAW_DIR}")


if __name__ == "__main__":
    main()

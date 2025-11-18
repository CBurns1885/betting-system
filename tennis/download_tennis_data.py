#!/usr/bin/env python3
"""
Tennis Historical Data Downloader

Downloads historical tennis match data from:
1. Tennis Abstract (free, comprehensive)
2. ATP/WTA official APIs (if available)
3. Ultimate Tennis Statistics (scraping fallback)

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
    DATA_DIR, RAW_DIR, SEASONS, TOURS, SURFACES,
    TENNIS_ABSTRACT_BASE, ATP_API_BASE, WTA_API_BASE,
    log_header
)
from progress_utils import Timer, heartbeat

class TennisDataDownloader:
    """Downloads historical tennis match data"""

    def __init__(self):
        self.raw_dir = RAW_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download_tennis_abstract_season(self, year: int, tour: str = "ATP") -> pd.DataFrame:
        """
        Download full season data from Tennis Abstract

        Args:
            year: Season year (e.g., 2024)
            tour: Tour type ("ATP" or "WTA")

        Returns:
            DataFrame with match data
        """
        heartbeat(f"Downloading {tour} {year} season from Tennis Abstract")

        all_matches = []

        try:
            # Tennis Abstract provides CSV data
            if tour == "ATP":
                url = f"{TENNIS_ABSTRACT_BASE}/charting/meta.csv"
            else:
                url = f"{TENNIS_ABSTRACT_BASE}/charting/wta_meta.csv"

            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                # Parse CSV data
                from io import StringIO
                df = pd.read_csv(StringIO(response.text))

                # Filter by year
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                    df = df[df['Date'].dt.year == year]

                heartbeat(f"  Found {len(df)} matches")

                if len(df) > 0:
                    output_file = self.raw_dir / f"tennis_{tour.lower()}_{year}.csv"
                    df.to_csv(output_file, index=False)
                    print(f"  ✅ Saved {len(df)} matches to {output_file}")
                    return df

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"  ⚠️  Error downloading {tour} {year} season: {e}")

        return pd.DataFrame()

    def download_jeff_sackmann_data(self, year: int, tour: str = "ATP") -> pd.DataFrame:
        """
        Download data from Jeff Sackmann's GitHub (tennis_atp / tennis_wta)
        This is one of the best free tennis data sources

        Args:
            year: Season year
            tour: "ATP" or "WTA"

        Returns:
            DataFrame with match data
        """
        heartbeat(f"Downloading {tour} {year} from Jeff Sackmann GitHub")

        try:
            if tour == "ATP":
                url = f"https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{year}.csv"
            else:
                url = f"https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{year}.csv"

            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                from io import StringIO
                df = pd.read_csv(StringIO(response.text))

                heartbeat(f"  Found {len(df)} matches")

                if len(df) > 0:
                    output_file = self.raw_dir / f"tennis_{tour.lower()}_{year}_sackmann.csv"
                    df.to_csv(output_file, index=False)
                    print(f"  ✅ Saved {len(df)} matches to {output_file}")
                    return df

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"  ⚠️  Error downloading {tour} {year} season: {e}")

        return pd.DataFrame()

    def parse_match_data(self, match: Dict[str, Any], year: int) -> Dict[str, Any]:
        """Parse match data into standardized format"""
        try:
            match_data = {
                'season': year,
                'date': match.get('tourney_date', match.get('Date', '')),
                'tournament': match.get('tourney_name', match.get('Tournament', '')),
                'surface': match.get('surface', match.get('Surface', 'Hard')),
                'draw_size': match.get('draw_size', 0),
                'tourney_level': match.get('tourney_level', ''),
                'match_num': match.get('match_num', 0),

                # Winner info
                'winner_name': match.get('winner_name', ''),
                'winner_id': match.get('winner_id', ''),
                'winner_seed': match.get('winner_seed', None),
                'winner_entry': match.get('winner_entry', ''),
                'winner_rank': match.get('winner_rank', None),
                'winner_rank_points': match.get('winner_rank_points', None),

                # Loser info
                'loser_name': match.get('loser_name', ''),
                'loser_id': match.get('loser_id', ''),
                'loser_seed': match.get('loser_seed', None),
                'loser_entry': match.get('loser_entry', ''),
                'loser_rank': match.get('loser_rank', None),
                'loser_rank_points': match.get('loser_rank_points', None),

                # Match statistics
                'score': match.get('score', ''),
                'best_of': match.get('best_of', 3),
                'round': match.get('round', ''),
                'minutes': match.get('minutes', None),

                # Winner stats
                'w_ace': match.get('w_ace', None),
                'w_df': match.get('w_df', None),
                'w_svpt': match.get('w_svpt', None),
                'w_1stIn': match.get('w_1stIn', None),
                'w_1stWon': match.get('w_1stWon', None),
                'w_2ndWon': match.get('w_2ndWon', None),
                'w_SvGms': match.get('w_SvGms', None),
                'w_bpSaved': match.get('w_bpSaved', None),
                'w_bpFaced': match.get('w_bpFaced', None),

                # Loser stats
                'l_ace': match.get('l_ace', None),
                'l_df': match.get('l_df', None),
                'l_svpt': match.get('l_svpt', None),
                'l_1stIn': match.get('l_1stIn', None),
                'l_1stWon': match.get('l_1stWon', None),
                'l_2ndWon': match.get('l_2ndWon', None),
                'l_SvGms': match.get('l_SvGms', None),
                'l_bpSaved': match.get('l_bpSaved', None),
                'l_bpFaced': match.get('l_bpFaced', None),
            }

            return match_data

        except Exception as e:
            print(f"  ⚠️  Error parsing match: {e}")
            return None

    def download_all_seasons(self, seasons: List[int] = None, tours: List[str] = None):
        """Download data for multiple seasons and tours"""
        if seasons is None:
            seasons = SEASONS

        if tours is None:
            tours = ["ATP", "WTA"]

        with Timer(f"Downloading {len(seasons)} seasons for {len(tours)} tours"):
            for tour in tours:
                for year in seasons:
                    try:
                        # Try Jeff Sackmann data first (most reliable)
                        self.download_jeff_sackmann_data(year, tour)
                    except Exception as e:
                        print(f"⚠️  Failed to download {tour} {year} season: {e}")


def main():
    """Main download function"""
    import argparse

    parser = argparse.ArgumentParser(description='Download tennis historical data')
    parser.add_argument('--start', type=int, default=2018,
                       help='Start season year (default: 2018)')
    parser.add_argument('--end', type=int, default=datetime.now().year,
                       help='End season year (default: current year)')
    parser.add_argument('--tour', choices=['ATP', 'WTA', 'both'],
                       default='both', help='Tour type')

    args = parser.parse_args()

    seasons = list(range(args.start, args.end + 1))
    tours = ['ATP', 'WTA'] if args.tour == 'both' else [args.tour.upper()]

    log_header(f"Tennis Data Download: {seasons[0]}-{seasons[-1]}")

    downloader = TennisDataDownloader()
    downloader.download_all_seasons(seasons, tours)

    print("\n✅ Download complete!")
    print(f"📁 Data saved to: {RAW_DIR}")


if __name__ == "__main__":
    main()

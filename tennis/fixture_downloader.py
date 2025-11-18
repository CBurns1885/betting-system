#!/usr/bin/env python3
"""
Tennis Fixture Downloader

Downloads upcoming tennis matches from various sources.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
from config import RAW_DIR, ATP_API_BASE, WTA_API_BASE, ODDS_API_BASE, log_header
from progress_utils import heartbeat

class TennisFixtureDownloader:
    """Downloads upcoming tennis match fixtures"""

    def __init__(self):
        self.raw_dir = RAW_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download_upcoming_from_sackmann(self) -> pd.DataFrame:
        """
        Download current week's matches from Jeff Sackmann's data

        Note: This is updated weekly, so it might not have all upcoming matches
        """
        heartbeat("Downloading current matches from Sackmann data")

        all_matches = []

        try:
            # Get current year ATP and WTA matches
            current_year = datetime.now().year

            for tour in ['ATP', 'WTA']:
                if tour == "ATP":
                    url = f"https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{current_year}.csv"
                else:
                    url = f"https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{current_year}.csv"

                response = self.session.get(url, timeout=30)

                if response.status_code == 200:
                    from io import StringIO
                    df = pd.read_csv(StringIO(response.text))

                    # Get matches from the last 7 days and next 7 days
                    if 'tourney_date' in df.columns:
                        df['tourney_date'] = pd.to_datetime(df['tourney_date'], format='%Y%m%d', errors='coerce')
                        today = pd.Timestamp.now()
                        week_ago = today - pd.Timedelta(days=7)
                        week_ahead = today + pd.Timedelta(days=7)

                        recent_matches = df[
                            (df['tourney_date'] >= week_ago) &
                            (df['tourney_date'] <= week_ahead)
                        ].copy()

                        recent_matches['tour'] = tour
                        all_matches.append(recent_matches)

                        heartbeat(f"  Found {len(recent_matches)} {tour} matches")

        except Exception as e:
            print(f"  ⚠️  Error downloading upcoming matches: {e}")

        if all_matches:
            combined_df = pd.concat(all_matches, ignore_index=True)
            output_file = self.raw_dir / "upcoming_tennis_matches.csv"
            combined_df.to_csv(output_file, index=False)
            print(f"  ✅ Saved {len(combined_df)} upcoming matches to {output_file}")
            return combined_df

        return pd.DataFrame()

    def download_from_odds_api(self, api_key: str = None, days: int = 7) -> pd.DataFrame:
        """
        Download upcoming matches from The Odds API

        Args:
            api_key: The Odds API key (optional)
            days: Number of days ahead to fetch

        Returns:
            DataFrame with upcoming matches and odds
        """
        if not api_key:
            print("  ⚠️  No Odds API key provided, skipping odds download")
            return pd.DataFrame()

        heartbeat(f"Downloading upcoming matches from The Odds API ({days} days)")

        all_matches = []

        try:
            # ATP Tour
            url = f"{ODDS_API_BASE}/odds"
            params = {
                'apiKey': api_key,
                'regions': 'us,uk,eu',
                'markets': 'h2h,spreads,totals',
                'oddsFormat': 'decimal'
            }

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()

                for match in data:
                    match_data = {
                        'date': match.get('commence_time', ''),
                        'player1': match.get('home_team', ''),
                        'player2': match.get('away_team', ''),
                        'bookmakers': len(match.get('bookmakers', [])),
                    }

                    # Extract best odds
                    bookmakers = match.get('bookmakers', [])
                    if bookmakers:
                        for bookmaker in bookmakers:
                            markets = bookmaker.get('markets', [])
                            for market in markets:
                                if market.get('key') == 'h2h':
                                    outcomes = market.get('outcomes', [])
                                    if len(outcomes) >= 2:
                                        match_data['player1_odds'] = outcomes[0].get('price', None)
                                        match_data['player2_odds'] = outcomes[1].get('price', None)
                                    break
                            break

                    all_matches.append(match_data)

                heartbeat(f"  Found {len(all_matches)} matches with odds")

        except Exception as e:
            print(f"  ⚠️  Error downloading from Odds API: {e}")

        if all_matches:
            df = pd.DataFrame(all_matches)
            output_file = self.raw_dir / "upcoming_tennis_odds.csv"
            df.to_csv(output_file, index=False)
            print(f"  ✅ Saved {len(all_matches)} matches with odds to {output_file}")
            return df

        return pd.DataFrame()

    def download_all_upcoming(self, odds_api_key: str = None):
        """Download all upcoming matches"""
        log_header("Downloading Tennis Upcoming Matches")

        # Download from free sources
        sackmann_df = self.download_upcoming_from_sackmann()

        # Download odds if API key provided
        if odds_api_key:
            odds_df = self.download_from_odds_api(odds_api_key)

        print("\n✅ Fixture download complete!")
        print(f"📁 Saved to: {self.raw_dir}")


def main():
    """Main fixture download function"""
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Download upcoming tennis matches')
    parser.add_argument('--odds-api-key', type=str,
                       default=os.environ.get('THE_ODDS_API_KEY'),
                       help='The Odds API key for betting lines')

    args = parser.parse_args()

    downloader = TennisFixtureDownloader()
    downloader.download_all_upcoming(args.odds_api_key)


if __name__ == "__main__":
    main()

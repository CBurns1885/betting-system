#!/usr/bin/env python3
"""
NFL Upcoming Fixtures Downloader

Downloads upcoming NFL games with betting odds for the current week.
Uses ESPN API for fixtures and The Odds API for betting lines.
"""

import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from config import (
    BASE_DIR, ESPN_API_BASE, ODDS_API_BASE, THE_ODDS_API_KEY,
    NFL_TEAMS, log_header
)
from progress_utils import Timer, heartbeat

class NFLFixtureDownloader:
    """Downloads upcoming NFL fixtures with odds"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_current_week(self) -> tuple[int, int]:
        """
        Determine current NFL season and week

        Returns:
            (season_year, week_number)
        """
        now = datetime.now()
        year = now.year
        month = now.month

        # NFL season runs Sept (9) to Feb (2)
        if month >= 9:
            season = year
        elif month <= 2:
            season = year - 1
        else:
            # Offseason
            return (year, 0)

        # Rough week calculation (NFL starts around Sept 7)
        # Week 1 typically starts first Thursday after Labor Day
        season_start = datetime(season, 9, 7)
        days_since_start = (now - season_start).days

        if days_since_start < 0:
            week = 0  # Season hasn't started
        else:
            week = min(days_since_start // 7 + 1, 18)

        return (season, week)

    def download_espn_upcoming(self) -> pd.DataFrame:
        """Download upcoming games from ESPN API"""

        season, current_week = self.get_current_week()

        if current_week == 0:
            print("⚠️  NFL offseason - no upcoming games")
            return pd.DataFrame()

        heartbeat(f"Downloading Week {current_week} fixtures from ESPN")

        fixtures = []

        try:
            # Get current week
            url = f"{ESPN_API_BASE}/scoreboard"

            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()

                if 'events' in data:
                    for event in data['events']:
                        fixture = self._parse_espn_fixture(event)
                        if fixture:
                            fixtures.append(fixture)

                    print(f"  ✅ Found {len(fixtures)} upcoming games")

        except Exception as e:
            print(f"  ⚠️  Error downloading from ESPN: {e}")

        if fixtures:
            return pd.DataFrame(fixtures)

        return pd.DataFrame()

    def _parse_espn_fixture(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ESPN fixture into standardized format"""
        try:
            competitions = event.get('competitions', [])
            if not competitions:
                return None

            comp = competitions[0]
            competitors = comp.get('competitors', [])

            if len(competitors) != 2:
                return None

            home = next((t for t in competitors if t.get('homeAway') == 'home'), None)
            away = next((t for t in competitors if t.get('homeAway') == 'away'), None)

            if not home or not away:
                return None

            # Get game info
            game_id = event.get('id', '')
            game_date = event.get('date', '')
            venue = comp.get('venue', {}).get('fullName', '')
            broadcast = ', '.join([b.get('names', [''])[0] for b in comp.get('broadcasts', [])])

            # Parse date
            if game_date:
                dt = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d')
                time_str = dt.strftime('%H:%M')
            else:
                date_str = ''
                time_str = ''

            fixture = {
                'game_id': game_id,
                'date': date_str,
                'time': time_str,
                'home_team': home.get('team', {}).get('abbreviation', ''),
                'away_team': away.get('team', {}).get('abbreviation', ''),
                'home_team_full': home.get('team', {}).get('displayName', ''),
                'away_team_full': away.get('team', {}).get('displayName', ''),
                'venue': venue,
                'broadcast': broadcast,
                'home_record': home.get('records', [{}])[0].get('summary', '') if home.get('records') else '',
                'away_record': away.get('records', [{}])[0].get('summary', '') if away.get('records') else '',
            }

            # Get odds if available
            if 'odds' in comp and comp['odds']:
                odds = comp['odds'][0]
                fixture['spread'] = odds.get('details', '')
                fixture['over_under'] = odds.get('overUnder', '')

            return fixture

        except Exception as e:
            print(f"  ⚠️  Error parsing fixture: {e}")
            return None

    def download_odds_api(self) -> pd.DataFrame:
        """Download betting odds from The Odds API"""

        if not THE_ODDS_API_KEY:
            print("⚠️  THE_ODDS_API_KEY not set - skipping odds download")
            return pd.DataFrame()

        heartbeat("Downloading betting odds from The Odds API")

        try:
            url = f"{ODDS_API_BASE}/odds"
            params = {
                'apiKey': THE_ODDS_API_KEY,
                'regions': 'us',
                'markets': 'h2h,spreads,totals',
                'oddsFormat': 'american',
            }

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                odds_data = []

                for game in data:
                    game_odds = self._parse_odds_api_game(game)
                    if game_odds:
                        odds_data.append(game_odds)

                print(f"  ✅ Retrieved odds for {len(odds_data)} games")
                return pd.DataFrame(odds_data)

            else:
                print(f"  ⚠️  Odds API returned status {response.status_code}")

        except Exception as e:
            print(f"  ⚠️  Error downloading odds: {e}")

        return pd.DataFrame()

    def _parse_odds_api_game(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """Parse odds from The Odds API"""
        try:
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')

            # Convert team names to abbreviations (simple mapping)
            home_abbr = self._team_name_to_abbr(home_team)
            away_abbr = self._team_name_to_abbr(away_team)

            odds_data = {
                'game_id': game.get('id', ''),
                'home_team': home_abbr,
                'away_team': away_abbr,
                'commence_time': game.get('commence_time', ''),
            }

            # Parse bookmaker odds (average across books)
            bookmakers = game.get('bookmakers', [])

            if bookmakers:
                # Get consensus odds
                moneyline_home = []
                moneyline_away = []
                spread_home = []
                spread_points = []
                totals_over = []
                totals_points = []

                for book in bookmakers:
                    for market in book.get('markets', []):
                        market_key = market.get('key', '')

                        if market_key == 'h2h':  # Moneyline
                            for outcome in market.get('outcomes', []):
                                if outcome.get('name') == home_team:
                                    moneyline_home.append(outcome.get('price'))
                                elif outcome.get('name') == away_team:
                                    moneyline_away.append(outcome.get('price'))

                        elif market_key == 'spreads':  # Spread
                            for outcome in market.get('outcomes', []):
                                if outcome.get('name') == home_team:
                                    spread_home.append(outcome.get('price'))
                                    spread_points.append(outcome.get('point'))

                        elif market_key == 'totals':  # Over/Under
                            for outcome in market.get('outcomes', []):
                                if outcome.get('name') == 'Over':
                                    totals_over.append(outcome.get('price'))
                                    totals_points.append(outcome.get('point'))

                # Calculate averages
                if moneyline_home:
                    odds_data['moneyline_home'] = sum(moneyline_home) / len(moneyline_home)
                if moneyline_away:
                    odds_data['moneyline_away'] = sum(moneyline_away) / len(moneyline_away)
                if spread_points:
                    odds_data['spread'] = sum(spread_points) / len(spread_points)
                if spread_home:
                    odds_data['spread_odds_home'] = sum(spread_home) / len(spread_home)
                if totals_points:
                    odds_data['total'] = sum(totals_points) / len(totals_points)
                if totals_over:
                    odds_data['total_odds_over'] = sum(totals_over) / len(totals_over)

            return odds_data

        except Exception as e:
            print(f"  ⚠️  Error parsing odds: {e}")
            return None

    def _team_name_to_abbr(self, full_name: str) -> str:
        """Convert full team name to abbreviation"""
        # Simple reverse lookup
        for abbr, name in NFL_TEAMS.items():
            if name in full_name or full_name in name:
                return abbr

        # Fallback: use last word as abbreviation
        words = full_name.split()
        return words[-1][:3].upper() if words else full_name

    def download_and_save(self, output_file: str = None):
        """Download fixtures and odds, combine and save"""

        with Timer("Downloading NFL fixtures and odds"):
            # Get fixtures from ESPN
            fixtures_df = self.download_espn_upcoming()

            if fixtures_df.empty:
                print("⚠️  No fixtures found")
                return

            # Get odds from The Odds API
            odds_df = self.download_odds_api()

            # Merge if we have both
            if not odds_df.empty:
                # Merge on team matchup
                combined = fixtures_df.merge(
                    odds_df,
                    on=['home_team', 'away_team'],
                    how='left',
                    suffixes=('', '_odds')
                )
            else:
                combined = fixtures_df

            # Save to files
            if output_file is None:
                output_file = BASE_DIR / "upcoming_fixtures"

            # Save as CSV
            csv_file = f"{output_file}.csv"
            combined.to_csv(csv_file, index=False)
            print(f"\n✅ Saved {len(combined)} fixtures to {csv_file}")

            # Save as Excel
            try:
                xlsx_file = f"{output_file}.xlsx"
                combined.to_excel(xlsx_file, index=False)
                print(f"✅ Saved to {xlsx_file}")
            except ImportError:
                print("⚠️  openpyxl not installed - skipping Excel export")

            return combined


def main():
    """Main function"""
    log_header("NFL Upcoming Fixtures Download")

    downloader = NFLFixtureDownloader()
    downloader.download_and_save()


if __name__ == "__main__":
    main()

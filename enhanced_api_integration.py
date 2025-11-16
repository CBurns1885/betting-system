#!/usr/bin/env python3
"""
enhanced_api_integration.py
Complete API-Football integration for the football prediction system
Enhances the existing pipeline with professional data sources
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import requests
import pandas as pd
import numpy as np

# ============================================================================
# CONFIGURATION
# ============================================================================

# API Configuration - Set your key here or use environment variable
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "YOUR_API_KEY_HERE")
BASE_URL = "https://v3.football.api-sports.io"

# League Mapping - Map football-data.co.uk codes to API-Football IDs
LEAGUE_MAPPING = {
    "E0": 39,   # Premier League
    "E1": 40,   # Championship
    "E2": 41,   # League One
    "E3": 42,   # League Two
    "EC": 48,   # National League
    "SP1": 140, # La Liga
    "SP2": 141, # Segunda Division
    "D1": 78,   # Bundesliga
    "D2": 79,   # 2. Bundesliga
    "I1": 135,  # Serie A
    "I2": 136,  # Serie B
    "F1": 61,   # Ligue 1
    "F2": 62,   # Ligue 2
    "N1": 88,   # Eredivisie
    "B1": 144,  # Jupiler Pro League
    "P1": 94,   # Primeira Liga
    "T1": 203,  # Super Lig
    "SC0": 179, # Scottish Premiership
}

# Additional high-value leagues to include
EXTRA_LEAGUES = {
    2: "UEFA Champions League",
    3: "UEFA Europa League",
    848: "UEFA Europa Conference League",
    4: "Euro Championship",
    1: "World Cup",
}

# ============================================================================
# API CLIENT
# ============================================================================

class APIFootballClient:
    """Enhanced API-Football client with caching and rate limiting"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": api_key})
        self.cache_dir = Path("cache/api_football")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.request_count = 0
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Implement rate limiting to avoid hitting API limits"""
        time_since_last = time.time() - self.last_request_time
        if time_since_last < 0.5:  # Max 2 requests per second
            time.sleep(0.5 - time_since_last)
        self.last_request_time = time.time()
        
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Make API request with error handling and caching"""
        self._rate_limit()
        
        # Check cache first
        cache_key = f"{endpoint}_{json.dumps(params, sort_keys=True)}.json"
        cache_path = self.cache_dir / cache_key.replace("/", "_")
        
        if cache_path.exists():
            cache_age = time.time() - cache_path.stat().st_mtime
            if cache_age < 3600:  # Cache for 1 hour
                with open(cache_path, 'r') as f:
                    return json.load(f)
        
        # Make request
        url = f"{BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if data.get("errors"):
                print(f"API Error: {data['errors']}")
                return {"response": []}
            
            # Cache successful response
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            
            self.request_count += 1
            return data
            
        except Exception as e:
            print(f"Request failed: {e}")
            return {"response": []}
    
    def get_fixtures(self, date: str, league_id: Optional[int] = None) -> List[Dict]:
        """Get fixtures for a specific date"""
        params = {"date": date, "timezone": "UTC"}
        if league_id:
            params["league"] = league_id
        
        data = self._make_request("/fixtures", params)
        return data.get("response", [])
    
    def get_team_statistics(self, team_id: int, league_id: int, season: int) -> Dict:
        """Get detailed team statistics"""
        params = {"team": team_id, "league": league_id, "season": season}
        data = self._make_request("/teams/statistics", params)
        response = data.get("response", {})
        return response if response else {}
    
    def get_h2h(self, team1_id: int, team2_id: int, last: int = 10) -> List[Dict]:
        """Get head-to-head history between two teams"""
        params = {"h2h": f"{team1_id}-{team2_id}", "last": last}
        data = self._make_request("/fixtures/headtohead", params)
        return data.get("response", [])
    
    def get_team_form(self, team_id: int, last: int = 5) -> str:
        """Get team's recent form (W/D/L string)"""
        params = {"team": team_id, "last": last}
        data = self._make_request("/fixtures", params)
        
        form = []
        for fixture in data.get("response", [])[:last]:
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            
            if teams.get("home", {}).get("id") == team_id:
                home_goals = goals.get("home", 0)
                away_goals = goals.get("away", 0)
                if home_goals > away_goals:
                    form.append("W")
                elif home_goals < away_goals:
                    form.append("L")
                else:
                    form.append("D")
            else:
                home_goals = goals.get("home", 0)
                away_goals = goals.get("away", 0)
                if away_goals > home_goals:
                    form.append("W")
                elif away_goals < home_goals:
                    form.append("L")
                else:
                    form.append("D")
        
        return "".join(form)
    
    def get_injuries(self, team_id: int) -> List[Dict]:
        """Get current injuries for a team"""
        params = {"team": team_id}
        data = self._make_request("/injuries", params)
        return data.get("response", [])
    
    def get_predictions(self, fixture_id: int) -> Dict:
        """Get predictions for a specific fixture"""
        params = {"fixture": fixture_id}
        data = self._make_request("/predictions", params)
        response = data.get("response", [])
        return response[0] if response else {}

# ============================================================================
# FIXTURE ENHANCEMENT
# ============================================================================

def enhance_fixtures_with_api_data(fixtures_df: pd.DataFrame, api_client: APIFootballClient) -> pd.DataFrame:
    """
    Enhance fixture data with API-Football statistics
    
    Args:
        fixtures_df: DataFrame with columns [Date, League, HomeTeam, AwayTeam]
        api_client: Initialized API-Football client
    
    Returns:
        Enhanced DataFrame with additional features
    """
    enhanced_features = []
    
    print("Enhancing fixtures with API data...")
    for idx, row in fixtures_df.iterrows():
        if idx % 10 == 0:
            print(f"  Processing fixture {idx+1}/{len(fixtures_df)}")
        
        # Get league ID
        league_code = row['League']
        league_id = LEAGUE_MAPPING.get(league_code)
        
        if not league_id:
            print(f"  Warning: No API mapping for league {league_code}")
            enhanced_features.append({})
            continue
        
        # Search for the fixture in API
        date_str = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
        fixtures = api_client.get_fixtures(date_str, league_id)
        
        # Try to match teams (this is simplified - you may need fuzzy matching)
        home_team = row['HomeTeam'].lower().strip()
        away_team = row['AwayTeam'].lower().strip()
        
        fixture_data = {}
        for fixture in fixtures:
            teams = fixture.get('teams', {})
            api_home = teams.get('home', {}).get('name', '').lower().strip()
            api_away = teams.get('away', {}).get('name', '').lower().strip()
            
            # Simple matching - you might need more sophisticated matching
            if (home_team in api_home or api_home in home_team) and \
               (away_team in api_away or api_away in away_team):
                
                fixture_id = fixture['fixture']['id']
                home_id = teams['home']['id']
                away_id = teams['away']['id']
                
                # Get additional data
                season = datetime.now().year
                
                # Team statistics
                home_stats = api_client.get_team_statistics(home_id, league_id, season)
                away_stats = api_client.get_team_statistics(away_id, league_id, season)
                
                # Head-to-head
                h2h = api_client.get_h2h(home_id, away_id)
                
                # Recent form
                home_form = api_client.get_team_form(home_id)
                away_form = api_client.get_team_form(away_id)
                
                # Injuries
                home_injuries = len(api_client.get_injuries(home_id))
                away_injuries = len(api_client.get_injuries(away_id))
                
                # API predictions
                predictions = api_client.get_predictions(fixture_id)
                
                # Extract features
                fixture_data = {
                    'api_fixture_id': fixture_id,
                    'home_team_id': home_id,
                    'away_team_id': away_id,
                    
                    # Form
                    'home_form_score': home_form.count('W') * 3 + home_form.count('D'),
                    'away_form_score': away_form.count('W') * 3 + away_form.count('D'),
                    'home_form_string': home_form,
                    'away_form_string': away_form,
                    
                    # Team stats (if available)
                    'home_goals_for_avg': extract_stat(home_stats, 'goals.for.average.total'),
                    'home_goals_against_avg': extract_stat(home_stats, 'goals.against.average.total'),
                    'away_goals_for_avg': extract_stat(away_stats, 'goals.for.average.total'),
                    'away_goals_against_avg': extract_stat(away_stats, 'goals.against.average.total'),
                    
                    # H2H stats
                    'h2h_home_wins': count_h2h_wins(h2h, home_id),
                    'h2h_draws': count_h2h_draws(h2h),
                    'h2h_away_wins': count_h2h_wins(h2h, away_id),
                    'h2h_total_goals_avg': calculate_h2h_goals_avg(h2h),
                    
                    # Injuries
                    'home_injuries': home_injuries,
                    'away_injuries': away_injuries,
                    
                    # API predictions (if available)
                    'api_prediction_home_win': extract_prediction(predictions, 'home'),
                    'api_prediction_draw': extract_prediction(predictions, 'draw'),
                    'api_prediction_away_win': extract_prediction(predictions, 'away'),
                    'api_prediction_btts': extract_prediction_btts(predictions),
                    'api_prediction_over25': extract_prediction_goals(predictions, 2.5),
                }
                
                break
        
        enhanced_features.append(fixture_data)
    
    # Add enhanced features to DataFrame
    enhanced_df = pd.DataFrame(enhanced_features)
    result_df = pd.concat([fixtures_df, enhanced_df], axis=1)
    
    print(f"Enhanced {len(result_df)} fixtures with {len(enhanced_df.columns)} new features")
    print(f"Total API requests made: {api_client.request_count}")
    
    return result_df

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_stat(stats_dict: Dict, path: str, default=0):
    """Extract nested statistic from API response"""
    keys = path.split('.')
    value = stats_dict
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key, {})
        else:
            return default
    return value if value else default

def count_h2h_wins(h2h_list: List[Dict], team_id: int) -> int:
    """Count wins for a team in H2H fixtures"""
    wins = 0
    for fixture in h2h_list:
        teams = fixture.get('teams', {})
        goals = fixture.get('goals', {})
        
        if teams.get('home', {}).get('id') == team_id:
            if goals.get('home', 0) > goals.get('away', 0):
                wins += 1
        elif teams.get('away', {}).get('id') == team_id:
            if goals.get('away', 0) > goals.get('home', 0):
                wins += 1
    
    return wins

def count_h2h_draws(h2h_list: List[Dict]) -> int:
    """Count draws in H2H fixtures"""
    draws = 0
    for fixture in h2h_list:
        goals = fixture.get('goals', {})
        if goals.get('home', 0) == goals.get('away', 0):
            draws += 1
    return draws

def calculate_h2h_goals_avg(h2h_list: List[Dict]) -> float:
    """Calculate average total goals in H2H fixtures"""
    if not h2h_list:
        return 0
    
    total_goals = 0
    for fixture in h2h_list:
        goals = fixture.get('goals', {})
        total_goals += goals.get('home', 0) + goals.get('away', 0)
    
    return total_goals / len(h2h_list) if h2h_list else 0

def extract_prediction(predictions: Dict, outcome: str) -> float:
    """Extract prediction probability from API response"""
    if not predictions:
        return 0
    
    pred = predictions.get('predictions', {})
    if outcome == 'home':
        return float(pred.get('home', '0%').strip('%')) / 100
    elif outcome == 'draw':
        return float(pred.get('draw', '0%').strip('%')) / 100
    elif outcome == 'away':
        return float(pred.get('away', '0%').strip('%')) / 100
    
    return 0

def extract_prediction_btts(predictions: Dict) -> float:
    """Extract BTTS prediction from API response"""
    if not predictions:
        return 0
    
    teams = predictions.get('teams', {})
    btts = predictions.get('predictions', {}).get('btts', {})
    return float(btts.get('yes', '0%').strip('%')) / 100

def extract_prediction_goals(predictions: Dict, threshold: float) -> float:
    """Extract over/under goals prediction from API response"""
    if not predictions:
        return 0
    
    goals = predictions.get('predictions', {}).get('goals', {})
    if threshold == 2.5:
        over = goals.get('over_2_5', {})
        return float(over.get('percentage', '0%').strip('%')) / 100
    
    return 0

# ============================================================================
# INTEGRATION WITH EXISTING PIPELINE
# ============================================================================

def integrate_with_weekly_run():
    """
    Modified version of fixture download step for run_weeklyOU.py
    This replaces the simple_fixture_downloader
    """
    print("="*60)
    print("🌍 ENHANCED FIXTURE DOWNLOAD WITH API-FOOTBALL")
    print("="*60)
    
    # Initialize API client
    if API_FOOTBALL_KEY == "YOUR_API_KEY_HERE":
        print("⚠️ API key not set! Falling back to simple downloader...")
        from simple_fixture_downloader import download_upcoming_fixtures
        return download_upcoming_fixtures()
    
    api_client = APIFootballClient(API_FOOTBALL_KEY)
    
    # Get fixtures for next 7 days
    all_fixtures = []
    start_date = datetime.now()
    
    for days_ahead in range(7):
        date = start_date + timedelta(days=days_ahead)
        date_str = date.strftime('%Y-%m-%d')
        print(f"\nFetching fixtures for {date_str}...")
        
        # Get fixtures for all mapped leagues
        for league_code, league_id in LEAGUE_MAPPING.items():
            fixtures = api_client.get_fixtures(date_str, league_id)
            
            for fixture in fixtures:
                fixture_data = parse_api_fixture(fixture, league_code)
                if fixture_data:
                    all_fixtures.append(fixture_data)
        
        # Also get extra leagues (Champions League, etc.)
        for league_id, league_name in EXTRA_LEAGUES.items():
            fixtures = api_client.get_fixtures(date_str, league_id)
            
            for fixture in fixtures:
                fixture_data = parse_api_fixture(fixture, league_name)
                if fixture_data:
                    all_fixtures.append(fixture_data)
    
    # Convert to DataFrame
    fixtures_df = pd.DataFrame(all_fixtures)
    
    if fixtures_df.empty:
        print("⚠️ No fixtures found via API! Falling back to simple downloader...")
        from simple_fixture_downloader import download_upcoming_fixtures
        return download_upcoming_fixtures()
    
    # Save to CSV
    output_path = Path("outputs") / "upcoming_fixtures.csv"
    output_path.parent.mkdir(exist_ok=True)
    fixtures_df.to_csv(output_path, index=False)
    
    print(f"\n✅ Downloaded {len(fixtures_df)} fixtures")
    print(f"   Leagues: {fixtures_df['League'].nunique()}")
    print(f"   Saved to: {output_path}")
    
    # Optionally enhance with additional stats
    if input("\nEnhance with additional API statistics? (y/n): ").lower() == 'y':
        enhanced_df = enhance_fixtures_with_api_data(fixtures_df, api_client)
        enhanced_path = Path("outputs") / "enhanced_fixtures.csv"
        enhanced_df.to_csv(enhanced_path, index=False)
        print(f"   Enhanced data saved to: {enhanced_path}")
        return enhanced_path
    
    return output_path

def parse_api_fixture(fixture: Dict, league_code: str) -> Optional[Dict]:
    """Parse API fixture into standard format"""
    try:
        fixture_info = fixture.get('fixture', {})
        teams = fixture.get('teams', {})
        
        # Parse date
        date_str = fixture_info.get('date', '')
        date = pd.to_datetime(date_str).strftime('%d/%m/%Y')
        
        return {
            'Date': date,
            'Time': pd.to_datetime(date_str).strftime('%H:%M'),
            'League': league_code,
            'HomeTeam': teams.get('home', {}).get('name', ''),
            'AwayTeam': teams.get('away', {}).get('name', ''),
            'fixture_id': fixture_info.get('id'),
            'venue': fixture_info.get('venue', {}).get('name', ''),
            'referee': fixture_info.get('referee', ''),
        }
    except Exception as e:
        print(f"Error parsing fixture: {e}")
        return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("API-Football Enhanced Integration Module")
    print("="*60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test mode - verify API connection
        print("Testing API connection...")
        
        if API_FOOTBALL_KEY == "YOUR_API_KEY_HERE":
            print("❌ Please set your API key in the script or environment variable!")
            sys.exit(1)
        
        client = APIFootballClient(API_FOOTBALL_KEY)
        
        # Test with Premier League fixture
        fixtures = client.get_fixtures(datetime.now().strftime('%Y-%m-%d'), 39)
        
        if fixtures:
            print(f"✅ API connection successful!")
            print(f"   Found {len(fixtures)} Premier League fixtures today")
        else:
            print("⚠️ No fixtures found (this might be normal if no matches today)")
        
        print(f"\nAPI requests made: {client.request_count}")
        
    elif len(sys.argv) > 1 and sys.argv[1] == "--integrate":
        # Integration mode - replace fixture downloader
        result = integrate_with_weekly_run()
        print(f"\nIntegration complete: {result}")
        
    else:
        # Default - show usage
        print("\nUsage:")
        print("  python enhanced_api_integration.py --test      # Test API connection")
        print("  python enhanced_api_integration.py --integrate # Run enhanced fixture download")
        print("\nConfiguration:")
        print(f"  API Key: {'✅ Set' if API_FOOTBALL_KEY != 'YOUR_API_KEY_HERE' else '❌ Not set'}")
        print(f"  Leagues mapped: {len(LEAGUE_MAPPING)}")
        print(f"  Extra leagues: {len(EXTRA_LEAGUES)}")

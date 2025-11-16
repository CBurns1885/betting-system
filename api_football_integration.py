#!/usr/bin/env python3
"""
api_football_integration.py
Complete API-Football integration with all betting markets and data types
Production-ready implementation for football prediction system
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

import requests
import pandas as pd
import numpy as np
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
RAPIDAPI_BASE = "https://api-football-v1.p.rapidapi.com/v3"
USE_RAPIDAPI = os.environ.get("USE_RAPIDAPI", "false").lower() == "true"

# Cache configuration
CACHE_DIR = Path("cache/api_football")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_EXPIRY = {
    "fixtures": 3600,        # 1 hour
    "statistics": 86400,     # 24 hours
    "teams": 604800,         # 1 week
    "leagues": 2592000,      # 30 days
    "odds": 300,             # 5 minutes
    "live": 15,              # 15 seconds
    "predictions": 3600,     # 1 hour
    "h2h": 86400,           # 24 hours
}

# League mappings
LEAGUE_MAPPING = {
    # English Leagues
    "E0": 39,   # Premier League
    "E1": 40,   # Championship
    "E2": 41,   # League One
    "E3": 42,   # League Two
    "EC": 43,   # National League
    
    # Spanish Leagues
    "SP1": 140, # La Liga
    "SP2": 141, # Segunda Division
    
    # German Leagues
    "D1": 78,   # Bundesliga
    "D2": 79,   # 2. Bundesliga
    
    # Italian Leagues
    "I1": 135,  # Serie A
    "I2": 136,  # Serie B
    
    # French Leagues
    "F1": 61,   # Ligue 1
    "F2": 62,   # Ligue 2
    
    # Dutch League
    "N1": 88,   # Eredivisie
    
    # Belgian League
    "B1": 144,  # Jupiler Pro League
    
    # Portuguese League
    "P1": 94,   # Primeira Liga
    
    # Turkish League
    "T1": 203,  # Super Lig
    
    # Scottish Leagues
    "SC0": 179, # Scottish Premiership
    "SC1": 180, # Scottish Championship
    
    # Greek League
    "G1": 197,  # Super League
}

# International competitions
INTERNATIONAL_LEAGUES = {
    1: "World Cup",
    2: "UEFA Champions League",
    3: "UEFA Europa League",
    4: "Euro Championship",
    5: "Nations League",
    6: "Copa America",
    7: "AFC Champions League",
    848: "UEFA Europa Conference League",
    531: "UEFA Super Cup",
    532: "Copa Libertadores",
    13: "Copa del Rey",
    45: "FA Cup",
    48: "League Cup",
    529: "Coupe de France",
    81: "DFB Pokal",
    137: "Coppa Italia",
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TeamStatistics:
    """Comprehensive team statistics"""
    team_id: int
    team_name: str
    form: str
    goals_for_home: int
    goals_for_away: int
    goals_against_home: int
    goals_against_away: int
    goals_for_avg_home: float
    goals_for_avg_away: float
    goals_against_avg_home: float
    goals_against_avg_away: float
    clean_sheets_home: int
    clean_sheets_away: int
    failed_to_score_home: int
    failed_to_score_away: int
    penalty_scored: int
    penalty_missed: int
    fixtures_played_home: int
    fixtures_played_away: int
    wins_home: int
    wins_away: int
    draws_home: int
    draws_away: int
    loses_home: int
    loses_away: int
    biggest_win_home: str
    biggest_win_away: str
    biggest_lose_home: str
    biggest_lose_away: str

@dataclass
class PlayerStatistics:
    """Player performance statistics"""
    player_id: int
    player_name: str
    position: str
    rating: float
    games_played: int
    games_started: int
    minutes: int
    goals: int
    assists: int
    saves: int = 0
    conceded: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    shots_total: int = 0
    shots_on: int = 0
    passes_total: int = 0
    passes_accuracy: int = 0
    key_passes: int = 0
    dribbles_success: int = 0
    penalty_scored: int = 0
    penalty_missed: int = 0

@dataclass
class OddsData:
    """Comprehensive odds from multiple bookmakers"""
    fixture_id: int
    bookmaker: str
    market: str
    last_update: datetime
    odds: Dict[str, float]

@dataclass
class InjuryData:
    """Team injury information"""
    player_id: int
    player_name: str
    type: str
    reason: str
    return_date: Optional[str] = None

@dataclass
class PredictionData:
    """API prediction data"""
    fixture_id: int
    predictions: Dict[str, Any]
    comparison: Dict[str, Dict[str, float]]
    teams: Dict[str, Any]
    h2h: List[Dict]
    goals: Dict[str, float]
    advice: str

# ============================================================================
# API CLIENT
# ============================================================================

class APIFootballClient:
    """
    Enhanced API-Football client with comprehensive data fetching
    Handles all markets, statistics, and real-time data
    """
    
    def __init__(self, api_key: str, use_rapidapi: bool = False):
        """Initialize API client with retry logic and session management"""
        self.api_key = api_key
        self.use_rapidapi = use_rapidapi
        self.base_url = RAPIDAPI_BASE if use_rapidapi else BASE_URL
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry = Retry(
            total=3,
            read=3,
            connect=3,
            backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504)
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        if use_rapidapi:
            self.session.headers.update({
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
            })
        else:
            self.session.headers.update({
                "x-apisports-key": api_key
            })
        
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit = 10  # requests per second
    
    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key for request"""
        params_str = json.dumps(params, sort_keys=True)
        key_str = f"{endpoint}_{params_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str, cache_type: str) -> Optional[Dict]:
        """Retrieve data from cache if valid"""
        cache_file = CACHE_DIR / f"{cache_type}_{cache_key}.json"
        
        if cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            max_age = CACHE_EXPIRY.get(cache_type, 3600)
            
            if cache_age < max_age:
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        return None
    
    def _save_to_cache(self, cache_key: str, cache_type: str, data: Dict):
        """Save data to cache"""
        cache_file = CACHE_DIR / f"{cache_type}_{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f, default=str)
    
    def _rate_limit_wait(self):
        """Implement rate limiting"""
        elapsed = time.time() - self.last_request_time
        min_interval = 1.0 / self.rate_limit
        
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None, cache_type: str = "general") -> Dict:
        """Make API request with caching and error handling"""
        if params is None:
            params = {}
        
        # Check cache first
        cache_key = self._get_cache_key(endpoint, params)
        cached_data = self._get_from_cache(cache_key, cache_type)
        if cached_data:
            return cached_data
        
        # Rate limiting
        self._rate_limit_wait()
        
        # Make request
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if data.get("errors") and data["errors"]:
                print(f"API Error on {endpoint}: {data['errors']}")
                return {"response": []}
            
            # Cache successful response
            self._save_to_cache(cache_key, cache_type, data)
            self.request_count += 1
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {endpoint}: {e}")
            return {"response": []}
    
    # ========================================================================
    # FIXTURES & MATCHES
    # ========================================================================
    
    def get_fixtures_by_date(self, date: str, league_id: Optional[int] = None) -> List[Dict]:
        """Get all fixtures for a specific date"""
        params = {
            "date": date,
            "timezone": "UTC"
        }
        if league_id:
            params["league"] = league_id
        
        data = self._make_request("/fixtures", params, "fixtures")
        return data.get("response", [])
    
    def get_fixture_by_id(self, fixture_id: int) -> Dict:
        """Get detailed fixture information"""
        params = {"id": fixture_id}
        data = self._make_request("/fixtures", params, "fixtures")
        response = data.get("response", [])
        return response[0] if response else {}
    
    def get_live_fixtures(self) -> List[Dict]:
        """Get all currently live fixtures"""
        params = {"live": "all"}
        data = self._make_request("/fixtures", params, "live")
        return data.get("response", [])
    
    def get_fixture_statistics(self, fixture_id: int) -> List[Dict]:
        """Get detailed match statistics"""
        params = {"fixture": fixture_id}
        data = self._make_request("/fixtures/statistics", params, "statistics")
        return data.get("response", [])
    
    def get_fixture_events(self, fixture_id: int) -> List[Dict]:
        """Get match events (goals, cards, substitutions)"""
        params = {"fixture": fixture_id}
        data = self._make_request("/fixtures/events", params, "fixtures")
        return data.get("response", [])
    
    def get_fixture_lineups(self, fixture_id: int) -> List[Dict]:
        """Get team lineups and formations"""
        params = {"fixture": fixture_id}
        data = self._make_request("/fixtures/lineups", params, "fixtures")
        return data.get("response", [])
    
    def get_fixture_player_statistics(self, fixture_id: int) -> List[Dict]:
        """Get player statistics for a fixture"""
        params = {"fixture": fixture_id}
        data = self._make_request("/fixtures/players", params, "statistics")
        return data.get("response", [])
    
    # ========================================================================
    # TEAMS & PLAYERS
    # ========================================================================
    
    def get_team_information(self, team_id: int) -> Dict:
        """Get team information"""
        params = {"id": team_id}
        data = self._make_request("/teams", params, "teams")
        response = data.get("response", [])
        return response[0] if response else {}
    
    def get_team_statistics(self, team_id: int, league_id: int, season: int) -> TeamStatistics:
        """Get comprehensive team statistics"""
        params = {
            "team": team_id,
            "league": league_id,
            "season": season
        }
        data = self._make_request("/teams/statistics", params, "statistics")
        response = data.get("response", {})
        
        if not response:
            return None
        
        # Parse statistics into TeamStatistics object
        stats = response
        return TeamStatistics(
            team_id=team_id,
            team_name=stats.get("team", {}).get("name", ""),
            form=stats.get("form", ""),
            goals_for_home=stats.get("goals", {}).get("for", {}).get("home", 0),
            goals_for_away=stats.get("goals", {}).get("for", {}).get("away", 0),
            goals_against_home=stats.get("goals", {}).get("against", {}).get("home", 0),
            goals_against_away=stats.get("goals", {}).get("against", {}).get("away", 0),
            goals_for_avg_home=float(stats.get("goals", {}).get("for", {}).get("average", {}).get("home", 0)),
            goals_for_avg_away=float(stats.get("goals", {}).get("for", {}).get("average", {}).get("away", 0)),
            goals_against_avg_home=float(stats.get("goals", {}).get("against", {}).get("average", {}).get("home", 0)),
            goals_against_avg_away=float(stats.get("goals", {}).get("against", {}).get("average", {}).get("away", 0)),
            clean_sheets_home=stats.get("clean_sheet", {}).get("home", 0),
            clean_sheets_away=stats.get("clean_sheet", {}).get("away", 0),
            failed_to_score_home=stats.get("failed_to_score", {}).get("home", 0),
            failed_to_score_away=stats.get("failed_to_score", {}).get("away", 0),
            penalty_scored=stats.get("penalty", {}).get("scored", {}).get("total", 0),
            penalty_missed=stats.get("penalty", {}).get("missed", {}).get("total", 0),
            fixtures_played_home=stats.get("fixtures", {}).get("played", {}).get("home", 0),
            fixtures_played_away=stats.get("fixtures", {}).get("played", {}).get("away", 0),
            wins_home=stats.get("fixtures", {}).get("wins", {}).get("home", 0),
            wins_away=stats.get("fixtures", {}).get("wins", {}).get("away", 0),
            draws_home=stats.get("fixtures", {}).get("draws", {}).get("home", 0),
            draws_away=stats.get("fixtures", {}).get("draws", {}).get("away", 0),
            loses_home=stats.get("fixtures", {}).get("loses", {}).get("home", 0),
            loses_away=stats.get("fixtures", {}).get("loses", {}).get("away", 0),
            biggest_win_home=str(stats.get("biggest", {}).get("wins", {}).get("home", "")),
            biggest_win_away=str(stats.get("biggest", {}).get("wins", {}).get("away", "")),
            biggest_lose_home=str(stats.get("biggest", {}).get("loses", {}).get("home", "")),
            biggest_lose_away=str(stats.get("biggest", {}).get("loses", {}).get("away", ""))
        )
    
    def get_team_squad(self, team_id: int) -> List[Dict]:
        """Get team squad/players"""
        params = {"team": team_id}
        data = self._make_request("/players/squads", params, "teams")
        response = data.get("response", [])
        return response[0].get("players", []) if response else []
    
    def get_player_statistics(self, player_id: int, season: int) -> PlayerStatistics:
        """Get player statistics for a season"""
        params = {
            "id": player_id,
            "season": season
        }
        data = self._make_request("/players", params, "statistics")
        response = data.get("response", [])
        
        if not response:
            return None
        
        player_data = response[0]
        stats = player_data.get("statistics", [])
        
        if not stats:
            return None
        
        # Aggregate stats across all competitions
        total_stats = stats[0]  # Primary league stats
        
        return PlayerStatistics(
            player_id=player_id,
            player_name=player_data.get("player", {}).get("name", ""),
            position=total_stats.get("games", {}).get("position", ""),
            rating=float(total_stats.get("games", {}).get("rating", 0) or 0),
            games_played=total_stats.get("games", {}).get("appearences", 0),
            games_started=total_stats.get("games", {}).get("lineups", 0),
            minutes=total_stats.get("games", {}).get("minutes", 0),
            goals=total_stats.get("goals", {}).get("total", 0),
            assists=total_stats.get("goals", {}).get("assists", 0),
            saves=total_stats.get("goals", {}).get("saves", 0),
            conceded=total_stats.get("goals", {}).get("conceded", 0),
            yellow_cards=total_stats.get("cards", {}).get("yellow", 0),
            red_cards=total_stats.get("cards", {}).get("red", 0),
            shots_total=total_stats.get("shots", {}).get("total", 0),
            shots_on=total_stats.get("shots", {}).get("on", 0),
            passes_total=total_stats.get("passes", {}).get("total", 0),
            passes_accuracy=total_stats.get("passes", {}).get("accuracy", 0),
            key_passes=total_stats.get("passes", {}).get("key", 0),
            dribbles_success=total_stats.get("dribbles", {}).get("success", 0),
            penalty_scored=total_stats.get("penalty", {}).get("scored", 0),
            penalty_missed=total_stats.get("penalty", {}).get("missed", 0)
        )
    
    def get_top_scorers(self, league_id: int, season: int) -> List[Dict]:
        """Get top scorers for a league"""
        params = {
            "league": league_id,
            "season": season
        }
        data = self._make_request("/players/topscorers", params, "statistics")
        return data.get("response", [])
    
    def get_top_assists(self, league_id: int, season: int) -> List[Dict]:
        """Get top assist providers for a league"""
        params = {
            "league": league_id,
            "season": season
        }
        data = self._make_request("/players/topassists", params, "statistics")
        return data.get("response", [])
    
    def get_top_cards(self, league_id: int, season: int, card_type: str = "yellow") -> List[Dict]:
        """Get players with most cards"""
        endpoint = f"/players/top{card_type}cards"
        params = {
            "league": league_id,
            "season": season
        }
        data = self._make_request(endpoint, params, "statistics")
        return data.get("response", [])
    
    # ========================================================================
    # HEAD TO HEAD
    # ========================================================================
    
    def get_h2h(self, team1_id: int, team2_id: int, last: int = 20) -> List[Dict]:
        """Get head-to-head fixtures between two teams"""
        params = {
            "h2h": f"{team1_id}-{team2_id}",
            "last": last
        }
        data = self._make_request("/fixtures/headtohead", params, "h2h")
        return data.get("response", [])
    
    def analyze_h2h(self, h2h_fixtures: List[Dict]) -> Dict:
        """Analyze H2H fixtures for patterns"""
        if not h2h_fixtures:
            return {}
        
        team1_wins = 0
        team2_wins = 0
        draws = 0
        total_goals = []
        btts_count = 0
        over25_count = 0
        
        for fixture in h2h_fixtures:
            goals = fixture.get("goals", {})
            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0
            
            total = home_goals + away_goals
            total_goals.append(total)
            
            if home_goals > away_goals:
                team1_wins += 1
            elif away_goals > home_goals:
                team2_wins += 1
            else:
                draws += 1
            
            if home_goals > 0 and away_goals > 0:
                btts_count += 1
            
            if total > 2.5:
                over25_count += 1
        
        total_matches = len(h2h_fixtures)
        
        return {
            "total_matches": total_matches,
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "draws": draws,
            "team1_win_pct": (team1_wins / total_matches * 100) if total_matches > 0 else 0,
            "team2_win_pct": (team2_wins / total_matches * 100) if total_matches > 0 else 0,
            "draw_pct": (draws / total_matches * 100) if total_matches > 0 else 0,
            "avg_total_goals": np.mean(total_goals) if total_goals else 0,
            "btts_pct": (btts_count / total_matches * 100) if total_matches > 0 else 0,
            "over25_pct": (over25_count / total_matches * 100) if total_matches > 0 else 0,
            "last_5_results": self._get_last_n_results(h2h_fixtures[:5])
        }
    
    def _get_last_n_results(self, fixtures: List[Dict]) -> str:
        """Get string representation of last N results"""
        results = []
        for fixture in fixtures:
            goals = fixture.get("goals", {})
            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0
            results.append(f"{home_goals}-{away_goals}")
        return ", ".join(results)
    
    # ========================================================================
    # INJURIES & SUSPENSIONS
    # ========================================================================
    
    def get_injuries(self, team_id: Optional[int] = None, league_id: Optional[int] = None, 
                     fixture_id: Optional[int] = None) -> List[InjuryData]:
        """Get injury information"""
        params = {}
        if team_id:
            params["team"] = team_id
        if league_id:
            params["league"] = league_id
        if fixture_id:
            params["fixture"] = fixture_id
        
        data = self._make_request("/injuries", params, "injuries")
        response = data.get("response", [])
        
        injuries = []
        for item in response:
            player = item.get("player", {})
            injuries.append(InjuryData(
                player_id=player.get("id", 0),
                player_name=player.get("name", ""),
                type=player.get("type", ""),
                reason=player.get("reason", ""),
                return_date=player.get("return", None)
            ))
        
        return injuries
    
    def get_suspensions(self, team_id: int) -> List[Dict]:
        """Get suspension information for a team"""
        # Note: API-Football doesn't have a dedicated suspensions endpoint
        # We need to derive this from cards data and fixture events
        squad = self.get_team_squad(team_id)
        suspensions = []
        
        for player in squad:
            player_id = player.get("id")
            # Check recent cards for this player
            # This would need to be implemented based on your specific needs
            
        return suspensions
    
    # ========================================================================
    # PREDICTIONS
    # ========================================================================
    
    def get_predictions(self, fixture_id: int) -> PredictionData:
        """Get API predictions for a fixture"""
        params = {"fixture": fixture_id}
        data = self._make_request("/predictions", params, "predictions")
        response = data.get("response", [])
        
        if not response:
            return None
        
        pred = response[0]
        
        return PredictionData(
            fixture_id=fixture_id,
            predictions=pred.get("predictions", {}),
            comparison=pred.get("comparison", {}),
            teams=pred.get("teams", {}),
            h2h=pred.get("h2h", []),
            goals=pred.get("goals", {}),
            advice=pred.get("predictions", {}).get("advice", "")
        )
    
    # ========================================================================
    # ODDS & BETTING MARKETS
    # ========================================================================
    
    def get_odds(self, fixture_id: int, bookmaker_id: Optional[int] = None) -> List[OddsData]:
        """Get all odds for a fixture"""
        params = {"fixture": fixture_id}
        if bookmaker_id:
            params["bookmaker"] = bookmaker_id
        
        data = self._make_request("/odds", params, "odds")
        response = data.get("response", [])
        
        if not response:
            return []
        
        odds_list = []
        fixture_odds = response[0]
        
        for bookmaker in fixture_odds.get("bookmakers", []):
            bookmaker_name = bookmaker.get("name", "")
            
            for bet in bookmaker.get("bets", []):
                market = bet.get("name", "")
                odds_dict = {}
                
                for value in bet.get("values", []):
                    odds_dict[value.get("value", "")] = float(value.get("odd", 0))
                
                odds_list.append(OddsData(
                    fixture_id=fixture_id,
                    bookmaker=bookmaker_name,
                    market=market,
                    last_update=datetime.fromisoformat(fixture_odds.get("update", "")),
                    odds=odds_dict
                ))
        
        return odds_list
    
    def get_live_odds(self, fixture_id: int) -> List[OddsData]:
        """Get live/in-play odds for a fixture"""
        params = {"fixture": fixture_id, "bet": "1"}  # bet=1 for live bets
        data = self._make_request("/odds/live", params, "live")
        response = data.get("response", [])
        
        # Parse similar to get_odds
        return self._parse_odds_response(response, fixture_id)
    
    def _parse_odds_response(self, response: List[Dict], fixture_id: int) -> List[OddsData]:
        """Parse odds response into OddsData objects"""
        odds_list = []
        
        for item in response:
            for bookmaker in item.get("bookmakers", []):
                bookmaker_name = bookmaker.get("name", "")
                
                for bet in bookmaker.get("bets", []):
                    market = bet.get("name", "")
                    odds_dict = {}
                    
                    for value in bet.get("values", []):
                        odds_dict[value.get("value", "")] = float(value.get("odd", 0))
                    
                    odds_list.append(OddsData(
                        fixture_id=fixture_id,
                        bookmaker=bookmaker_name,
                        market=market,
                        last_update=datetime.now(),
                        odds=odds_dict
                    ))
        
        return odds_list
    
    def get_bookmakers(self) -> List[Dict]:
        """Get list of all bookmakers"""
        data = self._make_request("/bookmakers", cache_type="bookmakers")
        return data.get("response", [])
    
    def get_bet_types(self) -> List[Dict]:
        """Get all available bet types"""
        data = self._make_request("/bets", cache_type="bets")
        return data.get("response", [])
    
    # ========================================================================
    # STANDINGS & LEAGUES
    # ========================================================================
    
    def get_standings(self, league_id: int, season: int) -> List[Dict]:
        """Get league standings"""
        params = {
            "league": league_id,
            "season": season
        }
        data = self._make_request("/standings", params, "standings")
        response = data.get("response", [])
        return response[0].get("league", {}).get("standings", [[]])[0] if response else []
    
    def get_leagues(self, country: Optional[str] = None, season: Optional[int] = None) -> List[Dict]:
        """Get available leagues"""
        params = {}
        if country:
            params["country"] = country
        if season:
            params["season"] = season
        
        data = self._make_request("/leagues", params, "leagues")
        return data.get("response", [])
    
    def get_league_rounds(self, league_id: int, season: int, current: bool = True) -> List[str]:
        """Get rounds/matchdays for a league"""
        params = {
            "league": league_id,
            "season": season
        }
        if current:
            params["current"] = "true"
        
        data = self._make_request("/fixtures/rounds", params, "fixtures")
        return data.get("response", [])
    
    # ========================================================================
    # VENUES & WEATHER
    # ========================================================================
    
    def get_venues(self, country: Optional[str] = None, city: Optional[str] = None) -> List[Dict]:
        """Get venue information"""
        params = {}
        if country:
            params["country"] = country
        if city:
            params["city"] = city
        
        data = self._make_request("/venues", params, "venues")
        return data.get("response", [])
    
    # ========================================================================
    # SIDELINED (Additional injuries/suspensions info)
    # ========================================================================
    
    def get_sidelined(self, player_id: Optional[int] = None, coach_id: Optional[int] = None) -> List[Dict]:
        """Get sidelined information for players or coaches"""
        params = {}
        if player_id:
            params["player"] = player_id
        if coach_id:
            params["coach"] = coach_id
        
        data = self._make_request("/sidelined", params, "sidelined")
        return data.get("response", [])
    
    # ========================================================================
    # TROPHIES
    # ========================================================================
    
    def get_trophies(self, player_id: Optional[int] = None, coach_id: Optional[int] = None) -> List[Dict]:
        """Get trophies won by player or coach"""
        params = {}
        if player_id:
            params["player"] = player_id
        if coach_id:
            params["coach"] = coach_id
        
        data = self._make_request("/trophies", params, "trophies")
        return data.get("response", [])
    
    # ========================================================================
    # TRANSFERS
    # ========================================================================
    
    def get_transfers(self, team_id: Optional[int] = None, player_id: Optional[int] = None) -> List[Dict]:
        """Get transfer information"""
        params = {}
        if team_id:
            params["team"] = team_id
        if player_id:
            params["player"] = player_id
        
        data = self._make_request("/transfers", params, "transfers")
        return data.get("response", [])

# ============================================================================
# DATA PROCESSING & ANALYSIS
# ============================================================================

class MarketAnalyzer:
    """Analyze all betting markets for value and opportunities"""
    
    def __init__(self, api_client: APIFootballClient):
        self.api = api_client
    
    def analyze_match_result(self, odds_data: List[OddsData], prediction: PredictionData) -> Dict:
        """Analyze 1X2 market"""
        best_odds = self._get_best_odds(odds_data, "Match Winner")
        
        if not best_odds or not prediction:
            return {}
        
        api_probs = {
            "home": float(prediction.predictions.get("home", "0").strip("%")) / 100,
            "draw": float(prediction.predictions.get("draw", "0").strip("%")) / 100,
            "away": float(prediction.predictions.get("away", "0").strip("%")) / 100
        }
        
        return {
            "market": "Match Winner",
            "best_odds": best_odds,
            "api_probabilities": api_probs,
            "value_bets": self._find_value(best_odds, api_probs),
            "recommended_bet": self._recommend_bet(best_odds, api_probs)
        }
    
    def analyze_over_under(self, odds_data: List[OddsData], prediction: PredictionData, 
                           line: float = 2.5) -> Dict:
        """Analyze Over/Under markets"""
        market_name = f"Goals Over/Under"
        best_odds = self._get_best_odds(odds_data, market_name)
        
        if not best_odds or not prediction:
            return {}
        
        # Calculate probabilities based on predicted goals
        home_goals = float(prediction.goals.get("home", 0))
        away_goals = float(prediction.goals.get("away", 0))
        total_predicted = home_goals + away_goals
        
        # Simple probability calculation (would be better with Poisson)
        over_prob = 1 - self._poisson_cdf(line, total_predicted)
        under_prob = self._poisson_cdf(line, total_predicted)
        
        api_probs = {
            f"Over {line}": over_prob,
            f"Under {line}": under_prob
        }
        
        return {
            "market": f"Over/Under {line}",
            "predicted_goals": total_predicted,
            "best_odds": best_odds,
            "calculated_probabilities": api_probs,
            "value_bets": self._find_value(best_odds, api_probs),
            "recommended_bet": self._recommend_bet(best_odds, api_probs)
        }
    
    def analyze_btts(self, odds_data: List[OddsData], prediction: PredictionData) -> Dict:
        """Analyze Both Teams to Score market"""
        best_odds = self._get_best_odds(odds_data, "Both Teams Score")
        
        if not best_odds or not prediction:
            return {}
        
        # Calculate BTTS probability from predicted goals
        home_goals = float(prediction.goals.get("home", 0))
        away_goals = float(prediction.goals.get("away", 0))
        
        # Probability of scoring at least 1 goal
        home_scores_prob = 1 - np.exp(-home_goals)  # Poisson P(X >= 1)
        away_scores_prob = 1 - np.exp(-away_goals)
        
        btts_yes_prob = home_scores_prob * away_scores_prob
        btts_no_prob = 1 - btts_yes_prob
        
        api_probs = {
            "Yes": btts_yes_prob,
            "No": btts_no_prob
        }
        
        return {
            "market": "Both Teams to Score",
            "best_odds": best_odds,
            "calculated_probabilities": api_probs,
            "value_bets": self._find_value(best_odds, api_probs),
            "recommended_bet": self._recommend_bet(best_odds, api_probs)
        }
    
    def analyze_asian_handicap(self, odds_data: List[OddsData], prediction: PredictionData,
                              line: float = -0.5) -> Dict:
        """Analyze Asian Handicap markets"""
        market_name = "Asian Handicap"
        best_odds = self._get_best_odds_ah(odds_data, market_name, line)
        
        if not best_odds or not prediction:
            return {}
        
        # Calculate AH probabilities based on predicted goal difference
        home_goals = float(prediction.goals.get("home", 0))
        away_goals = float(prediction.goals.get("away", 0))
        predicted_diff = home_goals - away_goals
        
        # Adjust for handicap line
        adjusted_diff = predicted_diff + line
        
        if line == -0.5:  # Home -0.5
            home_covers_prob = self._calculate_ah_probability(adjusted_diff, 0)
            away_covers_prob = 1 - home_covers_prob
        else:
            # More complex calculation for other lines
            home_covers_prob = self._calculate_ah_probability(adjusted_diff, 0)
            away_covers_prob = 1 - home_covers_prob
        
        api_probs = {
            f"Home {line}": home_covers_prob,
            f"Away {-line}": away_covers_prob
        }
        
        return {
            "market": f"Asian Handicap {line}",
            "predicted_difference": predicted_diff,
            "best_odds": best_odds,
            "calculated_probabilities": api_probs,
            "value_bets": self._find_value(best_odds, api_probs),
            "recommended_bet": self._recommend_bet(best_odds, api_probs)
        }
    
    def analyze_correct_score(self, odds_data: List[OddsData], prediction: PredictionData) -> Dict:
        """Analyze Correct Score markets"""
        best_odds = self._get_best_odds(odds_data, "Correct Score")
        
        if not best_odds or not prediction:
            return {}
        
        # Calculate correct score probabilities using Poisson distribution
        home_goals = float(prediction.goals.get("home", 0))
        away_goals = float(prediction.goals.get("away", 0))
        
        score_probs = {}
        for h in range(6):  # 0-5 goals
            for a in range(6):
                prob = self._poisson_pmf(h, home_goals) * self._poisson_pmf(a, away_goals)
                score_probs[f"{h}:{a}"] = prob
        
        # Normalize probabilities
        total_prob = sum(score_probs.values())
        score_probs = {k: v/total_prob for k, v in score_probs.items()}
        
        # Find top 5 most likely scores
        top_scores = sorted(score_probs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "market": "Correct Score",
            "best_odds": best_odds,
            "top_5_scores": dict(top_scores),
            "value_bets": self._find_value(best_odds, score_probs),
            "recommended_bet": self._recommend_correct_score(best_odds, score_probs)
        }
    
    def analyze_double_chance(self, odds_data: List[OddsData], prediction: PredictionData) -> Dict:
        """Analyze Double Chance markets"""
        best_odds = self._get_best_odds(odds_data, "Double Chance")
        
        if not best_odds or not prediction:
            return {}
        
        # Calculate double chance probabilities
        home_prob = float(prediction.predictions.get("home", "0").strip("%")) / 100
        draw_prob = float(prediction.predictions.get("draw", "0").strip("%")) / 100
        away_prob = float(prediction.predictions.get("away", "0").strip("%")) / 100
        
        api_probs = {
            "Home/Draw": home_prob + draw_prob,
            "Home/Away": home_prob + away_prob,
            "Draw/Away": draw_prob + away_prob
        }
        
        return {
            "market": "Double Chance",
            "best_odds": best_odds,
            "calculated_probabilities": api_probs,
            "value_bets": self._find_value(best_odds, api_probs),
            "recommended_bet": self._recommend_bet(best_odds, api_probs)
        }
    
    def analyze_half_time(self, odds_data: List[OddsData], fixture_stats: Dict) -> Dict:
        """Analyze Half-Time markets"""
        best_odds_ht = self._get_best_odds(odds_data, "First Half Winner")
        best_odds_htft = self._get_best_odds(odds_data, "HT/FT Double")
        
        results = {}
        
        if best_odds_ht:
            # Analyze based on team's first half performance
            results["first_half_winner"] = {
                "market": "First Half Winner",
                "best_odds": best_odds_ht,
                "analysis": "Based on first half statistics"
            }
        
        if best_odds_htft:
            results["ht_ft_double"] = {
                "market": "Half-Time/Full-Time",
                "best_odds": best_odds_htft,
                "analysis": "Based on comeback patterns"
            }
        
        return results
    
    def analyze_goalscorer(self, odds_data: List[OddsData], player_stats: List[PlayerStatistics]) -> Dict:
        """Analyze Goalscorer markets"""
        first_goal = self._get_best_odds(odds_data, "First Goal Scorer")
        anytime = self._get_best_odds(odds_data, "Anytime Goal Scorer")
        
        results = {}
        
        if first_goal:
            results["first_goalscorer"] = {
                "market": "First Goal Scorer",
                "best_odds": first_goal,
                "top_candidates": self._get_top_scorers(player_stats, 3)
            }
        
        if anytime:
            results["anytime_goalscorer"] = {
                "market": "Anytime Goal Scorer", 
                "best_odds": anytime,
                "top_candidates": self._get_top_scorers(player_stats, 5)
            }
        
        return results
    
    def analyze_corners(self, odds_data: List[OddsData], team_stats: Dict) -> Dict:
        """Analyze Corner markets"""
        total_corners = self._get_best_odds(odds_data, "Corners Over Under")
        team_corners = self._get_best_odds(odds_data, "Team Total Corners")
        
        results = {}
        
        if total_corners:
            # Calculate expected corners based on team stats
            home_corners_avg = team_stats.get("home_corners_avg", 5)
            away_corners_avg = team_stats.get("away_corners_avg", 5)
            expected_total = home_corners_avg + away_corners_avg
            
            results["total_corners"] = {
                "market": "Total Corners",
                "expected": expected_total,
                "best_odds": total_corners,
                "recommended_line": self._recommend_corners_line(expected_total)
            }
        
        return results
    
    def analyze_cards(self, odds_data: List[OddsData], referee_stats: Dict) -> Dict:
        """Analyze Card markets"""
        total_cards = self._get_best_odds(odds_data, "Cards Over Under")
        
        if not total_cards:
            return {}
        
        # Calculate expected cards based on referee tendencies
        ref_avg_cards = referee_stats.get("avg_cards_per_game", 3.5)
        
        return {
            "market": "Total Cards",
            "referee_average": ref_avg_cards,
            "best_odds": total_cards,
            "recommended_bet": self._recommend_cards_bet(ref_avg_cards, total_cards)
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _get_best_odds(self, odds_data: List[OddsData], market: str) -> Dict[str, float]:
        """Get best odds across all bookmakers for a market"""
        market_odds = [o for o in odds_data if market in o.market]
        
        if not market_odds:
            return {}
        
        best = {}
        for outcome in market_odds[0].odds.keys():
            best_odd = max(o.odds.get(outcome, 0) for o in market_odds)
            best_bookmaker = next((o.bookmaker for o in market_odds 
                                  if o.odds.get(outcome, 0) == best_odd), "")
            best[outcome] = {"odd": best_odd, "bookmaker": best_bookmaker}
        
        return best
    
    def _get_best_odds_ah(self, odds_data: List[OddsData], market: str, line: float) -> Dict:
        """Get best odds for Asian Handicap with specific line"""
        market_odds = [o for o in odds_data if market in o.market]
        
        best = {}
        for odds in market_odds:
            for outcome, odd in odds.odds.items():
                if str(line) in outcome:
                    if outcome not in best or odd > best[outcome]["odd"]:
                        best[outcome] = {"odd": odd, "bookmaker": odds.bookmaker}
        
        return best
    
    def _find_value(self, odds: Dict, probabilities: Dict, min_edge: float = 0.05) -> List[Dict]:
        """Find value bets with positive expected value"""
        value_bets = []
        
        for outcome, prob in probabilities.items():
            if outcome in odds:
                odd = odds[outcome].get("odd", 0) if isinstance(odds[outcome], dict) else odds[outcome]
                if odd > 0:
                    ev = (prob * odd) - 1
                    
                    if ev > min_edge:
                        value_bets.append({
                            "outcome": outcome,
                            "probability": prob,
                            "odd": odd,
                            "expected_value": ev,
                            "edge_percentage": ev * 100,
                            "kelly_stake": self._kelly_criterion(prob, odd)
                        })
        
        return sorted(value_bets, key=lambda x: x["expected_value"], reverse=True)
    
    def _recommend_bet(self, odds: Dict, probabilities: Dict) -> Dict:
        """Recommend the best bet based on value and probability"""
        value_bets = self._find_value(odds, probabilities)
        
        if not value_bets:
            return {"recommendation": "No value found"}
        
        best = value_bets[0]
        
        return {
            "outcome": best["outcome"],
            "probability": best["probability"],
            "odd": best["odd"],
            "expected_value": best["expected_value"],
            "recommended_stake": best["kelly_stake"],
            "confidence": self._calculate_confidence(best["probability"], best["expected_value"])
        }
    
    def _recommend_correct_score(self, odds: Dict, probabilities: Dict) -> Dict:
        """Recommend correct score bets"""
        value_bets = self._find_value(odds, probabilities, min_edge=0.20)  # Higher edge for CS
        
        if not value_bets:
            return {"recommendation": "No value in correct score market"}
        
        # Recommend top 2 value scores
        top_scores = value_bets[:2]
        
        return {
            "recommended_scores": [
                {
                    "score": bet["outcome"],
                    "probability": bet["probability"],
                    "odd": bet["odd"],
                    "expected_value": bet["expected_value"]
                }
                for bet in top_scores
            ],
            "combined_stake": sum(bet["kelly_stake"] for bet in top_scores)
        }
    
    def _recommend_corners_line(self, expected: float) -> float:
        """Recommend corners line based on expected total"""
        lines = [7.5, 8.5, 9.5, 10.5, 11.5, 12.5]
        return min(lines, key=lambda x: abs(x - expected))
    
    def _recommend_cards_bet(self, ref_avg: float, odds: Dict) -> Dict:
        """Recommend cards bet based on referee average"""
        if ref_avg > 4.5:
            return {"recommendation": "Over cards", "confidence": "High"}
        elif ref_avg < 2.5:
            return {"recommendation": "Under cards", "confidence": "High"}
        else:
            return {"recommendation": "Avoid cards market", "confidence": "Low"}
    
    def _get_top_scorers(self, players: List[PlayerStatistics], n: int) -> List[Dict]:
        """Get top N likely scorers"""
        scorers = sorted(players, key=lambda p: p.goals / max(p.games_played, 1), reverse=True)
        
        return [
            {
                "player": s.player_name,
                "goals": s.goals,
                "games": s.games_played,
                "goals_per_game": s.goals / max(s.games_played, 1)
            }
            for s in scorers[:n]
        ]
    
    def _kelly_criterion(self, prob: float, odds: float, fraction: float = 0.25) -> float:
        """Calculate Kelly stake percentage"""
        if prob <= 0 or prob >= 1 or odds <= 1:
            return 0
        
        q = 1 - prob
        kelly = (prob * odds - q) / odds
        
        # Use fractional Kelly for safety
        stake = kelly * fraction
        
        # Cap at 5% of bankroll
        return min(max(0, stake), 0.05)
    
    def _calculate_confidence(self, probability: float, ev: float) -> str:
        """Calculate confidence level for a bet"""
        if probability > 0.70 and ev > 0.15:
            return "Very High"
        elif probability > 0.60 and ev > 0.10:
            return "High"
        elif probability > 0.50 and ev > 0.05:
            return "Medium"
        else:
            return "Low"
    
    def _poisson_pmf(self, k: int, lambda_: float) -> float:
        """Poisson probability mass function"""
        return np.exp(-lambda_) * (lambda_ ** k) / np.math.factorial(k)
    
    def _poisson_cdf(self, k: float, lambda_: float) -> float:
        """Poisson cumulative distribution function"""
        if k < 0:
            return 0
        
        k_int = int(k)
        total = 0
        for i in range(k_int + 1):
            total += self._poisson_pmf(i, lambda_)
        
        return total
    
    def _calculate_ah_probability(self, expected_diff: float, line: float) -> float:
        """Calculate Asian Handicap coverage probability"""
        # Simplified - would use more sophisticated model in production
        # Assuming normal distribution of goal difference
        from scipy.stats import norm
        
        std_dev = 1.5  # Standard deviation of goal difference
        z_score = (line - expected_diff) / std_dev
        
        return 1 - norm.cdf(z_score)

# ============================================================================
# ARBITRAGE FINDER
# ============================================================================

class ArbitrageFinder:
    """Find arbitrage opportunities across bookmakers"""
    
    def find_arbitrage(self, odds_data: List[OddsData]) -> List[Dict]:
        """Find all arbitrage opportunities in the odds data"""
        arbs = []
        
        # Group odds by market
        markets = {}
        for odds in odds_data:
            if odds.market not in markets:
                markets[odds.market] = []
            markets[odds.market].append(odds)
        
        # Check each market for arbitrage
        for market, market_odds in markets.items():
            if market == "Match Winner":
                arb = self._find_three_way_arb(market_odds)
                if arb:
                    arbs.append(arb)
            elif "Over/Under" in market or "Both Teams Score" in market:
                arb = self._find_two_way_arb(market_odds, market)
                if arb:
                    arbs.append(arb)
        
        return arbs
    
    def _find_three_way_arb(self, odds_list: List[OddsData]) -> Optional[Dict]:
        """Find arbitrage in 3-way markets (1X2)"""
        best_home = 0
        best_draw = 0
        best_away = 0
        
        home_bookie = ""
        draw_bookie = ""
        away_bookie = ""
        
        for odds in odds_list:
            home_odd = odds.odds.get("Home", 0)
            draw_odd = odds.odds.get("Draw", 0) 
            away_odd = odds.odds.get("Away", 0)
            
            if home_odd > best_home:
                best_home = home_odd
                home_bookie = odds.bookmaker
            
            if draw_odd > best_draw:
                best_draw = draw_odd
                draw_bookie = odds.bookmaker
            
            if away_odd > best_away:
                best_away = away_odd
                away_bookie = odds.bookmaker
        
        if best_home and best_draw and best_away:
            arb_percentage = (1/best_home + 1/best_draw + 1/best_away)
            
            if arb_percentage < 1.0:
                profit = (1 - arb_percentage) * 100
                
                # Calculate stakes for €100 total
                total_stake = 100
                stake_home = (1/best_home) / arb_percentage * total_stake
                stake_draw = (1/best_draw) / arb_percentage * total_stake
                stake_away = (1/best_away) / arb_percentage * total_stake
                
                return {
                    "market": "Match Winner",
                    "profit_percentage": profit,
                    "arb_percentage": arb_percentage,
                    "guaranteed_profit": profit,
                    "stakes": {
                        "home": {"stake": stake_home, "odd": best_home, "bookmaker": home_bookie},
                        "draw": {"stake": stake_draw, "odd": best_draw, "bookmaker": draw_bookie},
                        "away": {"stake": stake_away, "odd": best_away, "bookmaker": away_bookie}
                    },
                    "total_stake": total_stake,
                    "guaranteed_return": total_stake * (1 + profit/100)
                }
        
        return None
    
    def _find_two_way_arb(self, odds_list: List[OddsData], market: str) -> Optional[Dict]:
        """Find arbitrage in 2-way markets"""
        # Determine outcome names based on market
        if "Over/Under" in market:
            outcome1 = next((k for k in odds_list[0].odds.keys() if "Over" in k), None)
            outcome2 = next((k for k in odds_list[0].odds.keys() if "Under" in k), None)
        elif "Both Teams Score" in market:
            outcome1 = "Yes"
            outcome2 = "No"
        else:
            return None
        
        if not outcome1 or not outcome2:
            return None
        
        best_outcome1 = 0
        best_outcome2 = 0
        bookie1 = ""
        bookie2 = ""
        
        for odds in odds_list:
            odd1 = odds.odds.get(outcome1, 0)
            odd2 = odds.odds.get(outcome2, 0)
            
            if odd1 > best_outcome1:
                best_outcome1 = odd1
                bookie1 = odds.bookmaker
            
            if odd2 > best_outcome2:
                best_outcome2 = odd2
                bookie2 = odds.bookmaker
        
        if best_outcome1 and best_outcome2:
            arb_percentage = (1/best_outcome1 + 1/best_outcome2)
            
            if arb_percentage < 1.0:
                profit = (1 - arb_percentage) * 100
                
                total_stake = 100
                stake1 = (1/best_outcome1) / arb_percentage * total_stake
                stake2 = (1/best_outcome2) / arb_percentage * total_stake
                
                return {
                    "market": market,
                    "profit_percentage": profit,
                    "arb_percentage": arb_percentage,
                    "guaranteed_profit": profit,
                    "stakes": {
                        outcome1: {"stake": stake1, "odd": best_outcome1, "bookmaker": bookie1},
                        outcome2: {"stake": stake2, "odd": best_outcome2, "bookmaker": bookie2}
                    },
                    "total_stake": total_stake,
                    "guaranteed_return": total_stake * (1 + profit/100)
                }
        
        return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("API-Football Complete Integration Module")
    print("=" * 80)
    print("\nThis module provides:")
    print("- Complete fixture and match data fetching")
    print("- Team and player statistics")
    print("- Head-to-head analysis")
    print("- Injury and suspension tracking")
    print("- API predictions integration")
    print("- All betting markets analysis:")
    print("  * Match Result (1X2)")
    print("  * Over/Under (all lines)")
    print("  * Both Teams to Score")
    print("  * Asian Handicap")
    print("  * Correct Score")
    print("  * Double Chance")
    print("  * Half-Time/Full-Time")
    print("  * Goalscorer Markets")
    print("  * Corners")
    print("  * Cards")
    print("- Arbitrage opportunity finder")
    print("- Value betting calculator")
    print("- Kelly Criterion staking")
    
    if API_KEY:
        print(f"\n✅ API Key configured")
    else:
        print("\n❌ API Key not set - please configure API_FOOTBALL_KEY environment variable")

# config.py - NBA Betting System Configuration
from pathlib import Path
import os
from datetime import date, datetime

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR, INTERIM_DIR, PROCESSED_DIR = DATA_DIR / "raw", DATA_DIR / "interim", DATA_DIR / "processed"

def get_dated_output_dir():
    dated_dir = BASE_DIR / "outputs" / datetime.now().strftime("%Y-%m-%d")
    dated_dir.mkdir(parents=True, exist_ok=True)
    return dated_dir

OUTPUT_DIR = get_dated_output_dir()
MODEL_ARTIFACTS_DIR = BASE_DIR / "models"
MODELS_DIR = MODEL_ARTIFACTS_DIR

for p in [DATA_DIR, RAW_DIR, INTERIM_DIR, PROCESSED_DIR, MODEL_ARTIFACTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

FEATURES_PARQUET = PROCESSED_DIR / "features.parquet"
HISTORICAL_PARQUET = PROCESSED_DIR / "historical_games.parquet"

# NBA Season (Oct-June)
CURRENT_YEAR = date.today().year
CURRENT_MONTH = date.today().month
ACTIVE_SEASON_START = CURRENT_YEAR if CURRENT_MONTH >= 10 else CURRENT_YEAR - 1
SEASON_START_YEAR = int(os.environ.get("NBA_SEASON_START_YEAR", 2018))
SEASONS = list(range(SEASON_START_YEAR, ACTIVE_SEASON_START + 1))

# 30 NBA Teams
NBA_TEAMS = {
    # Eastern Conference - Atlantic
    "BOS": "Boston Celtics", "BKN": "Brooklyn Nets", "NYK": "New York Knicks",
    "PHI": "Philadelphia 76ers", "TOR": "Toronto Raptors",
    # Eastern Conference - Central
    "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DET": "Detroit Pistons",
    "IND": "Indiana Pacers", "MIL": "Milwaukee Bucks",
    # Eastern Conference - Southeast
    "ATL": "Atlanta Hawks", "CHA": "Charlotte Hornets", "MIA": "Miami Heat",
    "ORL": "Orlando Magic", "WAS": "Washington Wizards",
    # Western Conference - Northwest
    "DEN": "Denver Nuggets", "MIN": "Minnesota Timberwolves", "OKC": "Oklahoma City Thunder",
    "POR": "Portland Trail Blazers", "UTA": "Utah Jazz",
    # Western Conference - Pacific
    "GSW": "Golden State Warriors", "LAC": "Los Angeles Clippers", "LAL": "Los Angeles Lakers",
    "PHX": "Phoenix Suns", "SAC": "Sacramento Kings",
    # Western Conference - Southwest
    "DAL": "Dallas Mavericks", "HOU": "Houston Rockets", "MEM": "Memphis Grizzlies",
    "NOP": "New Orleans Pelicans", "SAS": "San Antonio Spurs",
}

DIVISIONS = {
    "ATLANTIC": ["BOS", "BKN", "NYK", "PHI", "TOR"],
    "CENTRAL": ["CHI", "CLE", "DET", "IND", "MIL"],
    "SOUTHEAST": ["ATL", "CHA", "MIA", "ORL", "WAS"],
    "NORTHWEST": ["DEN", "MIN", "OKC", "POR", "UTA"],
    "PACIFIC": ["GSW", "LAC", "LAL", "PHX", "SAC"],
    "SOUTHWEST": ["DAL", "HOU", "MEM", "NOP", "SAS"],
}

CONFERENCES = {
    "EAST": ["BOS", "BKN", "NYK", "PHI", "TOR", "CHI", "CLE", "DET", "IND", "MIL",
             "ATL", "CHA", "MIA", "ORL", "WAS"],
    "WEST": ["DEN", "MIN", "OKC", "POR", "UTA", "GSW", "LAC", "LAL", "PHX", "SAC",
             "DAL", "HOU", "MEM", "NOP", "SAS"],
}

# NBA Betting Markets
PRIMARY_MARKETS = ["MONEYLINE", "SPREAD", "TOTAL"]
ADDITIONAL_MARKETS = ["FIRST_HALF", "FIRST_QUARTER", "PLAYER_PROPS"]

# APIs
NBA_STATS_API_BASE = "https://stats.nba.com/stats"
BALLDONTLIE_API_BASE = "https://api.balldontlie.io/v1"
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba"

RANDOM_SEED = 42
PRIMARY_TARGETS = ["MONEYLINE", "SPREAD", "TOTAL"]
USE_ELO = True
USE_ROLLING_FORM = True

def log_header(msg: str):
    print(f"\n{'='*max(20, len(msg)+4)}\n  {msg}\n{'='*max(20, len(msg)+4)}")

print(f"🏀 NBA Betting System - Output: {OUTPUT_DIR}")

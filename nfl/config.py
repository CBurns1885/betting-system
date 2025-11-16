# config.py - NFL Betting System Configuration
from pathlib import Path
import os
from datetime import date, datetime

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"

# Dated output directories
def get_dated_output_dir():
    """Creates a dated folder for outputs (e.g., outputs/2025-11-16)"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    dated_dir = BASE_DIR / "outputs" / date_str
    dated_dir.mkdir(parents=True, exist_ok=True)
    return dated_dir

# Main output directory - DATED
OUTPUT_DIR = get_dated_output_dir()
MODEL_ARTIFACTS_DIR = BASE_DIR / "models"
MODELS_DIR = MODEL_ARTIFACTS_DIR  # Alias for compatibility

# API Keys (users should set these as environment variables)
SPORTRADAR_API_KEY = os.environ.get("SPORTRADAR_API_KEY", "")
ESPN_API_KEY = os.environ.get("ESPN_API_KEY", "")
THE_ODDS_API_KEY = os.environ.get("THE_ODDS_API_KEY", "")

# Ensure base directories exist
for p in [DATA_DIR, RAW_DIR, INTERIM_DIR, PROCESSED_DIR, MODEL_ARTIFACTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# --- Key File Paths ---
FEATURES_PARQUET = PROCESSED_DIR / "features.parquet"
HISTORICAL_PARQUET = PROCESSED_DIR / "historical_games.parquet"
WEEKLY_OUTPUT_CSV = OUTPUT_DIR / "weekly_bets_full.csv"
BLEND_WEIGHTS_JSON = MODEL_ARTIFACTS_DIR / "blend_weights.json"

# --- NFL Season Structure ---
CURRENT_YEAR = date.today().year
CURRENT_MONTH = date.today().month

# NFL season runs Sept-Feb, so season year is based on fall start
ACTIVE_SEASON_START = CURRENT_YEAR if CURRENT_MONTH >= 9 else CURRENT_YEAR - 1

# NFL seasons to train on (e.g., 2018, 2019, 2020, etc.)
SEASON_START_YEAR = int(os.environ.get("NFL_SEASON_START_YEAR", 2018))
SEASONS = list(range(SEASON_START_YEAR, ACTIVE_SEASON_START + 1))

# --- NFL Teams by Division ---
NFL_TEAMS = {
    # AFC East
    "BUF": "Buffalo Bills",
    "MIA": "Miami Dolphins",
    "NE": "New England Patriots",
    "NYJ": "New York Jets",

    # AFC North
    "BAL": "Baltimore Ravens",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "PIT": "Pittsburgh Steelers",

    # AFC South
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "TEN": "Tennessee Titans",

    # AFC West
    "DEN": "Denver Broncos",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",

    # NFC East
    "DAL": "Dallas Cowboys",
    "NYG": "New York Giants",
    "PHI": "Philadelphia Eagles",
    "WAS": "Washington Commanders",

    # NFC North
    "CHI": "Chicago Bears",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "MIN": "Minnesota Vikings",

    # NFC South
    "ATL": "Atlanta Falcons",
    "CAR": "Carolina Panthers",
    "NO": "New Orleans Saints",
    "TB": "Tampa Bay Buccaneers",

    # NFC West
    "ARI": "Arizona Cardinals",
    "LAR": "Los Angeles Rams",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
}

# Divisions
DIVISIONS = {
    "AFC_EAST": ["BUF", "MIA", "NE", "NYJ"],
    "AFC_NORTH": ["BAL", "CIN", "CLE", "PIT"],
    "AFC_SOUTH": ["HOU", "IND", "JAX", "TEN"],
    "AFC_WEST": ["DEN", "KC", "LV", "LAC"],
    "NFC_EAST": ["DAL", "NYG", "PHI", "WAS"],
    "NFC_NORTH": ["CHI", "DET", "GB", "MIN"],
    "NFC_SOUTH": ["ATL", "CAR", "NO", "TB"],
    "NFC_WEST": ["ARI", "LAR", "SF", "SEA"],
}

CONFERENCES = {
    "AFC": ["BUF", "MIA", "NE", "NYJ", "BAL", "CIN", "CLE", "PIT",
            "HOU", "IND", "JAX", "TEN", "DEN", "KC", "LV", "LAC"],
    "NFC": ["DAL", "NYG", "PHI", "WAS", "CHI", "DET", "GB", "MIN",
            "ATL", "CAR", "NO", "TB", "ARI", "LAR", "SF", "SEA"],
}

# --- NFL Betting Markets ---
PRIMARY_MARKETS = [
    "MONEYLINE",      # Win/Loss (no tie in NFL overtime)
    "SPREAD",         # Point spread (e.g., -7.5)
    "TOTAL",          # Over/Under total points
]

ADDITIONAL_MARKETS = [
    "TEAM_TOTAL",     # Team-specific O/U
    "FIRST_HALF",     # First half moneyline/spread/total
    "QUARTER",        # Quarter-specific props
]

# --- Data Sources ---
# ESPN API (free, limited)
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

# The Odds API (for betting lines)
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl"

# Pro Football Reference (scraping fallback)
PFR_BASE = "https://www.pro-football-reference.com"

# --- Randomness / Reproducibility ---
RANDOM_SEED = 42
GLOBAL_SEED = RANDOM_SEED

# --- Modeling ---
PRIMARY_TARGETS = ["MONEYLINE", "SPREAD", "TOTAL"]
USE_ELO = True
USE_ROLLING_FORM = True
USE_ADVANCED_STATS = True  # QB rating, yards per play, etc.

TRAIN_SEASONS_BACK = int(os.environ.get("NFL_TRAIN_SEASONS_BACK", 5))

def season_code(year_start: int) -> str:
    """Returns season code like '2024' for 2024-25 season"""
    return f"{year_start}"

def log_header(msg: str) -> None:
    bar = "=" * max(20, len(msg) + 4)
    print(f"\n{bar}")
    print(f"  {msg}")
    print(f"{bar}")

# Email configuration
EMAIL_SMTP_SERVER = os.environ.get("EMAIL_SMTP_SERVER", "smtp-mail.outlook.com")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", "")

print(f"🏈 NFL Betting System - Output directory: {OUTPUT_DIR}")

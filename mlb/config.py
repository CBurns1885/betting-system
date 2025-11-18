# config.py - MLB Betting System Configuration
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
    """Creates a dated folder for outputs (e.g., outputs/2025-05-15)"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    dated_dir = BASE_DIR / "outputs" / date_str
    dated_dir.mkdir(parents=True, exist_ok=True)
    return dated_dir

# Main output directory - DATED
OUTPUT_DIR = get_dated_output_dir()
MODEL_ARTIFACTS_DIR = BASE_DIR / "models"
MODELS_DIR = MODEL_ARTIFACTS_DIR  # Alias for compatibility

# API Keys (users should set these as environment variables)
BASEBALL_REFERENCE_API_KEY = os.environ.get("BASEBALL_REFERENCE_API_KEY", "")
STATCAST_API_KEY = os.environ.get("STATCAST_API_KEY", "")
THE_ODDS_API_KEY = os.environ.get("THE_ODDS_API_KEY", "")

# Ensure base directories exist
for p in [DATA_DIR, RAW_DIR, INTERIM_DIR, PROCESSED_DIR, MODEL_ARTIFACTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# --- Key File Paths ---
FEATURES_PARQUET = PROCESSED_DIR / "features.parquet"
HISTORICAL_PARQUET = PROCESSED_DIR / "historical_games.parquet"
WEEKLY_OUTPUT_CSV = OUTPUT_DIR / "weekly_predictions.csv"
BLEND_WEIGHTS_JSON = MODEL_ARTIFACTS_DIR / "blend_weights.json"

# --- MLB Season Structure ---
CURRENT_YEAR = date.today().year
CURRENT_MONTH = date.today().month

# MLB season runs April-October
ACTIVE_SEASON_START = CURRENT_YEAR if CURRENT_MONTH >= 4 else CURRENT_YEAR - 1

# MLB seasons to train on (e.g., 2018, 2019, 2020, etc.)
SEASON_START_YEAR = int(os.environ.get("MLB_SEASON_START_YEAR", 2018))
SEASONS = list(range(SEASON_START_YEAR, ACTIVE_SEASON_START + 1))

# --- MLB Teams by Division ---
MLB_TEAMS = {
    # AL East
    "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox",
    "NYY": "New York Yankees",
    "TB": "Tampa Bay Rays",
    "TOR": "Toronto Blue Jays",

    # AL Central
    "CWS": "Chicago White Sox",
    "CLE": "Cleveland Guardians",
    "DET": "Detroit Tigers",
    "KC": "Kansas City Royals",
    "MIN": "Minnesota Twins",

    # AL West
    "HOU": "Houston Astros",
    "LAA": "Los Angeles Angels",
    "OAK": "Oakland Athletics",
    "SEA": "Seattle Mariners",
    "TEX": "Texas Rangers",

    # NL East
    "ATL": "Atlanta Braves",
    "MIA": "Miami Marlins",
    "NYM": "New York Mets",
    "PHI": "Philadelphia Phillies",
    "WAS": "Washington Nationals",

    # NL Central
    "CHC": "Chicago Cubs",
    "CIN": "Cincinnati Reds",
    "MIL": "Milwaukee Brewers",
    "PIT": "Pittsburgh Pirates",
    "STL": "St. Louis Cardinals",

    # NL West
    "ARI": "Arizona Diamondbacks",
    "COL": "Colorado Rockies",
    "LAD": "Los Angeles Dodgers",
    "SD": "San Diego Padres",
    "SF": "San Francisco Giants",
}

# Divisions
DIVISIONS = {
    "AL_EAST": ["BAL", "BOS", "NYY", "TB", "TOR"],
    "AL_CENTRAL": ["CWS", "CLE", "DET", "KC", "MIN"],
    "AL_WEST": ["HOU", "LAA", "OAK", "SEA", "TEX"],
    "NL_EAST": ["ATL", "MIA", "NYM", "PHI", "WAS"],
    "NL_CENTRAL": ["CHC", "CIN", "MIL", "PIT", "STL"],
    "NL_WEST": ["ARI", "COL", "LAD", "SD", "SF"],
}

LEAGUES = {
    "AL": ["BAL", "BOS", "NYY", "TB", "TOR", "CWS", "CLE", "DET", "KC", "MIN",
           "HOU", "LAA", "OAK", "SEA", "TEX"],
    "NL": ["ATL", "MIA", "NYM", "PHI", "WAS", "CHC", "CIN", "MIL", "PIT", "STL",
           "ARI", "COL", "LAD", "SD", "SF"],
}

# --- Ballpark Factors ---
# Park factors affect runs scored (1.0 = neutral, >1.0 = hitter-friendly, <1.0 = pitcher-friendly)
BALLPARK_FACTORS = {
    "BAL": 1.05,  # Camden Yards - slightly hitter friendly
    "BOS": 1.08,  # Fenway - Green Monster, hitter friendly
    "NYY": 1.03,  # Yankee Stadium - short porch
    "TB": 0.96,   # Tropicana - pitcher friendly
    "TOR": 1.02,  # Rogers Centre
    "CWS": 1.00,  # Guaranteed Rate
    "CLE": 0.98,  # Progressive Field
    "DET": 1.01,  # Comerica Park
    "KC": 1.00,   # Kauffman Stadium
    "MIN": 1.02,  # Target Field
    "HOU": 0.99,  # Minute Maid Park
    "LAA": 1.00,  # Angel Stadium
    "OAK": 0.94,  # Oakland Coliseum - most pitcher friendly
    "SEA": 0.97,  # T-Mobile Park
    "TEX": 1.06,  # Globe Life Field - hitter friendly
    "ATL": 1.02,  # Truist Park
    "MIA": 0.96,  # LoanDepot Park - pitcher friendly
    "NYM": 0.98,  # Citi Field
    "PHI": 1.04,  # Citizens Bank Park
    "WAS": 1.01,  # Nationals Park
    "CHC": 1.07,  # Wrigley Field - wind matters
    "CIN": 1.08,  # Great American Ball Park - very hitter friendly
    "MIL": 0.99,  # American Family Field
    "PIT": 0.97,  # PNC Park
    "STL": 1.01,  # Busch Stadium
    "ARI": 1.05,  # Chase Field - hitter friendly
    "COL": 1.25,  # Coors Field - EXTREMELY hitter friendly (altitude)
    "LAD": 0.98,  # Dodger Stadium - pitcher friendly
    "SD": 0.95,   # Petco Park - pitcher friendly
    "SF": 0.93,   # Oracle Park - most pitcher friendly
}

# --- MLB Betting Markets ---
PRIMARY_MARKETS = [
    "MONEYLINE",      # Win/Loss
    "RUN_LINE",       # Spread (usually -1.5/+1.5)
    "TOTAL",          # Over/Under total runs
    "FIRST_5",        # First 5 innings result (pitcher-dependent)
]

ADDITIONAL_MARKETS = [
    "TEAM_TOTAL",     # Team-specific O/U runs
    "FIRST_INNING",   # First inning scoring
    "ALTERNATE_LINES", # Different run lines
]

# Standard run line
STANDARD_RUN_LINE = 1.5

# --- Data Sources ---
# Baseball Reference (scraping)
BASEBALL_REF_BASE = "https://www.baseball-reference.com"

# MLB Stats API (official)
MLB_STATS_API_BASE = "https://statsapi.mlb.com/api/v1"

# Statcast/Savant (advanced metrics)
STATCAST_BASE = "https://baseballsavant.mlb.com"

# The Odds API (for betting lines)
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports/baseball_mlb"

# --- Randomness / Reproducibility ---
RANDOM_SEED = 42
GLOBAL_SEED = RANDOM_SEED

# --- Modeling ---
PRIMARY_TARGETS = ["MONEYLINE", "RUN_LINE", "TOTAL", "FIRST_5"]
USE_ELO = True
USE_ROLLING_FORM = True
USE_PITCHER_STATS = True  # Critical for MLB!
USE_BALLPARK_FACTORS = True
USE_WEATHER = True  # Temperature/wind affect scoring

TRAIN_SEASONS_BACK = int(os.environ.get("MLB_TRAIN_SEASONS_BACK", 5))

def season_code(year_start: int) -> str:
    """Returns season code like '2024' for 2024 season"""
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

print(f"⚾ MLB Betting System - Output directory: {OUTPUT_DIR}")

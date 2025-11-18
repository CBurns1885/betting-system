# config.py - Rugby Union Betting System
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

for p in [DATA_DIR, RAW_DIR, INTERIM_DIR, PROCESSED_DIR, MODEL_ARTIFACTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

FEATURES_PARQUET = PROCESSED_DIR / "features.parquet"
HISTORICAL_PARQUET = PROCESSED_DIR / "historical_matches.parquet"

CURRENT_YEAR = date.today().year
SEASON_START_YEAR = int(os.environ.get("RUGBY_SEASON_START_YEAR", 2018))
SEASONS = list(range(SEASON_START_YEAR, CURRENT_YEAR + 1))

# Major Rugby Union Competitions
COMPETITIONS = {
    # International
    "SIX_NATIONS": {"tier": "Top", "teams": ["ENG", "IRE", "SCO", "WAL", "FRA", "ITA"]},
    "RUGBY_CHAMPIONSHIP": {"tier": "Top", "teams": ["NZL", "AUS", "RSA", "ARG"]},
    "AUTUMN_INTERNATIONALS": {"tier": "Top", "teams": "Various"},
    "WORLD_CUP": {"tier": "Top", "frequency": "4 years"},
    
    # Club Competitions
    "PREMIERSHIP": {"tier": "Top", "country": "England"},
    "TOP_14": {"tier": "Top", "country": "France"},
    "URC": {"tier": "Top", "description": "United Rugby Championship (Celtic/Italian/SA)"},
    "SUPER_RUGBY": {"tier": "Top", "regions": ["NZ", "AUS", "Pacific"]},
    "CHAMPIONS_CUP": {"tier": "Top", "description": "European Champions Cup"},
}

# Major Rugby Nations (Tier 1)
TIER_1_NATIONS = {
    "NZL": "New Zealand (All Blacks)",
    "IRE": "Ireland",
    "RSA": "South Africa (Springboks)",
    "FRA": "France",
    "ENG": "England",
    "SCO": "Scotland",
    "WAL": "Wales",
    "AUS": "Australia (Wallabies)",
    "ARG": "Argentina (Pumas)",
    "ITA": "Italy",
    "JPN": "Japan (Brave Blossoms)",
    "FIJ": "Fiji",
}

# Rugby Betting Markets
PRIMARY_MARKETS = [
    "MATCH_WINNER",     # 1X2 (Home/Draw/Away) - Draws are possible!
    "HANDICAP",         # Point handicap (like spread but can be large)
    "TOTAL_POINTS",     # Over/Under total points
    "FIRST_HALF",       # First half result
]

ADDITIONAL_MARKETS = [
    "WINNING_MARGIN",   # Margin brackets (1-12, 13-18, 19-24, 25+)
    "FIRST_TRYSCORER",  # Player to score first try
    "TOTAL_TRIES",      # Total tries in match
    "BOTH_TEAMS_SCORE_TRY", # Both teams score at least 1 try
]

# Home Advantage is SIGNIFICANT in rugby
HOME_ADVANTAGE_FACTOR = 1.15  # Home team scores ~15% more on average

# Weather Impact (rain heavily favors defense/kicking)
WEATHER_MATTERS = True

# Physical Dominance Stats
KEY_STATS = [
    "tries", "conversions", "penalties", "drop_goals",
    "possession_pct", "territory_pct",
    "tackles", "meters_gained", "line_breaks",
    "turnovers", "penalties_conceded",
    "scrums_won", "lineouts_won",
]

RANDOM_SEED = 42
PRIMARY_TARGETS = ["MATCH_WINNER", "HANDICAP", "TOTAL_POINTS"]
USE_ELO = True
USE_HOME_ADVANTAGE = True

def log_header(msg: str):
    print(f"\n{'='*max(20, len(msg)+4)}\n  {msg}\n{'='*max(20, len(msg)+4)}")

print(f"🏉 Rugby Union Betting System - Output: {OUTPUT_DIR}")

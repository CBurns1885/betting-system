# config.py - Rugby Union Betting System Configuration
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

# Rugby Union Competitions
CURRENT_YEAR = date.today().year
SEASON_START_YEAR = int(os.environ.get("RUGBY_SEASON_START_YEAR", 2018))
SEASONS = list(range(SEASON_START_YEAR, CURRENT_YEAR + 1))

# Tier 1 Rugby Nations (strongest teams)
TIER_1_NATIONS = {
    "NZL": "New Zealand (All Blacks)",
    "IRE": "Ireland",
    "RSA": "South Africa (Springboks)",
    "FRA": "France",
    "ENG": "England",
    "WAL": "Wales",
    "SCO": "Scotland",
    "AUS": "Australia (Wallabies)",
    "ARG": "Argentina (Pumas)",
    "ITA": "Italy",
    "FIJ": "Fiji",
    "JAP": "Japan",
}

# Tier 2 Nations
TIER_2_NATIONS = {
    "SAM": "Samoa",
    "TON": "Tonga",
    "GEO": "Georgia",
    "USA": "United States",
    "CAN": "Canada",
    "URU": "Uruguay",
    "NAM": "Namibia",
    "ROM": "Romania",
}

# Major International Competitions
COMPETITIONS = {
    # International
    "SIX_NATIONS": {
        "tier": "Top",
        "teams": ["ENG", "IRE", "SCO", "WAL", "FRA", "ITA"],
        "season": "Feb-Mar"
    },
    "RUGBY_CHAMPIONSHIP": {
        "tier": "Top",
        "teams": ["NZL", "AUS", "RSA", "ARG"],
        "season": "Aug-Oct"
    },
    "AUTUMN_INTERNATIONALS": {
        "tier": "Top",
        "teams": "Tier 1 + Tier 2",
        "season": "Nov"
    },
    "RUGBY_WORLD_CUP": {
        "tier": "Top",
        "teams": "All",
        "frequency": "Every 4 years"
    },

    # Club Competitions
    "EUROPEAN_CHAMPIONS_CUP": {
        "tier": "Club",
        "leagues": ["England", "France", "Ireland", "Wales", "Scotland", "Italy"]
    },
    "UNITED_RUGBY_CHAMPIONSHIP": {
        "tier": "Club",
        "leagues": ["Ireland", "Wales", "Scotland", "Italy", "South Africa"]
    },
    "ENGLISH_PREMIERSHIP": {
        "tier": "Club",
        "country": "England",
        "teams": 10
    },
    "TOP_14": {
        "tier": "Club",
        "country": "France",
        "teams": 14
    },
    "SUPER_RUGBY": {
        "tier": "Club",
        "countries": ["Australia", "New Zealand", "Pacific Islands"],
        "teams": 12
    },
}

# Rugby Union Betting Markets
PRIMARY_MARKETS = [
    "MATCH_WINNER",     # 1X2 (Home/Draw/Away) - draws are common!
    "HANDICAP",         # Points handicap (e.g., -7.5)
    "TOTAL_POINTS",     # Over/Under total points
    "FIRST_HALF",       # First half result
]

ADDITIONAL_MARKETS = [
    "WINNING_MARGIN",   # Margin of victory brackets
    "TEAM_TOTAL",       # Team-specific points O/U
    "TRY_SCORER",       # First/Anytime try scorer
    "HALF_TIME_FULL_TIME",  # HT/FT result combination
]

# Rugby-Specific Factors

# Home advantage is SIGNIFICANT in rugby (~15% boost in scoring)
HOME_ADVANTAGE_FACTOR = 1.15

# Altitude effect (e.g., South Africa high veldt)
ALTITUDE_TEAMS = ["RSA"]  # Some SA teams play at altitude
ALTITUDE_BONUS = 1.08

# Weather impact (rain = lower scoring, more forward play)
WEATHER_IMPACT = True

# Tournament fatigue (especially in World Cups with short turnarounds)
FATIGUE_FACTOR = True

# Scoring patterns
AVG_TRIES_PER_MATCH = 4.5
AVG_POINTS_PER_MATCH = 45
TRY_VALUE = 5
CONVERSION_VALUE = 2
PENALTY_VALUE = 3
DROP_GOAL_VALUE = 3

# Data Sources
RUGBY_DATA_API = "https://api.rugbydata.com"  # Hypothetical
ESPN_SCRUM_BASE = "https://www.espn.com/rugby/scoreboard"
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports/rugbyleague_nrl"

# APIs and keys
THE_ODDS_API_KEY = os.environ.get("THE_ODDS_API_KEY", "")

RANDOM_SEED = 42
PRIMARY_TARGETS = ["MATCH_WINNER", "HANDICAP", "TOTAL_POINTS"]
USE_ELO = True
USE_HOME_ADVANTAGE = True
USE_WEATHER = True
USE_HEAD_TO_HEAD = True  # Important for international matchups

def log_header(msg: str):
    print(f"\n{'='*max(20, len(msg)+4)}\n  {msg}\n{'='*max(20, len(msg)+4)}")

print(f"🏉 Rugby Union Betting System - Output: {OUTPUT_DIR}")

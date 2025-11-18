# config.py - Tennis Betting System Configuration
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

# Tennis Tours
CURRENT_YEAR = date.today().year
SEASON_START_YEAR = int(os.environ.get("TENNIS_SEASON_START_YEAR", 2018))
SEASONS = list(range(SEASON_START_YEAR, CURRENT_YEAR + 1))

# Tennis Tours
TOURS = {
    "ATP": "Men's Tennis (ATP Tour)",
    "WTA": "Women's Tennis (WTA Tour)",
    "CHALLENGER": "ATP Challenger Tour",
    "ITF_M": "ITF Men's Circuit",
    "ITF_W": "ITF Women's Circuit",
}

# Surface Types (CRITICAL for tennis)
SURFACES = {
    "HARD": {"speed": "medium-fast", "bounce": "medium", "description": "US Open, Australian Open"},
    "CLAY": {"speed": "slow", "bounce": "high", "description": "French Open, mostly Europe"},
    "GRASS": {"speed": "fast", "bounce": "low", "description": "Wimbledon, rare"},
    "CARPET": {"speed": "fast", "bounce": "low", "description": "Indoor, increasingly rare"},
}

# Major Tournaments (Grand Slams + Masters 1000)
MAJOR_TOURNAMENTS = {
    # Grand Slams (Best of 5 for men)
    "AUSTRALIAN_OPEN": {"surface": "HARD", "best_of": 5, "tier": "Grand Slam"},
    "FRENCH_OPEN": {"surface": "CLAY", "best_of": 5, "tier": "Grand Slam"},
    "WIMBLEDON": {"surface": "GRASS", "best_of": 5, "tier": "Grand Slam"},
    "US_OPEN": {"surface": "HARD", "best_of": 5, "tier": "Grand Slam"},
    
    # ATP Masters 1000 (Best of 3)
    "INDIAN_WELLS": {"surface": "HARD", "best_of": 3, "tier": "Masters 1000"},
    "MIAMI": {"surface": "HARD", "best_of": 3, "tier": "Masters 1000"},
    "MONTE_CARLO": {"surface": "CLAY", "best_of": 3, "tier": "Masters 1000"},
    "MADRID": {"surface": "CLAY", "best_of": 3, "tier": "Masters 1000"},
    "ROME": {"surface": "CLAY", "best_of": 3, "tier": "Masters 1000"},
    "CANADA": {"surface": "HARD", "best_of": 3, "tier": "Masters 1000"},
    "CINCINNATI": {"surface": "HARD", "best_of": 3, "tier": "Masters 1000"},
    "SHANGHAI": {"surface": "HARD", "best_of": 3, "tier": "Masters 1000"},
    "PARIS": {"surface": "HARD", "best_of": 3, "tier": "Masters 1000"},
}

# Tennis Betting Markets
PRIMARY_MARKETS = [
    "MATCH_WINNER",     # Moneyline (simple H2H)
    "SET_BETTING",      # Exact score in sets (2-0, 2-1, etc.)
    "TOTAL_GAMES",      # Over/Under total games in match
    "FIRST_SET",        # Who wins first set
]

ADDITIONAL_MARKETS = [
    "GAME_HANDICAP",    # Handicap on total games
    "PLAYER_TOTAL_GAMES", # Individual player game totals
    "TIEBREAK",         # Will there be a tiebreak
    "SET_HANDICAP",     # Set handicap
]

# Surface Performance Matters HUGELY
# Clay specialists vs hard court players
SURFACE_SPECIALISTS = True

# Head-to-head very important in tennis (1v1)
H2H_IMPORTANCE = "HIGH"

# APIs and Data Sources
ATP_API_BASE = "https://api.atptour.com"
WTA_API_BASE = "https://api.wtatennis.com"
TENNIS_ABSTRACT_BASE = "http://www.tennisabstract.com"  # Great free stats
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports/tennis"

RANDOM_SEED = 42
PRIMARY_TARGETS = ["MATCH_WINNER", "SET_BETTING", "TOTAL_GAMES"]
USE_ELO = True
USE_SURFACE_ELO = True  # Separate ELO per surface!
USE_H2H = True

def log_header(msg: str):
    print(f"\n{'='*max(20, len(msg)+4)}\n  {msg}\n{'='*max(20, len(msg)+4)}")

print(f"🎾 Tennis Betting System - Output: {OUTPUT_DIR}")

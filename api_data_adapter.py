#!/usr/bin/env python3
"""
api_data_adapter.py
Adapter to convert API-Football data to football-data.co.uk CSV format
Allows seamless switching between CSV downloads and API-Football
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enhanced_api_integration import APIFootballClient, LEAGUE_MAPPING

# ============================================================================
# API TO CSV CONVERSION
# ============================================================================

def convert_api_fixture_to_csv_row(fixture: Dict, league_code: str, season: str) -> Dict:
    """
    Convert a single API-Football fixture to CSV format

    Args:
        fixture: API-Football fixture object
        league_code: League code (e.g., "E0", "SP1")
        season: Season code (e.g., "2324")

    Returns:
        Dictionary with CSV columns
    """
    try:
        # Extract basic match info
        fixture_data = fixture.get("fixture", {})
        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        score = fixture.get("score", {})

        # Get match date
        date_str = fixture_data.get("date", "")
        match_date = pd.to_datetime(date_str).strftime("%d/%m/%Y") if date_str else ""

        # Get teams
        home_team = teams.get("home", {}).get("name", "")
        away_team = teams.get("away", {}).get("name", "")

        # Get full-time goals
        fthg = goals.get("home")
        ftag = goals.get("away")

        # Determine result
        if fthg is not None and ftag is not None:
            if fthg > ftag:
                ftr = "H"
            elif ftag > fthg:
                ftr = "A"
            else:
                ftr = "D"
        else:
            ftr = None

        # Get odds (if available)
        # Note: API-Football odds require separate endpoint calls
        # For now, set to NaN - can be enhanced later

        return {
            "League": league_code,
            "Date": match_date,
            "HomeTeam": home_team,
            "AwayTeam": away_team,
            "FTHG": fthg,
            "FTAG": ftag,
            "FTR": ftr,
            "B365H": np.nan,  # Bet365 home odds - requires odds endpoint
            "B365D": np.nan,  # Bet365 draw odds
            "B365A": np.nan,  # Bet365 away odds
            "PSCH": np.nan,   # Pinnacle home odds
            "PSCD": np.nan,   # Pinnacle draw odds
            "PSCA": np.nan,   # Pinnacle away odds
            "Season": season,
        }
    except Exception as e:
        print(f"⚠️ Error converting fixture: {e}")
        return None


def fetch_historical_from_api(
    api_client: APIFootballClient,
    league_code: str,
    season_year: int
) -> pd.DataFrame:
    """
    Fetch historical match data from API-Football for a league/season

    Args:
        api_client: Initialized API-Football client
        league_code: League code (e.g., "E0")
        season_year: Season start year (e.g., 2023 for 2023-24)

    Returns:
        DataFrame in football-data.co.uk CSV format
    """
    if league_code not in LEAGUE_MAPPING:
        print(f"⚠️ League {league_code} not mapped to API-Football ID")
        return pd.DataFrame()

    league_id = LEAGUE_MAPPING[league_code]
    season_code = f"{str(season_year)[-2:]}{str(season_year + 1)[-2:]}"

    print(f"📥 Fetching {league_code} ({league_id}) season {season_year} from API...")

    # Get all fixtures for the season
    # Note: API-Football uses calendar year for "season" parameter
    # We need to map: 2023-24 season → 2023
    params = {"league": league_id, "season": season_year}

    try:
        fixtures = api_client._make_request("/fixtures", params).get("response", [])

        if not fixtures:
            print(f"  ⚠️ No fixtures found for {league_code} {season_year}")
            return pd.DataFrame()

        # Convert each fixture to CSV row
        rows = []
        for fixture in fixtures:
            row = convert_api_fixture_to_csv_row(fixture, league_code, season_code)
            if row and row["FTR"] is not None:  # Only include completed matches
                rows.append(row)

        if not rows:
            print(f"  ⚠️ No completed matches for {league_code} {season_year}")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        print(f"  ✅ Fetched {len(df)} completed matches")
        return df

    except Exception as e:
        print(f"  ❌ Error fetching {league_code} {season_year}: {e}")
        return pd.DataFrame()


def download_historical_via_api(
    leagues: List[str],
    seasons: List[int],
    api_key: str,
    output_dir: Path = Path("data/raw_api")
) -> None:
    """
    Download historical data using API-Football and save in CSV format

    Args:
        leagues: List of league codes (e.g., ["E0", "SP1"])
        seasons: List of season start years (e.g., [2021, 2022, 2023])
        api_key: API-Football API key
        output_dir: Directory to save CSV files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if api_key == "YOUR_API_KEY_HERE" or not api_key:
        print("❌ Error: API_FOOTBALL_KEY not set!")
        print("   Set environment variable: export API_FOOTBALL_KEY='your-key'")
        return

    # Initialize API client
    client = APIFootballClient(api_key)

    print(f"\n{'='*60}")
    print(f"API-FOOTBALL HISTORICAL DATA DOWNLOAD")
    print(f"{'='*60}")
    print(f"Leagues: {leagues}")
    print(f"Seasons: {min(seasons)}-{max(seasons)}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    total_matches = 0

    for league in leagues:
        for season_year in seasons:
            season_code = f"{str(season_year)[-2:]}{str(season_year + 1)[-2:]}"

            # Fetch data from API
            df = fetch_historical_from_api(client, league, season_year)

            if not df.empty:
                # Save to CSV in same format as football-data.co.uk
                output_file = output_dir / f"{league}_{season_code}.csv"
                df.to_csv(output_file, index=False)
                print(f"  💾 Saved {output_file}")
                total_matches += len(df)

    print(f"\n{'='*60}")
    print(f"✅ Download complete: {total_matches} total matches")
    print(f"   API requests made: {client.request_count}")
    print(f"{'='*60}\n")


# ============================================================================
# HYBRID MODE: CSV + API FALLBACK
# ============================================================================

def download_with_fallback(
    leagues: List[str],
    seasons: List[int],
    use_api: bool = False,
    api_key: Optional[str] = None
) -> None:
    """
    Download historical data with fallback support

    Strategy:
    1. If use_api=True and API key available: Use API-Football
    2. If use_api=False or no API key: Use CSV downloads
    3. If CSV fails: Try API as fallback

    Args:
        leagues: List of league codes
        seasons: List of season start years
        use_api: Whether to use API-Football (default: False)
        api_key: API-Football key (optional, reads from env if not provided)
    """
    api_key = api_key or os.environ.get("API_FOOTBALL_KEY", "")
    has_api_key = api_key and api_key != "YOUR_API_KEY_HERE"

    if use_api and has_api_key:
        print("📡 Using API-Football for data download...")
        download_historical_via_api(leagues, seasons, api_key)
    else:
        print("📂 Using CSV downloads from football-data.co.uk...")
        from download_football_data import download
        try:
            download(leagues, seasons)
            print("✅ CSV download complete")
        except Exception as e:
            print(f"⚠️ CSV download failed: {e}")

            # Fallback to API if available
            if has_api_key:
                print("\n🔄 Falling back to API-Football...")
                download_historical_via_api(leagues, seasons, api_key)
            else:
                print("❌ No API key available for fallback")
                raise


# ============================================================================
# DATA VALIDATION
# ============================================================================

def validate_api_vs_csv_format(api_df: pd.DataFrame, csv_df: pd.DataFrame) -> bool:
    """
    Validate that API-converted data matches CSV format

    Args:
        api_df: DataFrame from API conversion
        csv_df: DataFrame from CSV download

    Returns:
        True if formats match
    """
    required_cols = ["League", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "Season"]

    # Check columns exist
    for col in required_cols:
        if col not in api_df.columns:
            print(f"❌ Missing column in API data: {col}")
            return False
        if col not in csv_df.columns:
            print(f"❌ Missing column in CSV data: {col}")
            return False

    # Check data types
    for col in ["FTHG", "FTAG"]:
        if api_df[col].dtype != csv_df[col].dtype:
            print(f"⚠️ Data type mismatch for {col}: API={api_df[col].dtype}, CSV={csv_df[col].dtype}")

    print("✅ Format validation passed")
    return True


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download football data via API or CSV")
    parser.add_argument("--mode", choices=["api", "csv", "hybrid"], default="csv",
                       help="Download mode: api, csv, or hybrid (csv with api fallback)")
    parser.add_argument("--leagues", nargs="+", default=["E0"],
                       help="League codes (e.g., E0 SP1 D1)")
    parser.add_argument("--start-year", type=int, default=2023,
                       help="Start season year (e.g., 2023 for 2023-24)")
    parser.add_argument("--end-year", type=int, default=datetime.now().year,
                       help="End season year")
    parser.add_argument("--api-key", type=str, default=None,
                       help="API-Football key (or set API_FOOTBALL_KEY env var)")

    args = parser.parse_args()

    seasons = list(range(args.start_year, args.end_year + 1))

    if args.mode == "api":
        api_key = args.api_key or os.environ.get("API_FOOTBALL_KEY")
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            print("❌ API key required for API mode")
            print("   Set with: --api-key YOUR_KEY or export API_FOOTBALL_KEY='YOUR_KEY'")
            exit(1)
        download_historical_via_api(args.leagues, seasons, api_key)

    elif args.mode == "csv":
        from download_football_data import download
        download(args.leagues, seasons)

    else:  # hybrid
        download_with_fallback(args.leagues, seasons, use_api=False, api_key=args.api_key)

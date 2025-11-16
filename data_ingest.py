# data_ingest.py - Fixed version
from __future__ import annotations
import io
import time
from typing import List, Dict, Optional
import pandas as pd
import requests
from pathlib import Path
import numpy as np

from config import (
    RAW_DIR, PROCESSED_DIR, FOOTBALL_DATA_CSV_BASE, SEASONS, LEAGUE_CODES,
    HISTORICAL_PARQUET, FOOTBALL_DATA_ORG_TOKEN, FOOTBALL_DATA_ORG_BASE, log_header
)



def _safe_request(url: str, headers: Optional[Dict[str, str]] = None, max_retries: int = 3, timeout: int = 30) -> requests.Response:
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")

def _download_historic_csv(season: str, league: str) -> pd.DataFrame:
    url = FOOTBALL_DATA_CSV_BASE.format(season=season, league=league)
    resp = _safe_request(url)
    raw = resp.content
    # Handle encoding issues
    df = pd.read_csv(io.BytesIO(raw), encoding='latin1')
    df["Season"] = season
    df["League"] = league
    return df

def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure required columns exist
    for col in ["B365H","B365D","B365A","PSCH","PSCD","PSCA"]:
        if col not in df.columns:
            df[col] = np.nan
    
    # Fix date column
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    
    # Convert odds columns to numeric
    odds_cols = ["B365H","B365D","B365A","PSCH","PSCD","PSCA"]
    for col in odds_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Keep only required columns
    keep_cols = ["League","Date","HomeTeam","AwayTeam","FTHG","FTAG","FTR",
                "B365H","B365D","B365A","PSCH","PSCD","PSCA","Season"]
    available_cols = [c for c in keep_cols if c in df.columns]
    return df[available_cols]

def _load_local_csv(raw_dir: Path, league: str, season: str) -> Optional[pd.DataFrame]:
    """Load CSV from local raw directory (works for both downloaded and API-generated CSVs)"""
    csv_path = raw_dir / f"{league}_{season}.csv"

    if not csv_path.exists():
        return None

    try:
        df = pd.read_csv(csv_path, encoding='latin1')
        df["Season"] = season
        df["League"] = league
        return df
    except Exception as e:
        print(f"  [WARN] Error reading {csv_path}: {e}")
        return None

def build_historical_results(seasons: List[str] = SEASONS, leagues: List[str] = LEAGUE_CODES, force: bool = False) -> Path:
    out_path = HISTORICAL_PARQUET
    if out_path.exists() and not force:
        log_header(f"Historical parquet already exists at {out_path}. Skipping download.")
        return out_path

    frames = []

    # Check for API-generated CSVs first (in data/raw_api)
    api_raw_dir = DATA_DIR / "raw_api"
    use_api_csvs = api_raw_dir.exists() and any(api_raw_dir.glob("*.csv"))

    if use_api_csvs:
        print("📡 Found API-generated CSVs, using those...")
        raw_dir = api_raw_dir
    else:
        print("📂 Using standard CSV files...")
        raw_dir = RAW_DIR

    for s in seasons:
        for lg in leagues:
            try:
                # First, try to load from local CSVs (API or downloaded)
                df = _load_local_csv(raw_dir, lg, s)

                # If not found locally, download from web
                if df is None:
                    print(f"Fetching {lg} {s} from web...")
                    df = _download_historic_csv(s, lg)
                else:
                    print(f"Loading {lg} {s} from local file...")

                df = _standardize_columns(df)
                df = df.dropna(subset=["HomeTeam","AwayTeam","Date"])
                if len(df) > 0:  # Only add if we got data
                    frames.append(df)
            except Exception as e:
                print(f"  [WARN] {lg} {s}: {e}")
                continue
    
    if not frames:
        raise RuntimeError("No historical data could be downloaded. Check network or league/season lists.")
    
    hist = pd.concat(frames, ignore_index=True)
    
    # Create additional columns safely
    hist["HomeGoals"] = pd.to_numeric(hist["FTHG"], errors='coerce').astype("Int64")
    hist["AwayGoals"] = pd.to_numeric(hist["FTAG"], errors='coerce').astype("Int64")
    
    # Create OU25 column
    total_goals = hist["HomeGoals"].fillna(0) + hist["AwayGoals"].fillna(0)
    hist["OU25"] = np.where(total_goals > 2, "O", "U").astype(str)
    
    # Sort and save
    hist = hist.sort_values(["Date","League"]).reset_index(drop=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    hist.to_parquet(out_path, index=False)
    
    log_header(f"Wrote historical results to {out_path} with {len(hist):,} rows.")
    return out_path

def fetch_fixtures(date_from: str, date_to: str, competitions: Optional[List[str]] = None) -> pd.DataFrame:
    if not FOOTBALL_DATA_ORG_TOKEN:
        raise RuntimeError("FOOTBALL_DATA_ORG_TOKEN is not set. Provide token or supply fixtures CSV.")
    
    params = []
    if competitions:
        params.append(f"competitions={','.join(competitions)}")
    params.append(f"dateFrom={date_from}")
    params.append(f"dateTo={date_to}")
    
    url = f"{FOOTBALL_DATA_ORG_BASE}/matches?{'&'.join(params)}"
    headers = {"X-Auth-Token": FOOTBALL_DATA_ORG_TOKEN}
    resp = _safe_request(url, headers=headers)
    js = resp.json()
    
    matches = js.get("matches", [])
    rows = []
    for m in matches:
        rows.append({
            "utcDate": m.get("utcDate"),
            "competition": m.get("competition", {}).get("code") or m.get("competition", {}).get("name"),
            "HomeTeam": m.get("homeTeam", {}).get("name"),
            "AwayTeam": m.get("awayTeam", {}).get("name"),
            "status": m.get("status"),
            "id": m.get("id"),
        })
    
    df = pd.DataFrame(rows)
    if len(df) == 0:
        return df
    
    df["Date"] = pd.to_datetime(df["utcDate"]).dt.tz_convert("Europe/London").dt.date
    return df[["Date","competition","HomeTeam","AwayTeam","status","id"]]

if __name__ == "__main__":
    build_historical_results()
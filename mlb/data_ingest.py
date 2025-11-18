#!/usr/bin/env python3
# MLB Data Ingestion
import pandas as pd
from pathlib import Path
from config import RAW_DIR, PROCESSED_DIR, MLB_TEAMS, log_header

class MLBDataIngestor:
    def __init__(self):
        self.raw_dir = RAW_DIR
        self.processed_dir = PROCESSED_DIR
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def load_raw_files(self):
        files = list(self.raw_dir.glob("mlb_*.csv"))
        if not files:
            return pd.DataFrame()
        
        dfs = []
        for file in sorted(files):
            try:
                df = pd.read_csv(file)
                dfs.append(df)
            except:
                pass
        
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    
    def clean_data(self, df):
        df = df.drop_duplicates(subset=['season', 'date', 'home_team', 'away_team'])
        valid_teams = set(MLB_TEAMS.keys())
        df = df[df['home_team'].isin(valid_teams) & df['away_team'].isin(valid_teams)]
        return df.sort_values(['season', 'date']).reset_index(drop=True)
    
    def run(self):
        log_header("MLB Data Ingestion")
        df = self.load_raw_files()
        if df.empty:
            print("⚠️  No data found")
            return
        
        df = self.clean_data(df)
        output = self.processed_dir / "historical_games.parquet"
        df.to_parquet(output, index=False)
        print(f"✅ Saved {len(df)} games to {output}")

if __name__ == "__main__":
    MLBDataIngestor().run()

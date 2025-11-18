#!/usr/bin/env python3
# MLB Fixture Downloader - Simplified version
import requests
import pandas as pd
from datetime import datetime, timedelta
from config import BASE_DIR, MLB_STATS_API_BASE, log_header
from progress_utils import Timer

class MLBFixtureDownloader:
    def __init__(self):
        self.session = requests.Session()
    
    def download_mlb_upcoming(self, days=7):
        start = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        url = f"{MLB_STATS_API_BASE}/schedule"
        params = {'sportId': 1, 'startDate': start, 'endDate': end, 'gameType': 'R'}
        
        try:
            r = self.session.get(url, params=params, timeout=30)
            data = r.json()
            
            games = []
            for date_entry in data.get('dates', []):
                for game in date_entry.get('games', []):
                    teams = game.get('teams', {})
                    games.append({
                        'date': game.get('officialDate'),
                        'home_team': teams.get('home', {}).get('team', {}).get('abbreviation'),
                        'away_team': teams.get('away', {}).get('team', {}).get('abbreviation'),
                    })
            
            return pd.DataFrame(games)
        except:
            return pd.DataFrame()
    
    def download_and_save(self):
        df = self.download_mlb_upcoming()
        if not df.empty:
            df.to_csv(BASE_DIR / "upcoming_fixtures.csv", index=False)
            print(f"✅ Saved {len(df)} fixtures")

def main():
    log_header("MLB Fixtures Download")
    MLBFixtureDownloader().download_and_save()

if __name__ == "__main__":
    main()

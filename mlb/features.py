#!/usr/bin/env python3
# MLB Feature Engineering (Simplified)
import pandas as pd
import numpy as np
from config import BALLPARK_FACTORS

class MLBFeatureEngineer:
    def __init__(self, df):
        self.df = df.copy()
        self.elo_ratings = {}
    
    def create_features(self):
        features = []
        
        for idx, row in self.df.iterrows():
            game_features = {
                'season': row['season'],
                'date': row['date'],
                'home_team': row['home_team'],
                'away_team': row['away_team'],
            }
            
            # Ballpark factors
            game_features['home_park_factor'] = BALLPARK_FACTORS.get(row['home_team'], 1.0)
            
            # Targets (if available)
            if pd.notna(row.get('home_score')) and pd.notna(row.get('away_score')):
                game_features['home_score'] = row['home_score']
                game_features['away_score'] = row['away_score']
                game_features['total_runs'] = row['home_score'] + row['away_score']
                game_features['result'] = 'H' if row['home_score'] > row['away_score'] else 'A'
            
            features.append(game_features)
        
        return pd.DataFrame(features)

def build_features_from_raw(input_path, output_path=None):
    from config import PROCESSED_DIR
    df = pd.read_parquet(input_path)
    engineer = MLBFeatureEngineer(df)
    features_df = engineer.create_features()
    
    if output_path is None:
        output_path = PROCESSED_DIR / "features.parquet"
    
    features_df.to_parquet(output_path, index=False)
    print(f"✅ Created features: {len(features_df)} games")
    return features_df

if __name__ == "__main__":
    from config import PROCESSED_DIR
    build_features_from_raw(PROCESSED_DIR / "historical_games.parquet")

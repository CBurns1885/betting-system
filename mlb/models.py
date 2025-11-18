#!/usr/bin/env python3
# MLB Models (Simplified)
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from config import MODEL_ARTIFACTS_DIR, PROCESSED_DIR, PRIMARY_MARKETS, RANDOM_SEED, log_header

class MLBModelTrainer:
    def __init__(self, features_df):
        self.features_df = features_df
        self.models = {}
    
    def train_market(self, market):
        df = self.features_df[self.features_df['result'].notna()].copy()
        
        if market == "MONEYLINE":
            df['target'] = (df['result'] == 'H').astype(int)
        else:
            return None
        
        feature_cols = ['home_park_factor']
        X = df[feature_cols].fillna(0)
        y = df['target']
        
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=RANDOM_SEED)
        
        model = RandomForestClassifier(n_estimators=100, random_state=RANDOM_SEED)
        model.fit(X_train, y_train)
        
        acc = model.score(X_val, y_val)
        print(f"  {market}: {acc:.3f} accuracy")
        
        self.models[market] = model
        return model
    
    def train_all_markets(self):
        log_header("Training MLB Models")
        for market in PRIMARY_MARKETS[:1]:  # Just moneyline for now
            self.train_market(market)
        return self.models
    
    def save_models(self):
        MODEL_ARTIFACTS_DIR.mkdir(exist_ok=True)
        for name, model in self.models.items():
            path = MODEL_ARTIFACTS_DIR / f"{name}.pkl"
            joblib.dump(model, path)
        print("✅ Models saved")

def train_mlb_models():
    features_df = pd.read_parquet(PROCESSED_DIR / "features.parquet")
    trainer = MLBModelTrainer(features_df)
    trainer.train_all_markets()
    trainer.save_models()

if __name__ == "__main__":
    train_mlb_models()

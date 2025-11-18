#!/usr/bin/env python3
# MLB Predictions (Simplified)
import pandas as pd
import joblib
from config import BASE_DIR, MODEL_ARTIFACTS_DIR, OUTPUT_DIR, log_header

def predict_upcoming_games():
    log_header("MLB Predictions")
    
    fixtures = pd.read_csv(BASE_DIR / "upcoming_fixtures.csv")
    
    # Load model
    model = joblib.load(MODEL_ARTIFACTS_DIR / "MONEYLINE.pkl")
    
    # Create simple features
    fixtures['home_park_factor'] = 1.0  # Simplified
    
    # Predict
    X = fixtures[['home_park_factor']]
    probs = model.predict_proba(X)
    
    fixtures['home_win_prob'] = probs[:, 1]
    fixtures['away_win_prob'] = probs[:, 0]
    
    output = OUTPUT_DIR / "weekly_predictions.csv"
    fixtures.to_csv(output, index=False)
    print(f"✅ Saved predictions: {output}")

if __name__ == "__main__":
    predict_upcoming_games()

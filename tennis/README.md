# Tennis Betting System

Machine learning betting system for ATP and WTA tennis matches.

## Key Features

- **Surface-Specific ELO**: Separate ELO ratings for Clay, Hard, Grass, and Carpet surfaces
- **Head-to-Head Analysis**: 1v1 matchup history is critical in tennis
- **Player Rankings**: ATP/WTA ranking-based features
- **Tournament Tier**: Grand Slams vs Masters vs ATP 500/250
- **Match Format**: Best of 3 vs Best of 5 sets
- **Ensemble Models**: Random Forest, XGBoost, LightGBM, Gradient Boosting, Logistic Regression

## Markets Supported

- **Match Winner**: Moneyline (H2H winner)
- **Set Betting**: Exact score in sets (2-0, 2-1, etc.)
- **Total Games**: Over/Under total games in match
- **First Set**: Who wins the first set

## Data Sources

- **Jeff Sackmann GitHub**: Best free tennis data (ATP/WTA match history)
- **Tennis Abstract**: Comprehensive match statistics
- **The Odds API**: Live betting odds

## Setup

```bash
cd tennis
pip install -r requirements.txt
```

## Usage

### 1. Download Historical Data

```bash
python download_tennis_data.py --start 2018 --end 2024 --tour both
```

### 2. Engineer Features

```bash
python features.py
```

### 3. Train Models

```bash
python models.py
```

### 4. Download Upcoming Matches & Predict

```bash
python fixture_downloader.py --odds-api-key YOUR_KEY
python predict.py --market MATCH_WINNER
```

### 5. Backtest Strategy

```bash
python backtest.py --bankroll 1000 --train-size 500 --test-size 100
```

## Why Tennis is Great for Betting

1. **1v1 Simplicity**: No team dynamics, just individual performance
2. **Surface Importance**: Clay specialists vs hard court players creates predictable patterns
3. **H2H Matters**: Player matchups are highly informative
4. **Frequent Matches**: Weekly tournaments provide consistent data
5. **Ranking System**: Clear, quantifiable player strength indicators

## Surface Characteristics

- **Clay**: Slow, high bounce - favors defense and consistency (Nadal!)
- **Hard**: Medium-fast - balanced, most common surface
- **Grass**: Fast, low bounce - favors serve & volley (Wimbledon)
- **Carpet**: Fast, indoor - increasingly rare

## Directory Structure

```
tennis/
├── config.py                    # Configuration
├── download_tennis_data.py      # Historical data downloader
├── fixture_downloader.py        # Upcoming match downloader
├── features.py                  # Feature engineering (ELO, H2H)
├── models.py                    # ML model training
├── predict.py                   # Make predictions
├── backtest.py                  # Strategy backtesting
├── progress_utils.py            # Utility functions
├── requirements.txt             # Python dependencies
├── data/
│   ├── raw/                     # Raw match data
│   ├── interim/                 # Intermediate processed data
│   └── processed/               # Final features
├── models/                      # Trained model files
└── outputs/                     # Predictions and results
```

## Notes

- Surface-specific ELO is critical - don't ignore it!
- Grand Slam matches (best of 5) behave differently than regular tour matches (best of 3)
- Player fatigue matters in tournaments (multiple matches per week)
- Weather affects outdoor matches (wind, temperature)

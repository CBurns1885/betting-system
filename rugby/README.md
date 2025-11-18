# Rugby Union Betting System

Machine learning betting system for international and club rugby union matches.

## Key Features

- **Home Advantage Modeling**: ~15% scoring boost for home teams (significant in rugby!)
- **3-Way Outcomes**: Handles Home/Draw/Away (draws are common in rugby)
- **ELO Ratings**: Team strength ratings with point differential adjustments
- **Head-to-Head Records**: Historical matchup analysis
- **Recent Form**: Last 5 matches performance
- **Competition Tier**: World Cup, Six Nations, Rugby Championship, club competitions
- **Altitude Advantage**: South African teams at high veldt
- **Ensemble Models**: Random Forest, XGBoost, LightGBM, Gradient Boosting, Logistic Regression

## Markets Supported

- **Match Winner**: 1X2 (Home/Draw/Away)
- **Handicap**: Points handicap betting
- **Total Points**: Over/Under total points
- **First Half**: First half result

## Rugby-Specific Factors

### Home Advantage
Rugby has one of the strongest home advantages in sports (~15% boost):
- Crowd intimidation
- Travel fatigue for away teams
- Altitude (South Africa)
- Weather conditions

### Draws
Unlike many sports, draws are fairly common in rugby:
- No overtime in regular season matches
- Both teams get 2 competition points
- Important to model as separate outcome

### Scoring Patterns
- **Try**: 5 points (+ 2 for conversion)
- **Penalty**: 3 points
- **Drop Goal**: 3 points
- **Average**: ~45 points per match, ~4.5 tries

### Competition Structure
- **International**: Six Nations (Feb-Mar), Rugby Championship (Aug-Oct), Autumn Tests (Nov)
- **Club**: European Champions Cup, United Rugby Championship, Premiership, Top 14, Super Rugby

## Setup

```bash
cd rugby
pip install -r requirements.txt
```

## Usage

### 1. Download Historical Data

```bash
# Create sample dataset for testing
python download_rugby_data.py --sample

# Or download real data (requires data sources)
python download_rugby_data.py --start 2018 --end 2024
```

### 2. Engineer Features

```bash
python features.py
```

### 3. Train Models

```bash
python models.py
```

### 4. Make Predictions

```bash
python predict.py --market MATCH_WINNER
```

### 5. Backtest Strategy

```bash
python backtest.py
```

## Tier 1 Nations

The strongest rugby nations (in approximate current order):
1. **New Zealand** (All Blacks) - Most successful team historically
2. **Ireland** - Currently #1 ranked (as of 2024)
3. **South Africa** (Springboks) - Physical, forward-dominant
4. **France** - Flair and unpredictability
5. **England** - Large player pool
6. **Wales** - Strong Six Nations record
7. **Scotland** - Improving rapidly
8. **Australia** (Wallabies) - Traditional power, declining
9. **Argentina** (Pumas) - Aggressive pack play
10. **Italy** - Six Nations participant
11. **Fiji** - Sevens specialists
12. **Japan** - Emerging force

## Major Competitions

### International
- **Six Nations**: Annual European tournament (England, Ireland, Scotland, Wales, France, Italy)
- **Rugby Championship**: Southern Hemisphere (New Zealand, South Africa, Australia, Argentina)
- **Autumn Internationals**: November test matches
- **Rugby World Cup**: Every 4 years (most prestigious)

### Club
- **European Champions Cup**: Top European club competition
- **United Rugby Championship**: Irish, Welsh, Scottish, Italian, South African teams
- **English Premiership**: Top English league
- **Top 14**: French league (very competitive)
- **Super Rugby**: Australia, New Zealand, Pacific Islands

## Why Rugby is Challenging for Betting

1. **High Variance**: Upsets are common
2. **Injuries**: Physical sport, key player absences matter hugely
3. **Weather**: Rain = lower scoring, more kicking
4. **Referee Impact**: Different interpretations of rules
5. **Tournament Fatigue**: Short turnarounds in World Cups

## Directory Structure

```
rugby/
├── config.py                    # Configuration (teams, competitions)
├── download_rugby_data.py       # Historical data downloader
├── features.py                  # Feature engineering (ELO, H2H, form)
├── models.py                    # ML model training (3-way classification)
├── predict.py                   # Match predictions
├── backtest.py                  # Strategy backtesting
├── progress_utils.py            # Utility functions
├── requirements.txt             # Python dependencies
├── data/
│   ├── raw/                     # Raw match data
│   └── processed/               # Features
├── models/                      # Trained models
└── outputs/                     # Predictions
```

## Notes

- Home advantage is CRITICAL in rugby - don't underestimate it
- Model draws separately (don't just use binary classification)
- Weather significantly impacts scoring
- World Cup matches are different from regular tests (pressure, fatigue)
- Southern Hemisphere teams often struggle in Northern Hemisphere winter

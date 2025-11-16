# 🏈 NFL Betting System

A complete machine learning system for predicting NFL games and finding value bets across multiple markets.

## 🚀 QUICK START

### First Time Setup:

1. **Install Python 3.8+** (if not already installed)

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API keys** (optional but recommended):
   ```bash
   export THE_ODDS_API_KEY="your_key_here"
   # Get free key at: https://the-odds-api.com/
   ```

4. **Run the system:**
   ```bash
   python run_weekly.py
   ```

### Weekly Usage:

1. **Run once per week** (recommended Tuesday/Wednesday after Monday Night Football)
2. **Choose mode:**
   - Full mode: `python run_weekly.py` (~30-60 min first run, ~10 min after)
   - Fast mode: `python run_weekly.py --fixtures-only` (~2 min)
   - Retrain: `python run_weekly.py --retrain` (forces model retraining)
3. **Check outputs/** folder for predictions and reports

---

## 📊 OUTPUT FILES

The system generates these files in the `outputs/YYYY-MM-DD/` folder:

### Main Predictions:
- **weekly_predictions.csv** - All predictions with probabilities
- **weekly_predictions.xlsx** - Excel version
- **top_picks.csv** - Highest confidence picks

### Prediction Columns:
- `moneyline_home_prob` - Probability of home team winning
- `moneyline_away_prob` - Probability of away team winning
- `spread_cover_prob` - Probability of covering the spread
- `total_over_prob` - Probability of going over the total
- `total_under_prob` - Probability of going under the total
- Confidence scores and picks for each market

---

## 🎯 MARKETS COVERED

The system predicts probabilities for three main NFL betting markets:

1. **Moneyline** - Win/Loss (straight up)
2. **Spread** - Point spread coverage
3. **Totals** - Over/Under total points scored

---

## 📁 FILE STRUCTURE

```
nfl/
├── run_weekly.py              # Main weekly runner (7-step pipeline)
├── config.py                  # Configuration (teams, seasons, API keys)
│
├── Data Pipeline:
│   ├── download_nfl_data.py      # Download historical games (ESPN API)
│   ├── fixture_downloader.py     # Download upcoming games & odds
│   └── data_ingest.py            # Combine and clean raw data
│
├── Feature Engineering:
│   └── features.py               # Create NFL-specific features
│
├── Machine Learning:
│   ├── models.py                 # Train ensemble models
│   └── predict.py                # Generate predictions
│
└── Utilities:
    ├── progress_utils.py         # Progress tracking
    └── requirements.txt          # Python dependencies
```

---

## 🔧 DATA SOURCES

### Historical Game Data:
- **ESPN API** (primary, free)
  - Full game stats, scores, team info
  - Covers all NFL seasons 2018-present

- **Pro Football Reference** (fallback)
  - Comprehensive historical data
  - Requires web scraping

### Betting Odds:
- **The Odds API** (recommended)
  - Real-time betting lines
  - Free tier: 500 requests/month
  - Sign up: https://the-odds-api.com/

- **ESPN Odds** (backup)
  - Basic spread and total lines
  - Included with game data

---

## 🧠 FEATURES

The system creates 50+ predictive features for each game:

### Team Performance:
- Points scored/allowed (rolling averages)
- Win percentage (last 3, 5, 10 games)
- Offensive/defensive efficiency metrics

### Advanced Stats:
- Total yards, passing yards, rushing yards
- Turnovers and turnover differential
- Third down conversion %
- Red zone efficiency
- Time of possession

### Situational:
- Home field advantage
- Divisional game indicator
- Conference game indicator
- Days of rest
- Head-to-head history

### ELO Ratings:
- Team strength ratings
- Updated after each game
- Margin-adjusted

---

## 🤖 MODELS

The system uses an ensemble of machine learning models:

1. **Random Forest** - Robust baseline
2. **XGBoost** - Gradient boosting (high accuracy)
3. **LightGBM** - Fast gradient boosting
4. **Gradient Boosting** - Classic ensemble method
5. **Logistic Regression** - Linear baseline

Predictions are averaged across all models for better stability.

### Model Features:
- Probability calibration (isotonic regression)
- Feature importance tracking
- Cross-validation for reliability

---

## 📈 WORKFLOW

### Step-by-Step Pipeline:

**STEP 1: Download Historical Data**
- Fetches NFL games from ESPN API
- Covers configured seasons (default: last 5 years)
- Saves to `data/raw/`

**STEP 2: Download Upcoming Fixtures**
- Gets current week's games
- Fetches betting odds (if API key provided)
- Saves to `upcoming_fixtures.csv`

**STEP 3: Ingest Data**
- Combines all raw CSV files
- Cleans and validates data
- Saves to `data/processed/historical_games.parquet`

**STEP 4: Build Features**
- Creates 50+ features per game
- Calculates ELO ratings
- Computes rolling averages
- Saves to `data/processed/features.parquet`

**STEP 5: Train Models**
- Trains ensemble of 5 models
- Calibrates probabilities
- Saves to `models/*.pkl`
- Skips if models exist (use --retrain to override)

**STEP 6: Generate Predictions**
- Loads trained models
- Creates features for upcoming games
- Generates probabilities for all markets
- Saves to `outputs/YYYY-MM-DD/weekly_predictions.csv`

**STEP 7: Create Reports**
- Identifies high confidence picks
- Creates top picks report
- Displays summary statistics

---

## ⚡ USAGE MODES

### Full Mode (First Run):
```bash
python run_weekly.py
```
Downloads everything, trains models, generates predictions (~30-60 min)

### Fast Mode (Weekly Updates):
```bash
python run_weekly.py --fixtures-only
```
Only downloads fixtures and predicts with existing models (~2 min)

### Retrain Models:
```bash
python run_weekly.py --retrain
```
Forces model retraining with latest data (~20-30 min)

### Skip Historical Download:
```bash
python run_weekly.py --skip-download
```
Uses existing historical data, good for testing

---

## 🔑 API KEYS (Optional)

### The Odds API (Recommended):
```bash
export THE_ODDS_API_KEY="your_key_here"
```
- Free tier: 500 requests/month
- Provides accurate betting lines
- Sign up: https://the-odds-api.com/

### ESPN API:
- No key required
- Free tier limitations apply
- Automatically used

---

## 📊 INTERPRETING PREDICTIONS

### Confidence Levels:
- **> 70%** - High confidence (strong picks)
- **60-70%** - Medium confidence (good picks)
- **50-60%** - Low confidence (toss-up)

### Using Probabilities:
Compare model probabilities with implied odds:

```
Implied Probability = 1 / Decimal Odds
Value = Model Probability - Implied Probability

Example:
- Model: 65% home team wins
- Odds: -150 (implied ~60%)
- Value: +5% (good bet!)
```

### Top Picks:
The system automatically identifies games with:
- Highest confidence (>65%)
- Largest edge vs market odds
- Best risk/reward ratio

---

## 🧪 CUSTOMIZATION

### Change Seasons:
Edit `config.py`:
```python
SEASON_START_YEAR = 2018  # Start from 2018 season
```

### Add Features:
Edit `features.py` and add to `create_features()` method

### Adjust Model Parameters:
Edit `models.py` and modify hyperparameters

### Change Markets:
Edit `config.py` and add to `PRIMARY_MARKETS`

---

## 📝 TROUBLESHOOTING

### "No fixtures found"
- Check if NFL season is active
- Verify API keys (if using The Odds API)
- Try running during season (Sept-Feb)

### "Module not found"
```bash
pip install -r requirements.txt
```

### "No models found"
Run full pipeline first:
```bash
python run_weekly.py
```

### Slow first run
- First run downloads 5+ years of data
- Trains multiple models on thousands of games
- Subsequent runs are much faster (~2-10 min)

### Want faster runs?
- Use `--fixtures-only` mode for weekly updates
- Reduce `SEASON_START_YEAR` in config.py
- Use `--skip-download` to skip data refresh

---

## 🎓 BEST PRACTICES

### When to Run:
- **Tuesday/Wednesday** - After Monday Night Football
- Gives time for injury reports to settle
- Lines are usually posted by Wednesday

### Model Updates:
- **Retrain every 4-6 weeks** during season
- More frequent during playoffs
- Update after major roster changes

### Bankroll Management:
- **Never bet more than 1-3% per pick**
- Track all bets (use accuracy tracker)
- Focus on high confidence picks (>65%)

### Value Betting:
- Don't just bet favorites
- Look for edge vs market odds
- Shop lines across multiple books

---

## 📚 ADDITIONAL FEATURES TO ADD

Future enhancements (not yet implemented):

- **Player Props** - QB passing yards, RB rushing yards
- **Live Betting** - In-game probability updates
- **Weather Integration** - Impact of weather on totals
- **Injury Reports** - Adjust for key player absences
- **Referee Stats** - Some refs favor certain styles
- **Parlay Builder** - Correlated parlay finder
- **Accuracy Tracking** - Track and improve predictions
- **Backtesting** - Test strategies on historical data

---

## ⚠️ DISCLAIMER

This is a predictive model for educational and entertainment purposes.

- **Past performance does not guarantee future results**
- **Gambling involves risk of loss**
- **Bet responsibly and within your means**
- **This is NOT financial advice**
- **Always verify predictions against your own research**

Gambling can be addictive. If you or someone you know has a gambling problem, call 1-800-GAMBLER.

---

## 📞 SUPPORT

For issues or questions:
1. Check the troubleshooting section above
2. Review the example output files
3. Verify all dependencies are installed
4. Check API keys are set correctly

---

## 📜 LICENSE

This is a personal betting prediction system. Use at your own risk.

---

**Last Updated:** November 2025
**Version:** 1.0 - Initial Release
**Sport:** NFL (American Football)

---

## 🏈 EXAMPLE OUTPUT

```
Game: Kansas City Chiefs @ Buffalo Bills
Date: 2025-11-17

Moneyline:
  Home Win (BUF): 58.3%  ✓ PICK
  Away Win (KC):  41.7%

Spread (BUF -3.5):
  Cover:    54.2%  ✓ PICK
  No Cover: 45.8%

Total (O/U 47.5):
  Over:  62.1%  ✓ PICK
  Under: 37.9%

Confidence: 62.1% (MEDIUM)
```

---

**Good luck and bet responsibly! 🏈🎯**

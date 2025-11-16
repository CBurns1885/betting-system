# 🏈 NFL Betting System - Quick Start Guide

## Installation (5 minutes)

1. **Navigate to NFL directory:**
   ```bash
   cd nfl/
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Optional: Set API key for betting odds:**
   ```bash
   export THE_ODDS_API_KEY="your_key_here"
   ```
   Get a free key at: https://the-odds-api.com/

## First Run (30-60 minutes)

Run the complete pipeline to download data, train models, and generate predictions:

```bash
python run_weekly.py
```

This will:
1. Download 5 years of NFL historical data
2. Download upcoming week's games
3. Process and clean all data
4. Build 50+ predictive features
5. Train 5 machine learning models
6. Generate predictions for all upcoming games
7. Create analysis reports

## Weekly Usage (2-10 minutes)

After the first run, use fast mode for weekly updates:

```bash
python run_weekly.py --fixtures-only
```

This only downloads new fixtures and generates predictions using existing models (~2 minutes).

## View Results

Check the `outputs/YYYY-MM-DD/` folder for:
- `weekly_predictions.csv` - All predictions
- `weekly_predictions.xlsx` - Excel version
- `top_picks.csv` - Highest confidence picks

## Example Output

```
Game: Kansas City Chiefs @ Buffalo Bills

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

## Optional: Generate Advanced Reports

### Spread Analysis:
```bash
python spread_analyzer.py
```
Creates detailed spread betting report with key numbers analysis.

### Parlay Builder:
```bash
python parlay_builder.py
```
Builds optimized 3-6 leg parlays from high confidence picks.

### Accuracy Tracking:
```bash
# Log predictions
python accuracy_tracker.py --log outputs/*/weekly_predictions.csv --week 10 --season 2025

# Update with results (after games finish)
python accuracy_tracker.py --update results.csv

# Generate report
python accuracy_tracker.py --report
```

## Tips

1. **Best time to run:** Tuesday or Wednesday after Monday Night Football
2. **Retrain models:** Every 4-6 weeks with `--retrain` flag
3. **High confidence picks:** Focus on picks with >65% confidence
4. **Bet responsibly:** Never bet more than 1-3% of bankroll per pick

## Troubleshooting

**"No fixtures found"**
- Check if NFL season is active (Sept-Feb)
- Verify API key if using The Odds API

**"No models found"**
- Run full pipeline first: `python run_weekly.py`

**Slow performance**
- Use `--fixtures-only` for weekly updates
- Reduce `SEASON_START_YEAR` in config.py

## Need Help?

See full documentation: `README.md`

---

**Good luck and bet responsibly! 🏈**

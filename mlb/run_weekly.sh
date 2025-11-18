#!/bin/bash
# run_weekly.sh - Weekly MLB Betting System Runner
# Run this script 2-3 times per week during MLB season (April-October)
# to get predictions for upcoming games

set -e

echo "⚾ MLB WEEKLY BETTING PREDICTIONS"
echo "================================="
echo "📅 Run Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

if [ ! -f "config.py" ]; then
    echo "❌ Error: Must run from mlb/ directory"
    exit 1
fi

# Create dated output directory
OUTPUT_DATE=$(date '+%Y-%m-%d')
mkdir -p "outputs/${OUTPUT_DATE}"

# Step 1: Update historical data (only recent games)
echo "📥 Step 1/4: Updating MLB historical data..."
CURRENT_YEAR=$(date '+%Y')
python download_mlb_data.py --start-year $((CURRENT_YEAR - 1)) --end-year ${CURRENT_YEAR} || {
    echo "⚠️  Data download failed, using existing data..."
}

# Step 2: Retrain models weekly
MODEL_AGE=$(find models/ -name "*.pkl" -mtime +7 2>/dev/null | wc -l)
if [ "$MODEL_AGE" -gt 0 ] || [ ! -d "models" ] || [ -z "$(ls -A models 2>/dev/null)" ]; then
    echo ""
    echo "🔧 Step 2/4: Retraining models with latest data..."
    python features.py
    python models.py
else
    echo ""
    echo "🔧 Step 2/4: Using cached models (less than 7 days old)..."
fi

# Step 3: Download upcoming games (next 7 days)
echo ""
echo "🔮 Step 3/4: Downloading upcoming MLB games..."
python fixture_downloader.py --days 7

# Step 4: Generate predictions
echo ""
echo "🎯 Step 4/4: Generating predictions for all markets..."
python predict.py --output-dir "outputs/${OUTPUT_DATE}"

# Display summary
echo ""
echo "=" | head -c 60 | tr -d '\n' && echo ""
echo "✅ WEEKLY RUN COMPLETE!"
echo "=" | head -c 60 | tr -d '\n' && echo ""
echo ""
echo "📁 Results saved to: outputs/${OUTPUT_DATE}/"
echo ""

# Show summary if predictions exist
PRED_FILE="outputs/${OUTPUT_DATE}/mlb_predictions.csv"
if [ -f "$PRED_FILE" ]; then
    echo "⚾ THIS WEEK'S MLB PREDICTIONS:"
    echo "------------------------------"
    head -6 "$PRED_FILE" | tail -5 || echo "See $PRED_FILE for all predictions"
    echo ""
    TOTAL_GAMES=$(tail -n +2 "$PRED_FILE" | wc -l)
    echo "Total games: ${TOTAL_GAMES}"
    echo ""
    echo "💡 MLB plays 162 games/season - lots of betting opportunities!"
    echo "🎯 Focus on games with strong ballpark factor edges"
fi

echo ""
echo "📊 Markets: Moneyline, Run Line (±1.5), Totals, First 5 Innings"
echo ""

exit 0

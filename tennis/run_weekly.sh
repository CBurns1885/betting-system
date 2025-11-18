#!/bin/bash
# run_weekly.sh - Weekly Tennis Betting System Runner
# Run this script weekly during tennis season (year-round!)
# ATP/WTA tournaments happen almost every week

set -e

echo "🎾 TENNIS WEEKLY BETTING PREDICTIONS"
echo "===================================="
echo "📅 Run Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

if [ ! -f "config.py" ]; then
    echo "❌ Error: Must run from tennis/ directory"
    exit 1
fi

# Create dated output directory
OUTPUT_DATE=$(date '+%Y-%m-%d')
mkdir -p "outputs/${OUTPUT_DATE}"

# Step 1: Update historical data (last 2 years is sufficient)
echo "📥 Step 1/4: Updating tennis historical data..."
CURRENT_YEAR=$(date '+%Y')
python download_tennis_data.py --start $((CURRENT_YEAR - 1)) --end ${CURRENT_YEAR} || {
    echo "⚠️  Data download failed, using existing data..."
}

# Step 2: Retrain models weekly (important for tennis - form changes quickly!)
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

# Step 3: Download upcoming matches (next 7 days)
echo ""
echo "🔮 Step 3/4: Downloading upcoming tennis matches..."
python fixture_downloader.py

# Step 4: Generate predictions
echo ""
echo "🎯 Step 4/4: Generating predictions..."
python predict.py --market MATCH_WINNER --output-dir "outputs/${OUTPUT_DATE}"

# Display summary
echo ""
echo "=" | head -c 60 | tr -d '\n' && echo ""
echo "✅ WEEKLY RUN COMPLETE!"
echo "=" | head -c 60 | tr -d '\n' && echo ""
echo ""
echo "📁 Results saved to: outputs/${OUTPUT_DATE}/"
echo ""

# Show summary if predictions exist
PRED_FILE="outputs/${OUTPUT_DATE}/tennis_predictions_match_winner.csv"
VALUE_FILE="outputs/${OUTPUT_DATE}/tennis_value_bets.csv"

if [ -f "$PRED_FILE" ]; then
    echo "🎾 THIS WEEK'S TENNIS PREDICTIONS:"
    echo "---------------------------------"
    head -6 "$PRED_FILE" | tail -5 || echo "See $PRED_FILE for all predictions"
    echo ""
    TOTAL_MATCHES=$(tail -n +2 "$PRED_FILE" | wc -l)
    echo "Total matches: ${TOTAL_MATCHES}"
fi

if [ -f "$VALUE_FILE" ]; then
    echo ""
    echo "💰 VALUE BETS IDENTIFIED:"
    echo "------------------------"
    VALUE_COUNT=$(tail -n +2 "$VALUE_FILE" | wc -l)
    echo "Found ${VALUE_COUNT} value betting opportunities"
    echo "Check $VALUE_FILE for details"
fi

echo ""
echo "💡 TENNIS BETTING TIPS:"
echo "  - Surface matters HUGELY (clay vs hard vs grass)"
echo "  - Check head-to-head records (1v1 matchups)"
echo "  - Best of 5 (Grand Slams) vs Best of 3 (regular tour)"
echo "  - Recent form changes quickly in tennis"
echo ""
echo "📊 Markets: Match Winner, Set Betting, Total Games, First Set"
echo ""

exit 0

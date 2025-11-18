#!/bin/bash
# run_weekly.sh - Weekly Rugby Union Betting System Runner
# Run this script weekly during rugby season
# Six Nations (Feb-Mar), Rugby Championship (Aug-Oct), Autumn Tests (Nov)

set -e

echo "🏉 RUGBY UNION WEEKLY BETTING PREDICTIONS"
echo "=========================================="
echo "📅 Run Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

if [ ! -f "config.py" ]; then
    echo "❌ Error: Must run from rugby/ directory"
    exit 1
fi

# Create dated output directory
OUTPUT_DATE=$(date '+%Y-%m-%d')
mkdir -p "outputs/${OUTPUT_DATE}"

# Step 1: Update historical data
echo "📥 Step 1/4: Updating rugby historical data..."
CURRENT_YEAR=$(date '+%Y')
python download_rugby_data.py --start $((CURRENT_YEAR - 1)) --end ${CURRENT_YEAR} --sample || {
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

# Step 3: Download/create upcoming matches
echo ""
echo "🔮 Step 3/4: Loading upcoming rugby matches..."
echo "  (Note: Using sample data - configure real data sources in config.py)"

# Step 4: Generate predictions
echo ""
echo "🎯 Step 4/4: Generating predictions for 3-way outcomes..."
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
PRED_FILE="outputs/${OUTPUT_DATE}/rugby_predictions_match_winner.csv"

if [ -f "$PRED_FILE" ]; then
    echo "🏉 THIS WEEK'S RUGBY PREDICTIONS:"
    echo "--------------------------------"
    head -6 "$PRED_FILE" | tail -5 || echo "See $PRED_FILE for all predictions"
    echo ""
    TOTAL_MATCHES=$(tail -n +2 "$PRED_FILE" | wc -l)
    echo "Total matches: ${TOTAL_MATCHES}"
fi

echo ""
echo "💡 RUGBY BETTING TIPS:"
echo "  - HOME ADVANTAGE IS HUGE (~15% boost in scoring)"
echo "  - Draws are fairly common - don't ignore them!"
echo "  - Weather matters (rain = lower scoring, more kicks)"
echo "  - Tier 1 vs Tier 2 matchups are usually one-sided"
echo "  - Tournament fatigue in World Cups"
echo ""
echo "🏆 MAJOR COMPETITIONS:"
echo "  - Six Nations (Feb-Mar): Europe's best"
echo "  - Rugby Championship (Aug-Oct): Southern Hemisphere"
echo "  - Autumn Internationals (Nov): North vs South"
echo "  - Rugby World Cup (every 4 years)"
echo ""
echo "📊 Markets: Match Winner (1X2), Handicap, Total Points, First Half"
echo ""

exit 0

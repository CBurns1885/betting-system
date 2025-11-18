#!/bin/bash
# run_weekly.sh - Weekly NFL Betting System Runner
# Run this script once per week (e.g., via cron on Tuesday/Wednesday)
# to get predictions for the upcoming NFL games

set -e  # Exit on error

echo "🏈 NFL WEEKLY BETTING PREDICTIONS"
echo "================================="
echo "📅 Run Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Check if we're in the nfl directory
if [ ! -f "config.py" ]; then
    echo "❌ Error: Must run from nfl/ directory"
    exit 1
fi

# Create dated output directory
OUTPUT_DATE=$(date '+%Y-%m-%d')
mkdir -p "outputs/${OUTPUT_DATE}"

# Step 1: Update historical data (only download recent games)
echo "📥 Step 1/4: Updating NFL historical data..."
CURRENT_YEAR=$(date '+%Y')
python download_nfl_data.py --start-year $((CURRENT_YEAR - 1)) --end-year ${CURRENT_YEAR} || {
    echo "⚠️  Data download failed, using existing data..."
}

# Step 2: Retrain models if data is older than 7 days, else use cached models
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

# Step 3: Download upcoming NFL fixtures (next 2-4 weeks)
echo ""
echo "🔮 Step 3/4: Downloading upcoming NFL fixtures..."
python fixture_downloader.py --weeks-ahead 4

# Step 4: Generate predictions for all markets
echo ""
echo "🎯 Step 4/4: Generating predictions for upcoming games..."
python predict.py --output-dir "outputs/${OUTPUT_DATE}"

# Display summary
echo ""
echo "=" | head -c 60 | tr -d '\n' && echo ""
echo "✅ WEEKLY RUN COMPLETE!"
echo "=" | head -c 60 | tr -d '\n' && echo ""
echo ""
echo "📁 Results saved to: outputs/${OUTPUT_DATE}/"
echo ""

# Check if predictions file exists and show top picks
PRED_FILE="outputs/${OUTPUT_DATE}/nfl_predictions.csv"
if [ -f "$PRED_FILE" ]; then
    echo "🎲 TOP VALUE BETS THIS WEEK:"
    echo "----------------------------"
    # Show top 5 predictions if file exists
    head -6 "$PRED_FILE" | tail -5 || echo "See $PRED_FILE for all predictions"
    echo ""
    echo "Total predictions: $(tail -n +2 "$PRED_FILE" | wc -l)"
fi

echo ""
echo "💡 TIP: Review predictions in outputs/${OUTPUT_DATE}/ before placing bets"
echo "📊 Run backtest.py anytime to validate strategy performance"
echo ""

# Optional: Send email notification (uncomment and configure if needed)
# python send_predictions_email.py --predictions "$PRED_FILE"

exit 0

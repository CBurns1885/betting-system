#!/bin/bash
# run_nfl_system.sh - One-click NFL betting system runner

set -e  # Exit on error

echo "🏈 NFL BETTING SYSTEM - ONE-CLICK RUN"
echo "====================================="
echo ""

# Check if we're in the nfl directory
if [ ! -f "config.py" ]; then
    echo "❌ Error: Must run from nfl/ directory"
    exit 1
fi

# Step 1: Download historical data
echo "📥 Step 1/5: Downloading NFL historical data..."
python download_nfl_data.py --start-year 2018 --end-year 2024

# Step 2: Engineer features
echo ""
echo "🔧 Step 2/5: Engineering NFL features..."
python features.py

# Step 3: Train models
echo ""
echo "🤖 Step 3/5: Training ML models..."
python models.py

# Step 4: Download upcoming matches and make predictions
echo ""
echo "🔮 Step 4/5: Downloading upcoming NFL fixtures..."
python fixture_downloader.py --weeks-ahead 4

echo ""
echo "🎯 Making predictions for all markets..."
python predict.py

# Step 5: Run realistic backtest
echo ""
echo "📊 Step 5/5: Running realistic backtest with Kelly criterion..."
python realistic_backtest.py

echo ""
echo "✅ NFL SYSTEM RUN COMPLETE!"
echo "📁 Check outputs/ directory for:"
echo "   - predictions.csv (upcoming games)"
echo "   - backtest_results.csv (historical performance)"
echo "   - bankroll_chart.png (profit curve)"
echo ""

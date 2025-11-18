#!/bin/bash
# run_tennis_system.sh - One-click tennis betting system runner

set -e  # Exit on error

echo "🎾 TENNIS BETTING SYSTEM - ONE-CLICK RUN"
echo "========================================"
echo ""

# Check if we're in the tennis directory
if [ ! -f "config.py" ]; then
    echo "❌ Error: Must run from tennis/ directory"
    exit 1
fi

# Step 1: Download historical data
echo "📥 Step 1/5: Downloading historical tennis data..."
python download_tennis_data.py --start 2020 --end 2024 --tour both

# Step 2: Engineer features
echo ""
echo "🔧 Step 2/5: Engineering tennis features..."
python features.py

# Step 3: Train models
echo ""
echo "🤖 Step 3/5: Training ML models..."
python models.py

# Step 4: Download upcoming matches and make predictions
echo ""
echo "🔮 Step 4/5: Downloading upcoming matches..."
python fixture_downloader.py

echo ""
echo "🎯 Making predictions..."
python predict.py --market MATCH_WINNER

# Step 5: Run backtest
echo ""
echo "📊 Step 5/5: Running backtest..."
python backtest.py --bankroll 1000 --train-size 500 --test-size 100

echo ""
echo "✅ TENNIS SYSTEM RUN COMPLETE!"
echo "📁 Check outputs/ directory for results"
echo ""

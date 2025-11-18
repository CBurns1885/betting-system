#!/bin/bash
# run_nba_system.sh - One-click NBA betting system runner

set -e

echo "🏀 NBA BETTING SYSTEM - ONE-CLICK RUN"
echo "===================================="
echo ""

if [ ! -f "config.py" ]; then
    echo "❌ Error: Must run from nba/ directory"
    exit 1
fi

echo "📥 Step 1/5: Downloading NBA historical data..."
python download_nba_data.py --start-year 2018 --end-year 2024

echo ""
echo "🔧 Step 2/5: Engineering NBA features (pace-adjusted stats)..."
python features.py

echo ""
echo "🤖 Step 3/5: Training ML models..."
python models.py

echo ""
echo "🔮 Step 4/5: Downloading upcoming NBA fixtures..."
python fixture_downloader.py --days 7

echo ""
echo "🎯 Making predictions for all markets..."
python predict.py

echo ""
echo "📊 Step 5/5: Running backtest..."
python backtest.py

echo ""
echo "✅ NBA SYSTEM RUN COMPLETE!"
echo "📁 Check outputs/ directory for results"
echo ""

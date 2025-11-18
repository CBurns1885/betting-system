#!/bin/bash
# run_mlb_system.sh - One-click MLB betting system runner

set -e

echo "⚾ MLB BETTING SYSTEM - ONE-CLICK RUN"
echo "===================================="
echo ""

if [ ! -f "config.py" ]; then
    echo "❌ Error: Must run from mlb/ directory"
    exit 1
fi

echo "📥 Step 1/5: Downloading MLB historical data..."
python download_mlb_data.py --start-year 2018 --end-year 2024

echo ""
echo "🔧 Step 2/5: Engineering MLB features (ballpark factors, pitcher matchups)..."
python features.py

echo ""
echo "🤖 Step 3/5: Training ML models..."
python models.py

echo ""
echo "🔮 Step 4/5: Downloading upcoming MLB fixtures..."
python fixture_downloader.py --days 7

echo ""
echo "🎯 Making predictions..."
python predict.py

echo ""
echo "📊 Step 5/5: Running backtest..."
python backtest.py

echo ""
echo "✅ MLB SYSTEM RUN COMPLETE!"
echo "📁 Check outputs/ directory for results"
echo ""

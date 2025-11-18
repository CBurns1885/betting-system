#!/bin/bash
# run_rugby_system.sh - One-click Rugby Union betting system runner

set -e

echo "🏉 RUGBY UNION BETTING SYSTEM - ONE-CLICK RUN"
echo "============================================="
echo ""

if [ ! -f "config.py" ]; then
    echo "❌ Error: Must run from rugby/ directory"
    exit 1
fi

echo "📥 Step 1/5: Downloading Rugby Union historical data..."
python download_rugby_data.py --start 2018 --end 2024 --sample

echo ""
echo "🔧 Step 2/5: Engineering Rugby features (home advantage, ELO, H2H)..."
python features.py

echo ""
echo "🤖 Step 3/5: Training ML models (3-way classification: Home/Draw/Away)..."
python models.py

echo ""
echo "🎯 Step 4/5: Making predictions..."
python predict.py

echo ""
echo "📊 Step 5/5: Running backtest..."
python backtest.py

echo ""
echo "✅ RUGBY UNION SYSTEM RUN COMPLETE!"
echo "📁 Check outputs/ directory for results"
echo ""
echo "💡 Note: Using sample dataset. For real data, configure data sources in config.py"
echo ""

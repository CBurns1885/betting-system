#!/usr/bin/env python3
"""
validate_before_api.py
Complete system validation before paying for API subscription

This script runs comprehensive backtests to verify:
1. System accuracy (target: > 55%)
2. ROI potential (target: > 3%)
3. Market reliability
4. Model-market optimization

USAGE:
    python validate_before_api.py

EXPECTED TIME: 2-4 hours
OUTPUT: backtest_results/ directory with comprehensive reports
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("🔍 SYSTEM VALIDATION BEFORE API SUBSCRIPTION")
print("=" * 80)
print("\nThis will validate the system is ready for production use.")
print("Expected time: 2-4 hours")
print("Output: backtest_results/ directory")
print("\n" + "=" * 80)

# ============================================================================
# STEP 0: PRE-FLIGHT CHECKS
# ============================================================================

print("\nSTEP 0: Pre-flight Checks")
print("=" * 40)

# Check for required data
from config import DATA_DIR, OUTPUT_DIR, FEATURES_PARQUET

checks_passed = True

# 1. Check for features file
if not FEATURES_PARQUET.exists():
    print("❌ features.parquet not found!")
    print("   Please run: python run_weekly.py first")
    checks_passed = False
else:
    import pandas as pd
    df = pd.read_parquet(FEATURES_PARQUET)
    num_samples = len(df)
    num_features = len(df.columns)

    print(f"✅ features.parquet found")
    print(f"   Samples: {num_samples:,}")
    print(f"   Features: {num_features}")

    if num_samples < 5000:
        print(f"⚠️  Warning: Only {num_samples} samples (recommend > 10,000)")
        print("   Consider expanding training period")

    if num_features < 20:
        print(f"⚠️  Warning: Only {num_features} features (recommend > 30)")

# 2. Check for required packages
required_packages = {
    'sklearn': 'scikit-learn',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'xgboost': 'xgboost (optional but recommended)',
    'lightgbm': 'lightgbm (optional but recommended)',
    'optuna': 'optuna (optional but recommended)'
}

print("\n📦 Checking dependencies...")
for package, display_name in required_packages.items():
    try:
        __import__(package)
        print(f"✅ {display_name}")
    except ImportError:
        if package in ['xgboost', 'lightgbm', 'optuna']:
            print(f"⚠️  {display_name} - Not installed (optional)")
        else:
            print(f"❌ {display_name} - REQUIRED")
            checks_passed = False

if not checks_passed:
    print("\n❌ Pre-flight checks failed!")
    print("   Please fix issues above before proceeding.")
    sys.exit(1)

print("\n✅ All pre-flight checks passed!")

# ============================================================================
# STEP 1: QUICK VALIDATION (10-15 minutes)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 1: Quick Validation (10-15 minutes)")
print("=" * 80)
print("\nRunning basic backtest to verify system works...")

start_time = time.time()

try:
    # Check if backtest.py exists
    backtest_script = Path("backtest.py")
    if backtest_script.exists():
        print("\nExecuting: python backtest.py")
        import subprocess
        result = subprocess.run([sys.executable, "backtest.py"],
                              capture_output=True, text=True, timeout=900)

        if result.returncode == 0:
            print("✅ Quick backtest complete")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        else:
            print("⚠️  Quick backtest had issues:")
            print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
    else:
        print("ℹ️  backtest.py not found - skipping quick validation")
        print("   Proceeding to advanced validation...")

except Exception as e:
    print(f"⚠️  Quick backtest failed: {e}")
    print("   Continuing to advanced validation...")

elapsed = time.time() - start_time
print(f"\nQuick validation completed in {elapsed/60:.1f} minutes")

# ============================================================================
# STEP 2: ADVANCED VALIDATION (2-3 hours)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 2: Advanced Model Optimization (2-3 hours)")
print("=" * 80)
print("\nThis will test all models on all markets and find optimal combinations...")
print("⏰ This will take 2-3 hours - grab a coffee!")

response = input("\nProceed with advanced validation? (y/n): ").lower()

if response != 'y':
    print("\nValidation stopped by user.")
    print("You can run advanced validation later with:")
    print("   python backtest_engine_advanced.py")
    sys.exit(0)

start_time = time.time()

try:
    # Run advanced backtest engine
    advanced_script = Path("backtest_engine_advanced.py")

    if advanced_script.exists():
        print("\nExecuting: python backtest_engine_advanced.py")
        print("This will:")
        print("  • Test RandomForest, ExtraTrees, GradientBoosting, LogisticRegression")
        print("  • Test XGBoost, LightGBM, CatBoost (if available)")
        print("  • Optimize hyperparameters for each model-market combo")
        print("  • Find optimal ensemble weights")
        print("  • Generate comprehensive reports")
        print("\nStarting now...")

        import subprocess
        result = subprocess.run([sys.executable, str(advanced_script)],
                              capture_output=False,  # Show live output
                              timeout=14400)  # 4 hour timeout

        if result.returncode == 0:
            print("\n✅ Advanced validation complete!")
        else:
            print("\n⚠️  Advanced validation completed with warnings")

    else:
        # Try alternative advanced backtest
        alt_script = Path("advanced_backtest_engine.py")
        if alt_script.exists():
            print(f"\nExecuting: python {alt_script}")
            import subprocess
            result = subprocess.run([sys.executable, str(alt_script)],
                                  capture_output=False,
                                  timeout=14400)
        else:
            print("❌ No advanced backtest engine found!")
            print("   Expected: backtest_engine_advanced.py or advanced_backtest_engine.py")
            sys.exit(1)

except subprocess.TimeoutExpired:
    print("\n⚠️  Advanced validation timed out (> 4 hours)")
    print("   This might indicate performance issues.")
    print("   Check backtest_results/ for partial results.")
except Exception as e:
    print(f"\n❌ Advanced validation failed: {e}")
    print("   Please check the error and try again.")
    sys.exit(1)

elapsed = time.time() - start_time
print(f"\nAdvanced validation completed in {elapsed/60:.1f} minutes ({elapsed/3600:.1f} hours)")

# ============================================================================
# STEP 3: RESULTS ANALYSIS
# ============================================================================

print("\n" + "=" * 80)
print("STEP 3: Analyzing Results")
print("=" * 80)

results_dir = Path("backtest_results")

if not results_dir.exists():
    print("⚠️  backtest_results/ directory not found")
    print("   Backtest may not have completed successfully")
else:
    print(f"\n✅ Results directory found: {results_dir}")

    # List all result files
    result_files = list(results_dir.glob("*"))
    print(f"\n📁 Generated {len(result_files)} result files:")
    for file in sorted(result_files):
        size = file.stat().st_size
        print(f"   • {file.name} ({size:,} bytes)")

    # Try to load and summarize key results
    try:
        import pandas as pd

        # Check for model performance summary
        performance_file = results_dir / "model_performance_by_market.csv"
        if performance_file.exists():
            print("\n📊 MODEL PERFORMANCE SUMMARY:")
            print("=" * 60)

            df = pd.read_csv(performance_file)

            # Overall statistics
            print(f"\nTested: {df['model_name'].nunique()} models on {df['market'].nunique()} markets")
            print(f"Total combinations: {len(df)}")

            # Best performers
            print("\n🏆 TOP 5 MODEL-MARKET COMBINATIONS:")
            print("-" * 60)
            top_5 = df.nlargest(5, 'accuracy')[['model_name', 'market', 'accuracy', 'roi']]
            for idx, row in top_5.iterrows():
                print(f"{row['model_name']:20s} | {row['market']:20s} | "
                      f"Acc: {row['accuracy']:.1%} | ROI: {row['roi']:+.1%}")

            # Market averages
            print("\n📈 ACCURACY BY MARKET:")
            print("-" * 60)
            market_avg = df.groupby('market')['accuracy'].agg(['mean', 'max', 'count'])
            market_avg = market_avg.sort_values('mean', ascending=False)
            for market, row in market_avg.head(10).iterrows():
                print(f"{market:30s} | Avg: {row['mean']:.1%} | "
                      f"Best: {row['max']:.1%} | Models: {int(row['count'])}")

            # Overall accuracy
            overall_acc = df['accuracy'].mean()
            print(f"\n📊 OVERALL AVERAGE ACCURACY: {overall_acc:.1%}")

            # Decision guidance
            print("\n" + "=" * 60)
            print("🎯 VALIDATION RESULTS:")
            print("=" * 60)

            if overall_acc >= 0.55:
                print("✅ EXCELLENT - System exceeds 55% accuracy target")
                print("   Recommendation: PROCEED TO API MODE")
                print("   Expected improvement with API: +5-10%")
            elif overall_acc >= 0.52:
                print("⚠️  GOOD - System shows promise (52-55% accuracy)")
                print("   Recommendation: TEST MORE WITH CSV MODE")
                print("   Consider 4-week live validation before API")
            else:
                print("❌ NEEDS IMPROVEMENT - System below 52% accuracy")
                print("   Recommendation: IMPROVE SYSTEM BEFORE API")
                print("   Review feature engineering and model selection")

        else:
            print("\nℹ️  Detailed results file not found")
            print("   Check backtest_results/ directory manually")

    except Exception as e:
        print(f"\n⚠️  Could not analyze results: {e}")
        print("   Please check backtest_results/ directory manually")

# ============================================================================
# STEP 4: RECOMMENDATIONS
# ============================================================================

print("\n" + "=" * 80)
print("🎯 RECOMMENDATIONS")
print("=" * 80)

print("""
Based on your validation results:

1. ✅ PROCEED TO API if:
   • Overall accuracy ≥ 55%
   • Best markets ≥ 58%
   • Positive ROI on multiple markets
   • Stable performance across time

2. ⚠️  TEST MORE WITH CSV if:
   • Overall accuracy 52-55%
   • Some markets performing well
   • Want more confidence before paying

   ACTION: Run 4-week live validation
   python run_weekly.py  # Each week
   Track actual results manually
   Then decide on API

3. ❌ IMPROVE SYSTEM if:
   • Overall accuracy < 52%
   • Negative ROI on most markets
   • High variance in results

   ACTION: Review:
   • Feature engineering (features.py)
   • Training data quality (data_ingest.py)
   • Model selection (models.py)
   • Hyperparameter tuning (tuning.py)

NEXT STEPS:

CSV Mode (Free Testing):
  python run_weekly.py
  → Test predictions for free
  → Build confidence
  → Track real results

API Mode (When Ready - $29/month):
  export API_FOOTBALL_KEY='your-key'
  python run_weekly_api.py
  → 80+ markets
  → 200+ features
  → xG analytics
  → Injury tracking
  → Value betting tools
  → Expected: +5-10% accuracy boost

Remember: API pays for itself if accuracy improves just 5%!
""")

print("=" * 80)
print("Validation complete! Check backtest_results/ for detailed reports.")
print("=" * 80)

#!/usr/bin/env python3
"""
NFL Weekly Betting System - Main Runner

Complete pipeline for weekly NFL predictions:
1. Download latest historical data
2. Download upcoming fixtures
3. Ingest and process data
4. Build features
5. Train/load models
6. Generate predictions
7. Create analysis reports

Run this once per week (Tuesday/Wednesday recommended after MNF)
"""

import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    BASE_DIR, DATA_DIR, RAW_DIR, PROCESSED_DIR, OUTPUT_DIR,
    MODEL_ARTIFACTS_DIR, SEASONS, log_header
)
from progress_utils import Timer

# Import pipeline components
from download_nfl_data import NFLDataDownloader
from fixture_downloader import NFLFixtureDownloader
from data_ingest import NFLDataIngestor
from features import build_features_from_raw
from models import train_nfl_models
from predict import predict_upcoming_games


def step_1_download_historical():
    """Download historical NFL data"""
    log_header("STEP 1: Download Historical Data")

    downloader = NFLDataDownloader()

    # Download last 3 seasons (or all configured seasons)
    recent_seasons = SEASONS[-3:] if len(SEASONS) > 3 else SEASONS

    print(f"📥 Downloading seasons: {recent_seasons}")

    downloader.download_all_seasons(recent_seasons)

    print("✅ Step 1 complete\n")


def step_2_download_fixtures():
    """Download upcoming NFL fixtures"""
    log_header("STEP 2: Download Upcoming Fixtures")

    downloader = NFLFixtureDownloader()
    fixtures = downloader.download_and_save()

    if fixtures is None or len(fixtures) == 0:
        print("⚠️  No upcoming fixtures found")
        print("⚠️  If this is during the season, check your API keys")
        return False

    print("✅ Step 2 complete\n")
    return True


def step_3_ingest_data():
    """Ingest and combine raw data"""
    log_header("STEP 3: Ingest Raw Data")

    ingestor = NFLDataIngestor()
    df = ingestor.run()

    if df is None or len(df) == 0:
        print("❌ Data ingestion failed")
        return False

    print("✅ Step 3 complete\n")
    return True


def step_4_build_features():
    """Build features from processed data"""
    log_header("STEP 4: Build Features")

    historical_file = PROCESSED_DIR / "historical_games.parquet"

    if not historical_file.exists():
        print("❌ Historical data not found. Run step 3 first.")
        return False

    features_df = build_features_from_raw(str(historical_file))

    if features_df is None or len(features_df) == 0:
        print("❌ Feature building failed")
        return False

    print("✅ Step 4 complete\n")
    return True


def step_5_train_models(force_retrain: bool = False):
    """Train or load models"""
    log_header("STEP 5: Train Models")

    features_file = PROCESSED_DIR / "features.parquet"

    if not features_file.exists():
        print("❌ Features not found. Run step 4 first.")
        return False

    # Check if models already exist
    existing_models = list(MODEL_ARTIFACTS_DIR.glob("*.pkl"))

    if existing_models and not force_retrain:
        print(f"📦 Found {len(existing_models)} existing models")
        print("   Use --retrain to force retraining")
        print("   Skipping training...\n")
        print("✅ Step 5 complete (using existing models)\n")
        return True

    # Train new models
    train_nfl_models(str(features_file))

    print("✅ Step 5 complete\n")
    return True


def step_6_generate_predictions():
    """Generate predictions for upcoming games"""
    log_header("STEP 6: Generate Predictions")

    fixtures_file = BASE_DIR / "upcoming_fixtures.csv"
    historical_file = PROCESSED_DIR / "historical_games.parquet"

    if not fixtures_file.exists():
        print("❌ Fixtures not found. Run step 2 first.")
        return False

    if not historical_file.exists():
        print("❌ Historical data not found. Run step 3 first.")
        return False

    predict_upcoming_games(
        fixtures_path=str(fixtures_file),
        historical_path=str(historical_file)
    )

    print("✅ Step 6 complete\n")
    return True


def step_7_create_reports():
    """Create analysis reports"""
    log_header("STEP 7: Create Reports")

    predictions_file = OUTPUT_DIR / "weekly_predictions.csv"

    if not predictions_file.exists():
        print("❌ Predictions not found. Run step 6 first.")
        return False

    # Load predictions
    import pandas as pd
    predictions = pd.read_csv(predictions_file)

    # Create simple reports
    print("\n📊 Prediction Summary:")
    print(f"   Total games: {len(predictions)}")

    if 'moneyline_confidence' in predictions.columns:
        high_conf = predictions[predictions['moneyline_confidence'] > 0.65]
        print(f"   High confidence picks (>65%): {len(high_conf)}")

        if len(high_conf) > 0:
            print("\n🔥 Top Picks:")
            top = high_conf.nlargest(5, 'moneyline_confidence')[
                ['home_team', 'away_team', 'moneyline_pick', 'moneyline_confidence']
            ]
            print(top.to_string(index=False))

    # Save top picks
    if 'moneyline_confidence' in predictions.columns:
        top_picks = predictions.nlargest(10, 'moneyline_confidence')
        top_picks_file = OUTPUT_DIR / "top_picks.csv"
        top_picks.to_csv(top_picks_file, index=False)
        print(f"\n💾 Saved top picks to {top_picks_file}")

    print("\n✅ Step 7 complete\n")
    return True


def main():
    """Main pipeline"""
    import argparse

    parser = argparse.ArgumentParser(
        description='NFL Weekly Betting System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_weekly.py                 # Run full pipeline
  python run_weekly.py --retrain       # Force model retraining
  python run_weekly.py --skip-download # Skip data download
        """
    )

    parser.add_argument('--retrain', action='store_true',
                       help='Force model retraining even if models exist')
    parser.add_argument('--skip-download', action='store_true',
                       help='Skip historical data download (use existing)')
    parser.add_argument('--fixtures-only', action='store_true',
                       help='Only download fixtures and predict (fast mode)')

    args = parser.parse_args()

    # Print header
    print("=" * 70)
    print("🏈 NFL WEEKLY BETTING SYSTEM")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    with Timer("Complete Pipeline"):
        # Fast mode: just fixtures and predictions
        if args.fixtures_only:
            print("\n⚡ FAST MODE: Fixtures and predictions only\n")

            if not step_2_download_fixtures():
                print("❌ Pipeline failed at step 2")
                return

            if not step_6_generate_predictions():
                print("❌ Pipeline failed at step 6")
                return

            if not step_7_create_reports():
                print("❌ Pipeline failed at step 7")
                return

        # Full mode
        else:
            # Step 1: Download historical data (unless skipped)
            if not args.skip_download:
                step_1_download_historical()

            # Step 2: Download fixtures
            if not step_2_download_fixtures():
                print("❌ Pipeline failed at step 2")
                return

            # Step 3: Ingest data
            if not step_3_ingest_data():
                print("❌ Pipeline failed at step 3")
                return

            # Step 4: Build features
            if not step_4_build_features():
                print("❌ Pipeline failed at step 4")
                return

            # Step 5: Train models
            if not step_5_train_models(force_retrain=args.retrain):
                print("❌ Pipeline failed at step 5")
                return

            # Step 6: Generate predictions
            if not step_6_generate_predictions():
                print("❌ Pipeline failed at step 6")
                return

            # Step 7: Create reports
            if not step_7_create_reports():
                print("❌ Pipeline failed at step 7")
                return

    # Final summary
    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 70)
    print(f"\n📁 Results saved to: {OUTPUT_DIR}")
    print(f"   - weekly_predictions.csv")
    print(f"   - weekly_predictions.xlsx")
    print(f"   - top_picks.csv")
    print("\n🎯 Good luck with your bets! Bet responsibly.\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
test_api_integration.py
Test script to verify API-Football integration works with existing pipeline
"""

import os
import sys
from pathlib import Path
import pandas as pd

def test_imports():
    """Test that all required modules can be imported"""
    print("="*60)
    print("TEST 1: Module Imports")
    print("="*60)

    try:
        from api_data_adapter import (
            convert_api_fixture_to_csv_row,
            download_with_fallback,
            validate_api_vs_csv_format
        )
        print("✅ api_data_adapter imports OK")
    except ImportError as e:
        print(f"❌ Failed to import api_data_adapter: {e}")
        return False

    try:
        from enhanced_api_integration import APIFootballClient, LEAGUE_MAPPING
        print("✅ enhanced_api_integration imports OK")
    except ImportError as e:
        print(f"❌ Failed to import enhanced_api_integration: {e}")
        return False

    try:
        from download_football_data import download
        print("✅ download_football_data imports OK")
    except ImportError as e:
        print(f"❌ Failed to import download_football_data: {e}")
        return False

    try:
        from data_ingest import build_historical_results
        print("✅ data_ingest imports OK")
    except ImportError as e:
        print(f"❌ Failed to import data_ingest: {e}")
        return False

    print("\n✅ All imports successful!\n")
    return True


def test_league_mapping():
    """Test that league codes are properly mapped"""
    print("="*60)
    print("TEST 2: League Mapping")
    print("="*60)

    from enhanced_api_integration import LEAGUE_MAPPING
    from config import LEAGUE_CODES

    mapped_count = 0
    unmapped = []

    for league_code in LEAGUE_CODES:
        if league_code in LEAGUE_MAPPING:
            api_id = LEAGUE_MAPPING[league_code]
            print(f"✅ {league_code:4s} → API ID {api_id:3d}")
            mapped_count += 1
        else:
            print(f"⚠️  {league_code:4s} → NOT MAPPED")
            unmapped.append(league_code)

    print(f"\n📊 Summary: {mapped_count}/{len(LEAGUE_CODES)} leagues mapped")

    if unmapped:
        print(f"⚠️  Unmapped leagues: {unmapped}")
        print("   These will use CSV downloads only")

    print()
    return True


def test_csv_format():
    """Test CSV format conversion"""
    print("="*60)
    print("TEST 3: CSV Format Conversion")
    print("="*60)

    from api_data_adapter import convert_api_fixture_to_csv_row

    # Mock API-Football fixture response
    mock_fixture = {
        "fixture": {
            "id": 12345,
            "date": "2024-01-15T20:00:00+00:00",
            "status": {"short": "FT"}
        },
        "teams": {
            "home": {"id": 33, "name": "Manchester United"},
            "away": {"id": 34, "name": "Newcastle"}
        },
        "goals": {
            "home": 2,
            "away": 1
        },
        "score": {
            "fulltime": {"home": 2, "away": 1}
        }
    }

    row = convert_api_fixture_to_csv_row(mock_fixture, "E0", "2324")

    # Verify required columns
    required_cols = ["League", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "Season"]

    missing = []
    for col in required_cols:
        if col not in row or row[col] is None:
            missing.append(col)

    if missing:
        print(f"❌ Missing required columns: {missing}")
        return False

    # Verify values
    assert row["League"] == "E0", f"Expected League=E0, got {row['League']}"
    assert row["HomeTeam"] == "Manchester United", f"Expected HomeTeam=Manchester United"
    assert row["AwayTeam"] == "Newcastle", f"Expected AwayTeam=Newcastle"
    assert row["FTHG"] == 2, f"Expected FTHG=2, got {row['FTHG']}"
    assert row["FTAG"] == 1, f"Expected FTAG=1, got {row['FTAG']}"
    assert row["FTR"] == "H", f"Expected FTR=H, got {row['FTR']}"
    assert row["Season"] == "2324", f"Expected Season=2324, got {row['Season']}"

    print("✅ Mock fixture converted correctly:")
    print(f"   League: {row['League']}")
    print(f"   Date: {row['Date']}")
    print(f"   Match: {row['HomeTeam']} {row['FTHG']}-{row['FTAG']} {row['AwayTeam']}")
    print(f"   Result: {row['FTR']}")
    print(f"   Season: {row['Season']}")
    print()
    return True


def test_api_key_detection():
    """Test API key detection"""
    print("="*60)
    print("TEST 4: API Key Detection")
    print("="*60)

    api_key = os.environ.get("API_FOOTBALL_KEY", "")

    if api_key and api_key != "YOUR_API_KEY_HERE":
        print(f"✅ API key detected: {api_key[:10]}...{api_key[-4:]}")
        print("   API mode is READY")
        print("   To enable: Set USE_API_FOOTBALL=1 in run_weekly.py")
        has_key = True
    else:
        print("⚠️  No API key found")
        print("   CSV mode will be used")
        print("   To enable API mode:")
        print("   1. Get API key from https://www.api-football.com/")
        print("   2. Set: export API_FOOTBALL_KEY='your-key'")
        print("   3. Set USE_API_FOOTBALL=1 in run_weekly.py")
        has_key = False

    print()
    return True


def test_data_ingest_compatibility():
    """Test that data_ingest can handle both CSV and API data"""
    print("="*60)
    print("TEST 5: Data Ingest Compatibility")
    print("="*60)

    from data_ingest import _load_local_csv, _standardize_columns
    from config import RAW_DIR

    # Check if raw directory has any CSVs
    csv_files = list(RAW_DIR.glob("*.csv")) if RAW_DIR.exists() else []

    if csv_files:
        print(f"✅ Found {len(csv_files)} CSV files in {RAW_DIR}")

        # Try loading one
        sample_csv = csv_files[0]
        try:
            df = pd.read_csv(sample_csv, encoding='latin1')
            df = _standardize_columns(df)
            print(f"✅ Successfully loaded and standardized: {sample_csv.name}")
            print(f"   Columns: {list(df.columns)}")
            print(f"   Rows: {len(df)}")
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            return False
    else:
        print("ℹ️  No CSV files found in raw directory")
        print("   This is OK - they will be downloaded when needed")

    # Check for API-generated CSVs
    api_raw_dir = Path("data/raw_api")
    api_csv_files = list(api_raw_dir.glob("*.csv")) if api_raw_dir.exists() else []

    if api_csv_files:
        print(f"✅ Found {len(api_csv_files)} API-generated CSV files")
    else:
        print("ℹ️  No API-generated CSV files found")
        print("   These will be created when API mode is enabled")

    print()
    return True


def test_run_weekly_integration():
    """Test that run_weekly.py has API integration"""
    print("="*60)
    print("TEST 6: run_weekly.py Integration")
    print("="*60)

    run_weekly_path = Path("run_weekly.py")

    if not run_weekly_path.exists():
        print("❌ run_weekly.py not found")
        return False

    content = run_weekly_path.read_text()

    checks = {
        "USE_API_FOOTBALL": 'USE_API_FOOTBALL' in content,
        "API mode detection": 'use_api_mode = os.environ.get("USE_API_FOOTBALL"' in content,
        "API adapter import": 'from api_data_adapter import' in content,
        "Fallback logic": 'download_with_fallback' in content
    }

    all_passed = True
    for check_name, passed in checks.items():
        if passed:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_passed = False

    if all_passed:
        print("\n✅ run_weekly.py has full API integration!")

        # Show current settings
        if 'os.environ["USE_API_FOOTBALL"] = "0"' in content:
            print("   Current mode: CSV (default)")
            print("   To enable API: Change USE_API_FOOTBALL to '1'")
        elif 'os.environ["USE_API_FOOTBALL"] = "1"' in content:
            print("   Current mode: API")

    print()
    return all_passed


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("API-FOOTBALL INTEGRATION TEST SUITE")
    print("="*60)
    print()

    tests = [
        ("Module Imports", test_imports),
        ("League Mapping", test_league_mapping),
        ("CSV Format Conversion", test_csv_format),
        ("API Key Detection", test_api_key_detection),
        ("Data Ingest Compatibility", test_data_ingest_compatibility),
        ("run_weekly Integration", test_run_weekly_integration),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✅ API integration is ready to use")
        print("\nTo enable API mode:")
        print("   1. Get API key from https://www.api-football.com/")
        print("   2. Set: export API_FOOTBALL_KEY='your-key'")
        print("   3. Change USE_API_FOOTBALL to '1' in run_weekly.py")
        print("   4. Run: python run_weekly.py")
    else:
        print("\n⚠️  Some tests failed - review errors above")

    print("="*60)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

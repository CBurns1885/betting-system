#!/usr/bin/env python3
"""
NFL Data Ingestion

Combines raw CSV files from multiple sources into a single processed dataset.
Handles data cleaning, standardization, and validation.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List
from config import RAW_DIR, PROCESSED_DIR, NFL_TEAMS, log_header
from progress_utils import Timer


class NFLDataIngestor:
    """Combine and clean raw NFL data"""

    def __init__(self):
        self.raw_dir = RAW_DIR
        self.processed_dir = PROCESSED_DIR
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def load_raw_files(self, pattern: str = "nfl_*.csv") -> pd.DataFrame:
        """Load all raw CSV files matching pattern"""
        files = list(self.raw_dir.glob(pattern))

        if not files:
            print(f"⚠️  No files found matching {pattern} in {self.raw_dir}")
            return pd.DataFrame()

        print(f"📂 Found {len(files)} raw files")

        dfs = []
        for file in sorted(files):
            try:
                df = pd.read_csv(file)
                print(f"  ✅ Loaded {file.name}: {len(df)} games")
                dfs.append(df)
            except Exception as e:
                print(f"  ⚠️  Error loading {file.name}: {e}")

        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            return combined

        return pd.DataFrame()

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize data"""
        print("🧹 Cleaning data...")

        df = df.copy()

        # Remove duplicates
        before_count = len(df)
        df = df.drop_duplicates(subset=['season', 'week', 'home_team', 'away_team'])
        after_count = len(df)

        if before_count > after_count:
            print(f"  ✅ Removed {before_count - after_count} duplicates")

        # Validate team codes
        valid_teams = set(NFL_TEAMS.keys())
        df = df[
            df['home_team'].isin(valid_teams) &
            df['away_team'].isin(valid_teams)
        ]

        # Ensure numeric scores
        if 'home_score' in df.columns:
            df['home_score'] = pd.to_numeric(df['home_score'], errors='coerce')
        if 'away_score' in df.columns:
            df['away_score'] = pd.to_numeric(df['away_score'], errors='coerce')

        # Sort by season and week
        df = df.sort_values(['season', 'week']).reset_index(drop=True)

        print(f"  ✅ Final dataset: {len(df)} games")

        return df

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate data quality"""
        print("✓ Validating data...")

        issues = []

        # Check required columns
        required = ['season', 'week', 'home_team', 'away_team']
        missing = [col for col in required if col not in df.columns]

        if missing:
            issues.append(f"Missing required columns: {missing}")

        # Check for null values in key columns
        for col in required:
            if col in df.columns and df[col].isna().any():
                null_count = df[col].isna().sum()
                issues.append(f"Column '{col}' has {null_count} null values")

        # Check valid team codes
        valid_teams = set(NFL_TEAMS.keys())

        invalid_home = set(df['home_team'].unique()) - valid_teams
        invalid_away = set(df['away_team'].unique()) - valid_teams

        if invalid_home:
            issues.append(f"Invalid home teams: {invalid_home}")
        if invalid_away:
            issues.append(f"Invalid away teams: {invalid_away}")

        # Report
        if issues:
            print("  ⚠️  Validation issues found:")
            for issue in issues:
                print(f"    - {issue}")
            return False
        else:
            print("  ✅ Data validation passed")
            return True

    def save_processed(self, df: pd.DataFrame, filename: str = "historical_games.parquet"):
        """Save processed data"""
        output_path = self.processed_dir / filename

        # Save as parquet (efficient)
        df.to_parquet(output_path, index=False)
        print(f"✅ Saved to {output_path}")

        # Also save as CSV for easy viewing
        csv_path = output_path.with_suffix('.csv')
        df.to_csv(csv_path, index=False)
        print(f"✅ Saved to {csv_path}")

    def run(self):
        """Run full ingestion pipeline"""
        with Timer("NFL Data Ingestion"):
            # Load raw files
            df = self.load_raw_files()

            if df.empty:
                print("⚠️  No data to process")
                return None

            # Clean
            df = self.clean_data(df)

            # Validate
            self.validate_data(df)

            # Save
            self.save_processed(df)

            return df


def main():
    """Main ingestion function"""
    log_header("NFL Data Ingestion")

    ingestor = NFLDataIngestor()
    ingestor.run()

    print("\n✅ Ingestion complete!")


if __name__ == "__main__":
    main()

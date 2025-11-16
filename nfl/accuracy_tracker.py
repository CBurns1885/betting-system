#!/usr/bin/env python3
"""
NFL Accuracy Tracker

Tracks prediction accuracy over time to improve the model.
Stores results in SQLite database for historical analysis.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from config import BASE_DIR, OUTPUT_DIR, log_header


class NFLAccuracyTracker:
    """Track and analyze prediction accuracy"""

    def __init__(self, db_path: str = None):
        """
        Initialize tracker

        Args:
            db_path: Path to SQLite database (default: outputs/accuracy.db)
        """
        if db_path is None:
            db_path = OUTPUT_DIR.parent / "accuracy.db"

        self.db_path = db_path
        self.conn = None
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with tables"""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        # Predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_date TEXT,
                game_date TEXT,
                week INTEGER,
                season INTEGER,
                home_team TEXT,
                away_team TEXT,
                market TEXT,
                pick TEXT,
                confidence REAL,
                probability REAL,
                actual_result TEXT,
                correct INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accuracy_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT,
                total_picks INTEGER,
                correct_picks INTEGER,
                accuracy REAL,
                avg_confidence REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    def log_predictions(self, predictions_df: pd.DataFrame, week: int, season: int):
        """
        Log predictions to database

        Args:
            predictions_df: DataFrame with predictions
            week: NFL week number
            season: NFL season year
        """
        prediction_date = datetime.now().strftime("%Y-%m-%d")

        records = []

        for _, game in predictions_df.iterrows():
            # Moneyline
            if 'moneyline_pick' in game:
                records.append({
                    'prediction_date': prediction_date,
                    'game_date': game.get('date', ''),
                    'week': week,
                    'season': season,
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'market': 'MONEYLINE',
                    'pick': game['moneyline_pick'],
                    'confidence': game.get('moneyline_confidence', 0),
                    'probability': game.get('moneyline_home_prob', 0),
                    'actual_result': None,
                    'correct': None,
                })

            # Spread
            if 'spread_pick' in game:
                records.append({
                    'prediction_date': prediction_date,
                    'game_date': game.get('date', ''),
                    'week': week,
                    'season': season,
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'market': 'SPREAD',
                    'pick': game['spread_pick'],
                    'confidence': game.get('spread_confidence', 0),
                    'probability': game.get('spread_cover_prob', 0),
                    'actual_result': None,
                    'correct': None,
                })

            # Total
            if 'total_pick' in game:
                records.append({
                    'prediction_date': prediction_date,
                    'game_date': game.get('date', ''),
                    'week': week,
                    'season': season,
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'market': 'TOTAL',
                    'pick': game['total_pick'],
                    'confidence': game.get('total_confidence', 0),
                    'probability': game.get('total_over_prob', 0),
                    'actual_result': None,
                    'correct': None,
                })

        # Insert into database
        df = pd.DataFrame(records)
        df.to_sql('predictions', self.conn, if_exists='append', index=False)

        print(f"✅ Logged {len(records)} predictions to database")

    def update_results(self, results_df: pd.DataFrame):
        """
        Update predictions with actual results

        Args:
            results_df: DataFrame with game results (home_team, away_team, home_score, away_score)
        """
        cursor = self.conn.cursor()

        updated = 0

        for _, result in results_df.iterrows():
            home_team = result['home_team']
            away_team = result['away_team']
            home_score = result['home_score']
            away_score = result['away_score']

            # Determine moneyline result
            if home_score > away_score:
                ml_result = 'HOME'
            elif away_score > home_score:
                ml_result = 'AWAY'
            else:
                ml_result = 'TIE'

            # Update moneyline predictions
            cursor.execute("""
                UPDATE predictions
                SET actual_result = ?,
                    correct = CASE WHEN pick = ? THEN 1 ELSE 0 END
                WHERE home_team = ? AND away_team = ? AND market = 'MONEYLINE'
                  AND actual_result IS NULL
            """, (ml_result, ml_result, home_team, away_team))

            # Spread result (would need spread line to determine)
            # Skipping for now - would require spread data

            # Total result (would need total line)
            # Skipping for now - would require total line

            updated += cursor.rowcount

        self.conn.commit()
        print(f"✅ Updated {updated} predictions with results")

    def calculate_accuracy(self) -> pd.DataFrame:
        """
        Calculate accuracy by market

        Returns:
            DataFrame with accuracy stats
        """
        query = """
            SELECT
                market,
                COUNT(*) as total_picks,
                SUM(correct) as correct_picks,
                AVG(CASE WHEN correct IS NOT NULL THEN correct ELSE NULL END) as accuracy,
                AVG(confidence) as avg_confidence
            FROM predictions
            WHERE correct IS NOT NULL
            GROUP BY market
        """

        df = pd.read_sql_query(query, self.conn)
        return df

    def generate_accuracy_report(self, output_file: str = None):
        """Generate accuracy report"""

        if output_file is None:
            output_file = OUTPUT_DIR / "accuracy_report.html"

        log_header("Accuracy Report")

        # Overall accuracy
        accuracy_df = self.calculate_accuracy()

        if accuracy_df.empty:
            print("⚠️  No completed predictions to analyze")
            return

        print("\n📊 Accuracy by Market:")
        print(accuracy_df.to_string(index=False))

        # Accuracy by confidence level
        query = """
            SELECT
                CASE
                    WHEN confidence >= 0.70 THEN 'High (70%+)'
                    WHEN confidence >= 0.60 THEN 'Medium (60-70%)'
                    ELSE 'Low (<60%)'
                END as confidence_level,
                COUNT(*) as total,
                SUM(correct) as correct,
                AVG(CASE WHEN correct IS NOT NULL THEN correct ELSE NULL END) as accuracy
            FROM predictions
            WHERE correct IS NOT NULL
            GROUP BY confidence_level
        """

        conf_df = pd.read_sql_query(query, self.conn)

        # Create HTML report
        html = f"""
        <html>
        <head>
            <title>NFL Prediction Accuracy</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #003366; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th {{ background-color: #0066cc; color: white; padding: 10px; }}
                td {{ border: 1px solid #ddd; padding: 8px; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>🎯 NFL Prediction Accuracy Report</h1>

            <h2>Accuracy by Market</h2>
            {accuracy_df.to_html(index=False)}

            <h2>Accuracy by Confidence Level</h2>
            {conf_df.to_html(index=False)}

            <p><em>Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</em></p>
        </body>
        </html>
        """

        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✅ Saved accuracy report to {output_file}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main accuracy tracking"""
    import argparse

    parser = argparse.ArgumentParser(description='Track NFL prediction accuracy')
    parser.add_argument('--log', type=str,
                       help='Log predictions from CSV file')
    parser.add_argument('--update', type=str,
                       help='Update with results from CSV file')
    parser.add_argument('--report', action='store_true',
                       help='Generate accuracy report')
    parser.add_argument('--week', type=int, help='NFL week number')
    parser.add_argument('--season', type=int, help='NFL season year')

    args = parser.parse_args()

    tracker = NFLAccuracyTracker()

    try:
        if args.log:
            predictions = pd.read_csv(args.log)
            week = args.week or 1
            season = args.season or datetime.now().year
            tracker.log_predictions(predictions, week, season)

        if args.update:
            results = pd.read_csv(args.update)
            tracker.update_results(results)

        if args.report:
            tracker.generate_accuracy_report()

    finally:
        tracker.close()


if __name__ == "__main__":
    main()

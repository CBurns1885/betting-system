#!/usr/bin/env python3
"""
NFL Spread Analyzer

Analyzes spread betting opportunities and identifies:
- Games with high confidence spread picks
- Value against the market spread
- Key numbers analysis (3, 7, 10 points)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from config import OUTPUT_DIR, log_header


class NFLSpreadAnalyzer:
    """Analyze NFL spread betting opportunities"""

    def __init__(self, predictions_df: pd.DataFrame):
        """
        Initialize with predictions

        Args:
            predictions_df: DataFrame with predictions including spread probabilities
        """
        self.predictions = predictions_df.copy()
        self.key_numbers = [3, 7, 10, 14]  # Important margins in NFL

    def find_high_confidence_spreads(self, threshold: float = 0.60) -> pd.DataFrame:
        """
        Find spread picks with high confidence

        Args:
            threshold: Minimum confidence level (default 60%)

        Returns:
            DataFrame of high confidence spread picks
        """
        if 'spread_confidence' not in self.predictions.columns:
            print("⚠️  No spread confidence data available")
            return pd.DataFrame()

        high_conf = self.predictions[
            self.predictions['spread_confidence'] >= threshold
        ].copy()

        high_conf = high_conf.sort_values('spread_confidence', ascending=False)

        return high_conf[[
            'home_team', 'away_team', 'spread_line',
            'spread_pick', 'spread_confidence', 'spread_cover_prob'
        ]]

    def analyze_key_numbers(self) -> pd.DataFrame:
        """
        Analyze spreads near key numbers (3, 7, 10)

        Games with spreads at or near key numbers require extra attention
        """
        if 'spread_line' not in self.predictions.columns:
            print("⚠️  No spread line data available")
            return pd.DataFrame()

        analysis = []

        for _, game in self.predictions.iterrows():
            spread = game.get('spread_line')

            if pd.isna(spread):
                continue

            # Find nearest key number
            nearest_key = min(self.key_numbers, key=lambda x: abs(x - abs(spread)))
            distance = abs(abs(spread) - nearest_key)

            # Flag if within 0.5 of a key number
            is_key = distance <= 0.5

            analysis.append({
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'spread': spread,
                'nearest_key_number': nearest_key,
                'distance_to_key': distance,
                'is_key_number': is_key,
                'spread_pick': game.get('spread_pick', ''),
                'confidence': game.get('spread_confidence', 0),
            })

        df = pd.DataFrame(analysis)

        # Sort by distance to key number
        df = df.sort_values('distance_to_key')

        return df

    def find_value_bets(self, edge_threshold: float = 0.05) -> pd.DataFrame:
        """
        Find spreads with value against the market

        Args:
            edge_threshold: Minimum edge required (default 5%)

        Returns:
            DataFrame of value bets
        """
        # Convert implied odds to probability
        # For a standard -110 line, implied prob is ~52.4%

        value_bets = []

        for _, game in self.predictions.iterrows():
            cover_prob = game.get('spread_cover_prob', 0)

            # Assuming standard -110 line (implied 52.4%)
            market_prob = 0.524
            edge = cover_prob - market_prob

            if edge >= edge_threshold:
                value_bets.append({
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'spread': game.get('spread_line', 'N/A'),
                    'model_prob': cover_prob,
                    'market_prob': market_prob,
                    'edge': edge,
                    'pick': game.get('spread_pick', ''),
                })

        if not value_bets:
            return pd.DataFrame()

        df = pd.DataFrame(value_bets)
        df = df.sort_values('edge', ascending=False)

        return df

    def create_report(self, output_file: str = None):
        """Create comprehensive spread analysis report"""

        if output_file is None:
            output_file = OUTPUT_DIR / "spread_analysis.html"

        log_header("Spread Analysis Report")

        # High confidence picks
        high_conf = self.find_high_confidence_spreads(threshold=0.60)

        # Key numbers
        key_numbers = self.analyze_key_numbers()

        # Value bets
        value = self.find_value_bets(edge_threshold=0.05)

        # Create HTML report
        html = f"""
        <html>
        <head>
            <title>NFL Spread Analysis</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #003366; }}
                h2 {{ color: #0066cc; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th {{ background-color: #0066cc; color: white; padding: 10px; text-align: left; }}
                td {{ border: 1px solid #ddd; padding: 8px; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .high {{ background-color: #d4edda; }}
                .medium {{ background-color: #fff3cd; }}
                .low {{ background-color: #f8d7da; }}
            </style>
        </head>
        <body>
            <h1>🏈 NFL Spread Analysis Report</h1>

            <h2>📊 High Confidence Spread Picks (>60%)</h2>
            {high_conf.to_html(index=False) if not high_conf.empty else '<p>No high confidence picks found.</p>'}

            <h2>🔑 Key Number Analysis</h2>
            <p>Games with spreads at or near key numbers (3, 7, 10, 14):</p>
            {key_numbers[key_numbers['is_key_number']].to_html(index=False) if not key_numbers.empty else '<p>No games near key numbers.</p>'}

            <h2>💎 Value Bets (>5% Edge)</h2>
            {value.to_html(index=False) if not value.empty else '<p>No value bets found.</p>'}

            <h2>📈 Summary Statistics</h2>
            <ul>
                <li>Total games analyzed: {len(self.predictions)}</li>
                <li>High confidence picks: {len(high_conf)}</li>
                <li>Games near key numbers: {len(key_numbers[key_numbers['is_key_number']]) if not key_numbers.empty else 0}</li>
                <li>Value bets identified: {len(value)}</li>
            </ul>
        </body>
        </html>
        """

        # Save report
        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✅ Saved spread analysis to {output_file}")

        # Also save as CSV
        csv_file = str(output_file).replace('.html', '.csv')
        if not high_conf.empty:
            high_conf.to_csv(csv_file, index=False)
            print(f"✅ Saved CSV to {csv_file}")

        return high_conf


def main():
    """Main analysis function"""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze NFL spread bets')
    parser.add_argument('--predictions', type=str,
                       default=str(OUTPUT_DIR / 'weekly_predictions.csv'),
                       help='Path to predictions CSV')
    parser.add_argument('--threshold', type=float, default=0.60,
                       help='Confidence threshold (default: 0.60)')

    args = parser.parse_args()

    # Load predictions
    predictions = pd.read_csv(args.predictions)

    # Analyze
    analyzer = NFLSpreadAnalyzer(predictions)
    analyzer.create_report()


if __name__ == "__main__":
    main()

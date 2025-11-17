#!/usr/bin/env python3
"""
NFL Backtest Visualizer

Creates charts and reports from backtest results.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from config import OUTPUT_DIR, log_header

# Optional: matplotlib for charts
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class NFLBacktestVisualizer:
    """Visualize backtest results"""

    def __init__(self, summary_csv: str = None, predictions_csv: str = None):
        """
        Initialize visualizer

        Args:
            summary_csv: Path to backtest_summary.csv
            predictions_csv: Path to backtest_predictions.csv
        """
        if summary_csv is None:
            summary_csv = OUTPUT_DIR / "backtest_summary.csv"

        if predictions_csv is None:
            predictions_csv = OUTPUT_DIR / "backtest_predictions.csv"

        self.summary_df = None
        self.predictions_df = None

        if Path(summary_csv).exists():
            self.summary_df = pd.read_csv(summary_csv, index_col=0)

        if Path(predictions_csv).exists():
            self.predictions_df = pd.read_csv(predictions_csv)

    def create_html_report(self, output_file: str = None):
        """Create comprehensive HTML report"""

        if output_file is None:
            output_file = OUTPUT_DIR / "backtest_report.html"

        log_header("Generating Backtest Report")

        html = """
        <html>
        <head>
            <title>NFL Backtest Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                h1 { color: #003366; }
                h2 { color: #0066cc; margin-top: 30px; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th { background-color: #0066cc; color: white; padding: 12px; text-align: left; }
                td { border: 1px solid #ddd; padding: 10px; }
                tr:nth-child(even) { background-color: #f2f2f2; }
                .metric { display: inline-block; margin: 10px; padding: 15px;
                         background: #e7f3ff; border-radius: 8px; min-width: 150px; }
                .metric-label { font-size: 0.9em; color: #666; }
                .metric-value { font-size: 1.5em; font-weight: bold; color: #003366; }
                .positive { color: #28a745; }
                .negative { color: #dc3545; }
                .neutral { color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏈 NFL Backtest Report</h1>
        """

        # Summary statistics
        if self.summary_df is not None and not self.summary_df.empty:
            html += "<h2>📊 Performance Summary</h2>"
            html += self.summary_df.to_html(classes='table')

            # Overall metrics
            total_profit = self.summary_df['Profit_Units'].sum()
            total_games = self.summary_df['Total_Games'].sum()
            avg_accuracy = self.summary_df['Accuracy'].mean()
            avg_roi = self.summary_df['ROI'].mean()

            profit_class = 'positive' if total_profit > 0 else 'negative'

            html += f"""
            <h2>💰 Overall Metrics</h2>
            <div>
                <div class="metric">
                    <div class="metric-label">Total Games</div>
                    <div class="metric-value">{total_games:.0f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Avg Accuracy</div>
                    <div class="metric-value">{avg_accuracy:.1%}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Profit</div>
                    <div class="metric-value {profit_class}">{total_profit:+.1f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Avg ROI</div>
                    <div class="metric-value {profit_class}">{avg_roi:+.1f}%</div>
                </div>
            </div>
            """

        # Predictions breakdown
        if self.predictions_df is not None and not self.predictions_df.empty:
            html += "<h2>🎯 Predictions Breakdown</h2>"

            # Group by season and week
            if 'season' in self.predictions_df.columns and 'week' in self.predictions_df.columns:
                weekly_stats = self.predictions_df.groupby(['season', 'week']).size().reset_index(name='games')
                html += "<h3>Games per Week</h3>"
                html += weekly_stats.to_html(index=False, classes='table')

        # Recommendations
        if self.summary_df is not None and not self.summary_df.empty:
            html += "<h2>📋 Recommendations</h2><ul>"

            # Best markets
            best_markets = self.summary_df[self.summary_df['ROI'] > 0].index.tolist()
            if best_markets:
                html += f"<li><strong>✅ Focus on these markets:</strong> {', '.join(best_markets)}</li>"

            # Markets to avoid
            worst_markets = self.summary_df[self.summary_df['ROI'] < 0].index.tolist()
            if worst_markets:
                html += f"<li><strong>❌ Avoid these markets:</strong> {', '.join(worst_markets)}</li>"

            # High accuracy markets
            high_acc = self.summary_df[self.summary_df['Accuracy'] > 0.55].index.tolist()
            if high_acc:
                html += f"<li><strong>🎯 High accuracy markets:</strong> {', '.join(high_acc)}</li>"

            html += "</ul>"

        html += """
                <p><em>Report generated on """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M') + """</em></p>
            </div>
        </body>
        </html>
        """

        # Save report
        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✅ Saved HTML report to {output_file}")

    def plot_accuracy_by_market(self, output_file: str = None):
        """Plot accuracy comparison across markets"""

        if not HAS_MATPLOTLIB:
            print("⚠️ matplotlib not installed - skipping chart generation")
            return

        if self.summary_df is None or self.summary_df.empty:
            print("⚠️ No summary data available")
            return

        if output_file is None:
            output_file = OUTPUT_DIR / "accuracy_by_market.png"

        fig, ax = plt.subplots(figsize=(10, 6))

        markets = self.summary_df.index.tolist()
        accuracies = self.summary_df['Accuracy'].values

        ax.bar(markets, accuracies, color='#0066cc')
        ax.axhline(y=0.5, color='red', linestyle='--', label='Break-even (50%)')
        ax.set_xlabel('Market')
        ax.set_ylabel('Accuracy')
        ax.set_title('Backtest Accuracy by Market')
        ax.set_ylim(0, 1)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150)
        plt.close()

        print(f"✅ Saved accuracy chart to {output_file}")

    def plot_roi_by_market(self, output_file: str = None):
        """Plot ROI comparison across markets"""

        if not HAS_MATPLOTLIB:
            print("⚠️ matplotlib not installed - skipping chart generation")
            return

        if self.summary_df is None or self.summary_df.empty:
            print("⚠️ No summary data available")
            return

        if output_file is None:
            output_file = OUTPUT_DIR / "roi_by_market.png"

        fig, ax = plt.subplots(figsize=(10, 6))

        markets = self.summary_df.index.tolist()
        rois = self.summary_df['ROI'].values

        colors = ['green' if roi > 0 else 'red' for roi in rois]

        ax.bar(markets, rois, color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.set_xlabel('Market')
        ax.set_ylabel('ROI (%)')
        ax.set_title('Backtest ROI by Market')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150)
        plt.close()

        print(f"✅ Saved ROI chart to {output_file}")

    def generate_all_reports(self):
        """Generate all visualizations and reports"""
        log_header("Generating All Visualizations")

        self.create_html_report()

        if HAS_MATPLOTLIB:
            self.plot_accuracy_by_market()
            self.plot_roi_by_market()
        else:
            print("⚠️ Install matplotlib for chart generation:")
            print("   pip install matplotlib")


def main():
    """Main visualizer"""
    import argparse

    parser = argparse.ArgumentParser(description='Visualize NFL backtest results')
    parser.add_argument('--summary', type=str,
                       help='Path to backtest_summary.csv')
    parser.add_argument('--predictions', type=str,
                       help='Path to backtest_predictions.csv')

    args = parser.parse_args()

    visualizer = NFLBacktestVisualizer(
        summary_csv=args.summary,
        predictions_csv=args.predictions
    )

    visualizer.generate_all_reports()


if __name__ == "__main__":
    main()

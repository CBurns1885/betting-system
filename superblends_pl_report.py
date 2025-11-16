#!/usr/bin/env python3
"""
SuperBlends PL Report Generator
Generates an HTML report of SuperBlends predictions for Premier League (E0)
Excludes O/U 0.5 market for cleaner output
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("outputs") / datetime.now().strftime("%Y-%m-%d")
WEEKLY_BETS_FILE = OUTPUT_DIR / "weekly_bets_full.csv"

def load_superblends():
    """Load and filter SuperBlends predictions for PL"""
    if not WEEKLY_BETS_FILE.exists():
        print(f"❌ Error: {WEEKLY_BETS_FILE} not found!")
        return None

    df = pd.read_csv(WEEKLY_BETS_FILE)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')

    # Filter for Premier League only
    df = df[df["League"] == "E0"].copy()

    if df.empty:
        print("❌ No Premier League matches found in predictions")
        return None

    print(f"✅ Loaded {len(df)} Premier League matches")
    return df

def extract_superblends(df):
    """Extract SuperBlends columns and create market-based view"""
    # Get all SUPERBLEND columns
    sb_cols = [col for col in df.columns if col.startswith("SUPERBLEND_")]

    markets = {}

    for col in sb_cols:
        # Parse column name: SUPERBLEND_MARKET_SELECTION
        parts = col.replace("SUPERBLEND_", "").split("_")

        if col == "SUPERBLEND_OU_0_5_U" or col == "SUPERBLEND_OU_0_5_O":
            # Skip O/U 0.5
            continue

        if len(parts) >= 2:
            market = "_".join(parts[:-1])
            selection = parts[-1]

            if market not in markets:
                markets[market] = {}

            markets[market][col] = {
                'selection': selection,
                'probs': df[col].values
            }

    return markets

def generate_html_report(df, output_path):
    """Generate beautiful HTML report"""
    markets = extract_superblends(df)

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SuperBlends PL Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 15px 50px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .summary-card h3 {{
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .matches {{
            margin-top: 40px;
        }}
        .match {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #e9ecef;
            transition: all 0.3s ease;
        }}
        .match:hover {{
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        .match-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
        }}
        .match-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
        }}
        .match-date {{
            color: #666;
            font-size: 0.95em;
        }}
        .predictions {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .prediction {{
            background: white;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}
        .prediction-label {{
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .prediction-value {{
            font-size: 1.4em;
            font-weight: bold;
            color: #667eea;
        }}
        .high-prob {{
            background: rgba(102, 126, 234, 0.1);
            border-color: #667eea;
        }}
        .high-prob .prediction-value {{
            color: #667eea;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚽ SuperBlends Premier League Report</h1>
            <p>Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="content">
            <div class="summary">
                <div class="summary-card">
                    <h3>Total Matches</h3>
                    <div class="value">{len(df)}</div>
                </div>
                <div class="summary-card">
                    <h3>Market Types</h3>
                    <div class="value">{len(markets)}</div>
                </div>
                <div class="summary-card">
                    <h3>Date Range</h3>
                    <div class="value">{df['Date'].min().strftime('%b %d')} - {df['Date'].max().strftime('%b %d')}</div>
                </div>
            </div>

            <div class="matches">
"""

    # Add match predictions
    for idx, row in df.iterrows():
        home = row.get('HomeTeam', 'N/A')
        away = row.get('AwayTeam', 'N/A')
        date = row.get('Date', 'N/A')
        league = row.get('League', 'E0')

        html += f"""
                <div class="match">
                    <div class="match-header">
                        <div>
                            <div class="match-title">{home} vs {away}</div>
                            <div class="match-date">{date}</div>
                        </div>
                    </div>
                    <div class="predictions">
"""

        # Add top predictions for this match
        predictions = []
        for col in df.columns:
            if col.startswith("SUPERBLEND_") and col != "SUPERBLEND_OU_0_5_U" and col != "SUPERBLEND_OU_0_5_O":
                prob = row[col]
                if prob > 0.4:  # Only show predictions above 40%
                    # Clean up column name
                    label = col.replace("SUPERBLEND_", "").replace("_", " ")
                    predictions.append((label, prob, prob))

        # Sort by probability
        predictions.sort(key=lambda x: x[2], reverse=True)

        for label, prob, _ in predictions[:6]:  # Top 6 predictions
            prob_pct = f"{prob*100:.1f}%"
            high_class = "high-prob" if prob > 0.65 else ""
            html += f"""
                        <div class="prediction {high_class}">
                            <div class="prediction-label">{label}</div>
                            <div class="prediction-value">{prob_pct}</div>
                        </div>
"""

        html += """
                    </div>
                </div>
"""

    html += """
            </div>
        </div>

        <div class="footer">
            <p>🏆 SuperBlends combines multiple ML models and Dixon-Coles for maximum accuracy</p>
            <p>⚠️ Note: O/U 0.5 market excluded for cleaner reporting</p>
        </div>
    </div>
</body>
</html>
"""

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"✅ Saved HTML report: {output_path}")

def main():
    """Main execution"""
    print("="*60)
    print("⚽ SUPERBLENDS PL REPORT GENERATOR")
    print("="*60)

    # Load data
    df = load_superblends()
    if df is None:
        return

    # Generate report
    html_path = OUTPUT_DIR / "superblends_pl_report.html"
    generate_html_report(df, html_path)

    # Also generate CSV with top predictions
    csv_path = OUTPUT_DIR / "superblends_pl_report.csv"

    # Extract top predictions per match
    rows = []
    for idx, row in df.iterrows():
        match_row = {
            'Date': row.get('Date', ''),
            'HomeTeam': row.get('HomeTeam', ''),
            'AwayTeam': row.get('AwayTeam', ''),
        }

        # Get top 3 predictions
        predictions = []
        for col in df.columns:
            if col.startswith("SUPERBLEND_") and col not in ["SUPERBLEND_OU_0_5_U", "SUPERBLEND_OU_0_5_O"]:
                prob = row[col]
                if prob > 0.0:
                    label = col.replace("SUPERBLEND_", "")
                    predictions.append((label, prob))

        predictions.sort(key=lambda x: x[1], reverse=True)

        for i, (label, prob) in enumerate(predictions[:5]):
            match_row[f'Prediction_{i+1}'] = label
            match_row[f'Prob_{i+1}'] = f"{prob*100:.1f}%"

        rows.append(match_row)

    csv_df = pd.DataFrame(rows)
    csv_df.to_csv(csv_path, index=False)
    print(f"✅ Saved CSV report: {csv_path}")

    print("\n" + "="*60)
    print("✅ SuperBlends PL Report Complete!")
    print("="*60)
    print(f"\n📊 Reports saved to: {OUTPUT_DIR}")
    print(f"   • HTML: superblends_pl_report.html")
    print(f"   • CSV: superblends_pl_report.csv")
    print(f"\n💡 Open the HTML file in your browser to view the interactive report")

if __name__ == "__main__":
    main()

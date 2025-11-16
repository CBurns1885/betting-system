#!/usr/bin/env python3
"""
market_output_organizer.py
Organizes prediction outputs by market without filtering anything out.
Keeps ALL markets including Over/Under 0.5, just separates them for easier navigation.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# MARKET DEFINITIONS
# ============================================================================

MARKET_CATEGORIES = {
    'match_result': {
        'name': 'Match Result (1X2)',
        'markets': ['1X2', 'Match_Result', 'FTR', 'Full_Time_Result'],
        'columns': ['Home_Win', 'Draw', 'Away_Win', 'H', 'D', 'A']
    },
    
    'double_chance': {
        'name': 'Double Chance',
        'markets': ['Double_Chance', 'DC', '1X_12_X2'],
        'columns': ['DC_1X', 'DC_12', 'DC_X2', 'Home_Draw', 'Home_Away', 'Draw_Away']
    },
    
    'btts': {
        'name': 'Both Teams to Score',
        'markets': ['BTTS', 'Both_Teams_Score', 'GG', 'BTS'],
        'columns': ['BTTS_Yes', 'BTTS_No', 'Both_Score_Yes', 'Both_Score_No']
    },
    
    'over_under_0_5': {
        'name': 'Over/Under 0.5 Goals',
        'markets': ['Over_0_5', 'Under_0_5', 'O0.5', 'U0.5'],
        'columns': ['Over_0.5', 'Under_0.5', 'O0_5', 'U0_5']
    },
    
    'over_under_1_5': {
        'name': 'Over/Under 1.5 Goals',
        'markets': ['Over_1_5', 'Under_1_5', 'O1.5', 'U1.5'],
        'columns': ['Over_1.5', 'Under_1.5', 'O1_5', 'U1_5']
    },
    
    'over_under_2_5': {
        'name': 'Over/Under 2.5 Goals',
        'markets': ['Over_2_5', 'Under_2_5', 'O2.5', 'U2.5'],
        'columns': ['Over_2.5', 'Under_2.5', 'O2_5', 'U2_5']
    },
    
    'over_under_3_5': {
        'name': 'Over/Under 3.5 Goals',
        'markets': ['Over_3_5', 'Under_3_5', 'O3.5', 'U3.5'],
        'columns': ['Over_3.5', 'Under_3.5', 'O3_5', 'U3_5']
    },
    
    'over_under_4_5': {
        'name': 'Over/Under 4.5 Goals',
        'markets': ['Over_4_5', 'Under_4_5', 'O4.5', 'U4.5'],
        'columns': ['Over_4.5', 'Under_4.5', 'O4_5', 'U4_5']
    },
    
    'over_under_5_5': {
        'name': 'Over/Under 5.5 Goals',
        'markets': ['Over_5_5', 'Under_5_5', 'O5.5', 'U5.5'],
        'columns': ['Over_5.5', 'Under_5.5', 'O5_5', 'U5_5']
    },
    
    'asian_handicap': {
        'name': 'Asian Handicap',
        'markets': ['AH', 'Asian_Handicap', 'Handicap'],
        'columns': ['AH_Home', 'AH_Away', 'Handicap_Home', 'Handicap_Away']
    },
    
    'correct_score': {
        'name': 'Correct Score',
        'markets': ['CS', 'Correct_Score', 'Exact_Score'],
        'columns': ['CS_0_0', 'CS_1_0', 'CS_0_1', 'CS_1_1', 'CS_2_0', 'CS_0_2', 'CS_2_1', 'CS_1_2']
    },
    
    'half_time': {
        'name': 'Half Time Result',
        'markets': ['HT', 'Half_Time', 'HT_Result'],
        'columns': ['HT_Home', 'HT_Draw', 'HT_Away', 'HT_H', 'HT_D', 'HT_A']
    },
    
    'ht_ft': {
        'name': 'Half Time/Full Time',
        'markets': ['HT_FT', 'HTFT', 'Half_Full'],
        'columns': ['HH', 'HD', 'HA', 'DH', 'DD', 'DA', 'AH', 'AD', 'AA']
    },
    
    'corners': {
        'name': 'Corners',
        'markets': ['Corners', 'Total_Corners', 'Corner'],
        'columns': ['Corners_O8_5', 'Corners_O9_5', 'Corners_O10_5', 'Corners_U10_5']
    },
    
    'cards': {
        'name': 'Cards',
        'markets': ['Cards', 'Total_Cards', 'Bookings'],
        'columns': ['Cards_O2_5', 'Cards_O3_5', 'Cards_O4_5', 'Cards_U4_5']
    },
    
    'team_goals': {
        'name': 'Team Goals',
        'markets': ['Team_Goals', 'Home_Goals', 'Away_Goals'],
        'columns': ['Home_O0_5', 'Home_O1_5', 'Home_O2_5', 'Away_O0_5', 'Away_O1_5', 'Away_O2_5']
    },
    
    'clean_sheet': {
        'name': 'Clean Sheet',
        'markets': ['Clean_Sheet', 'CS_Home', 'CS_Away'],
        'columns': ['Home_Clean_Sheet', 'Away_Clean_Sheet', 'Home_CS', 'Away_CS']
    },
    
    'win_to_nil': {
        'name': 'Win to Nil',
        'markets': ['Win_to_Nil', 'WTN'],
        'columns': ['Home_Win_to_Nil', 'Away_Win_to_Nil', 'Home_WTN', 'Away_WTN']
    },
    
    'draw_no_bet': {
        'name': 'Draw No Bet',
        'markets': ['DNB', 'Draw_No_Bet'],
        'columns': ['DNB_Home', 'DNB_Away', 'Home_DNB', 'Away_DNB']
    },
    
    'european_handicap': {
        'name': 'European Handicap',
        'markets': ['EH', 'European_Handicap', 'Handicap_1X2'],
        'columns': ['EH_Home', 'EH_Draw', 'EH_Away']
    }
}

# ============================================================================
# OUTPUT ORGANIZER
# ============================================================================

class MarketOutputOrganizer:
    """Organizes prediction outputs by market"""
    
    def __init__(self, input_file: str, output_dir: Optional[str] = None):
        """
        Initialize the organizer
        
        Args:
            input_file: Path to the main predictions file (CSV)
            output_dir: Directory for organized outputs (default: outputs/YYYY-MM-DD/)
        """
        self.input_file = Path(input_file)
        
        if output_dir is None:
            self.output_dir = Path("outputs") / datetime.now().strftime("%Y-%m-%d")
        else:
            self.output_dir = Path(output_dir)
            
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load predictions
        self.df = pd.read_csv(self.input_file)
        print(f"✅ Loaded {len(self.df)} fixtures from {self.input_file}")
        print(f"📊 Total columns: {len(self.df.columns)}")
        
        # Identify available markets
        self.available_markets = self._identify_markets()
        print(f"🎯 Found {len(self.available_markets)} markets to organize")
        
    def _identify_markets(self) -> Dict[str, List[str]]:
        """Identify which markets are present in the data"""
        available = {}
        
        for market_key, market_info in MARKET_CATEGORIES.items():
            found_columns = []
            
            # Check for any matching columns
            for col in self.df.columns:
                # Check if column matches any of the market patterns
                for pattern in market_info['columns']:
                    if pattern.lower() in col.lower():
                        found_columns.append(col)
                        break
            
            if found_columns:
                available[market_key] = found_columns
                
        return available
    
    def organize_by_market(self):
        """Organize outputs into market-specific folders"""
        print("\n" + "="*60)
        print("ORGANIZING OUTPUTS BY MARKET")
        print("="*60)
        
        # Create summary statistics
        summary_stats = []
        
        for market_key, columns in self.available_markets.items():
            market_info = MARKET_CATEGORIES[market_key]
            market_name = market_info['name']
            
            print(f"\n📁 Processing {market_name}...")
            
            # Create market folder
            market_dir = self.output_dir / market_key
            market_dir.mkdir(exist_ok=True)
            
            # Extract market-specific data
            base_columns = ['Date', 'HomeTeam', 'AwayTeam', 'League']
            
            # Add any fixture identifiers
            for col in ['fixture_id', 'MatchID', 'ID']:
                if col in self.df.columns:
                    base_columns.append(col)
            
            # Get market columns
            market_columns = []
            for col in columns:
                if col in self.df.columns:
                    market_columns.append(col)
            
            if not market_columns:
                print(f"   ⚠️ No valid columns found for {market_name}")
                continue
            
            # Create market-specific dataframe
            market_df = self.df[base_columns + market_columns].copy()
            
            # Save all predictions
            all_predictions_file = market_dir / "all_predictions.csv"
            market_df.to_csv(all_predictions_file, index=False)
            print(f"   ✅ Saved {len(market_df)} predictions to {all_predictions_file}")
            
            # Calculate statistics for this market
            stats = self._calculate_market_stats(market_df, market_columns)
            stats['market'] = market_name
            stats['folder'] = market_key
            summary_stats.append(stats)
            
            # Create value bets (if odds/probabilities available)
            value_bets = self._extract_value_bets(market_df, market_columns)
            if value_bets is not None and not value_bets.empty:
                value_bets_file = market_dir / "value_bets.csv"
                value_bets.to_csv(value_bets_file, index=False)
                print(f"   ✅ Found {len(value_bets)} value bets")
            
            # Create confidence-based files
            self._create_confidence_files(market_df, market_columns, market_dir)
            
            # Generate market report
            self._generate_market_report(market_df, market_columns, stats, market_dir, market_name)
        
        # Create master summary
        self._create_master_summary(summary_stats)
        
        print("\n" + "="*60)
        print("✅ OUTPUT ORGANIZATION COMPLETE!")
        print("="*60)
        print(f"\n📁 All outputs saved to: {self.output_dir}")
        print(f"📊 Markets organized: {len(self.available_markets)}")
        
    def _calculate_market_stats(self, df: pd.DataFrame, columns: List[str]) -> Dict:
        """Calculate statistics for a market"""
        stats = {
            'total_fixtures': len(df),
            'columns': len(columns),
            'column_names': columns
        }
        
        # Calculate prediction distribution if possible
        if columns:
            first_col = columns[0]
            if first_col in df.columns:
                # Get distribution of predictions
                if df[first_col].dtype in ['float64', 'int64']:
                    stats['mean_probability'] = df[first_col].mean()
                    stats['std_probability'] = df[first_col].std()
                    stats['min_probability'] = df[first_col].min()
                    stats['max_probability'] = df[first_col].max()
        
        return stats
    
    def _extract_value_bets(self, df: pd.DataFrame, columns: List[str]) -> Optional[pd.DataFrame]:
        """Extract value bets based on expected value"""
        value_bets = []
        
        # Look for probability and odds columns
        for col in columns:
            prob_col = col
            odds_col = None
            
            # Try to find matching odds column
            for potential_odds in df.columns:
                if 'odds' in potential_odds.lower() and col.split('_')[0] in potential_odds:
                    odds_col = potential_odds
                    break
            
            if odds_col and odds_col in df.columns and prob_col in df.columns:
                # Calculate expected value
                try:
                    df['EV'] = (df[prob_col] * df[odds_col]) - 1
                    
                    # Filter for positive EV
                    value_df = df[df['EV'] > 0.05].copy()  # 5% edge minimum
                    
                    if not value_df.empty:
                        value_df['Market'] = col
                        value_df['Probability'] = df[prob_col]
                        value_df['Odds'] = df[odds_col]
                        value_bets.append(value_df[['Date', 'HomeTeam', 'AwayTeam', 'Market', 'Probability', 'Odds', 'EV']])
                except:
                    pass
        
        if value_bets:
            return pd.concat(value_bets, ignore_index=True)
        
        return None
    
    def _create_confidence_files(self, df: pd.DataFrame, columns: List[str], output_dir: Path):
        """Create files separated by confidence levels"""
        # Look for confidence column
        confidence_col = None
        for col in df.columns:
            if 'confidence' in col.lower():
                confidence_col = col
                break
        
        if confidence_col:
            # Get unique confidence levels
            confidence_levels = df[confidence_col].unique()
            
            for level in confidence_levels:
                if pd.notna(level):
                    level_df = df[df[confidence_col] == level]
                    
                    if not level_df.empty:
                        filename = f"confidence_{str(level).lower().replace(' ', '_')}.csv"
                        level_df.to_csv(output_dir / filename, index=False)
                        print(f"   📊 {level}: {len(level_df)} fixtures")
    
    def _generate_market_report(self, df: pd.DataFrame, columns: List[str], 
                               stats: Dict, output_dir: Path, market_name: str):
        """Generate HTML report for a market"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{market_name} - Predictions Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 3px solid #4CAF50;
                    padding-bottom: 10px;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background: #f9f9f9;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 2em;
                    font-weight: bold;
                    color: #4CAF50;
                }}
                .stat-label {{
                    color: #666;
                    margin-top: 5px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th {{
                    background: #4CAF50;
                    color: white;
                    padding: 10px;
                    text-align: left;
                }}
                td {{
                    padding: 8px;
                    border-bottom: 1px solid #ddd;
                }}
                tr:hover {{
                    background: #f5f5f5;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 {market_name}</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_fixtures']}</div>
                        <div class="stat-label">Total Fixtures</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(columns)}</div>
                        <div class="stat-label">Predictions Types</div>
                    </div>
        """
        
        # Add probability stats if available
        if 'mean_probability' in stats:
            html += f"""
                    <div class="stat-card">
                        <div class="stat-value">{stats['mean_probability']:.1%}</div>
                        <div class="stat-label">Average Probability</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['max_probability']:.1%}</div>
                        <div class="stat-label">Highest Confidence</div>
                    </div>
            """
        
        html += """
                </div>
                
                <h2>📊 Sample Predictions</h2>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Fixture</th>
        """
        
        # Add column headers
        for col in columns[:3]:  # Show first 3 prediction columns
            html += f"<th>{col.replace('_', ' ')}</th>"
        
        html += "</tr>"
        
        # Add sample rows (first 10)
        for idx, row in df.head(10).iterrows():
            html += f"""
                    <tr>
                        <td>{row['Date']}</td>
                        <td>{row['HomeTeam']} vs {row['AwayTeam']}</td>
            """
            
            for col in columns[:3]:
                if col in df.columns:
                    value = row[col]
                    if isinstance(value, float):
                        html += f"<td>{value:.3f}</td>"
                    else:
                        html += f"<td>{value}</td>"
            
            html += "</tr>"
        
        html += """
                </table>
                
                <h2>📁 Files in this folder</h2>
                <ul>
                    <li><strong>all_predictions.csv</strong> - Complete predictions for all fixtures</li>
                    <li><strong>value_bets.csv</strong> - Positive expected value selections</li>
                    <li><strong>confidence_*.csv</strong> - Predictions by confidence level</li>
                    <li><strong>report.html</strong> - This report</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Save report
        report_file = output_dir / "report.html"
        with open(report_file, 'w') as f:
            f.write(html)
    
    def _create_master_summary(self, summary_stats: List[Dict]):
        """Create master summary dashboard"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Predictions Master Dashboard</title>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    max-width: 1400px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }
                h1 {
                    color: #333;
                    text-align: center;
                    font-size: 2.5em;
                }
                .market-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }
                .market-card {
                    background: #f9f9f9;
                    border-radius: 10px;
                    padding: 20px;
                    transition: transform 0.3s;
                    cursor: pointer;
                }
                .market-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 5px 20px rgba(0,0,0,0.1);
                }
                .market-title {
                    font-size: 1.3em;
                    font-weight: bold;
                    color: #4CAF50;
                    margin-bottom: 10px;
                }
                .market-stat {
                    display: flex;
                    justify-content: space-between;
                    margin: 8px 0;
                    padding: 5px 0;
                    border-bottom: 1px solid #e0e0e0;
                }
                .market-link {
                    text-decoration: none;
                    color: inherit;
                }
                .summary-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                .summary-table th {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px;
                    text-align: left;
                }
                .summary-table td {
                    padding: 10px;
                    border-bottom: 1px solid #e0e0e0;
                }
                .summary-table tr:hover {
                    background: #f5f5f5;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Football Predictions Dashboard</h1>
                <p style="text-align: center; color: #666;">
        """
        
        html += f"""
                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
                    Total Markets: {len(summary_stats)}<br>
                    Output Directory: {self.output_dir}
                </p>
                
                <h2>📊 Markets Overview</h2>
                <div class="market-grid">
        """
        
        # Add market cards
        for stats in summary_stats:
            folder = stats['folder']
            
            # Determine icon based on market
            if 'over_under' in folder:
                icon = '⚽'
            elif 'btts' in folder:
                icon = '🥅'
            elif 'match_result' in folder:
                icon = '🏆'
            elif 'corner' in folder:
                icon = '🚩'
            elif 'card' in folder:
                icon = '🟨'
            else:
                icon = '📊'
            
            html += f"""
                <a href="{folder}/report.html" class="market-link">
                    <div class="market-card">
                        <div class="market-title">{icon} {stats['market']}</div>
                        <div class="market-stat">
                            <span>Fixtures:</span>
                            <strong>{stats['total_fixtures']}</strong>
                        </div>
                        <div class="market-stat">
                            <span>Predictions:</span>
                            <strong>{stats['columns']}</strong>
                        </div>
            """
            
            if 'mean_probability' in stats:
                html += f"""
                        <div class="market-stat">
                            <span>Avg Confidence:</span>
                            <strong>{stats['mean_probability']:.1%}</strong>
                        </div>
                """
            
            html += """
                        <div style="margin-top: 15px; text-align: center; color: #666; font-size: 0.9em;">
                            Click to view details →
                        </div>
                    </div>
                </a>
            """
        
        html += """
                </div>
                
                <h2>📋 Complete Market List</h2>
                <table class="summary-table">
                    <tr>
                        <th>Market</th>
                        <th>Folder</th>
                        <th>Fixtures</th>
                        <th>Files</th>
                        <th>Action</th>
                    </tr>
        """
        
        # Add summary table
        for stats in sorted(summary_stats, key=lambda x: x['market']):
            html += f"""
                    <tr>
                        <td><strong>{stats['market']}</strong></td>
                        <td>{stats['folder']}/</td>
                        <td>{stats['total_fixtures']}</td>
                        <td>all_predictions.csv, value_bets.csv, report.html</td>
                        <td><a href="{stats['folder']}/report.html">View Report</a></td>
                    </tr>
            """
        
        html += """
                </table>
                
                <h2>🎯 Quick Links</h2>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
                    <a href="match_result/all_predictions.csv" style="text-decoration: none;">
                        <div style="background: #e8f5e9; padding: 20px; border-radius: 8px; text-align: center;">
                            <strong>Match Results</strong><br>
                            Home/Draw/Away
                        </div>
                    </a>
                    <a href="btts/all_predictions.csv" style="text-decoration: none;">
                        <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; text-align: center;">
                            <strong>BTTS</strong><br>
                            Both Teams to Score
                        </div>
                    </a>
                    <a href="over_under_2_5/all_predictions.csv" style="text-decoration: none;">
                        <div style="background: #fce4ec; padding: 20px; border-radius: 8px; text-align: center;">
                            <strong>Goals O/U 2.5</strong><br>
                            Most Popular Market
                        </div>
                    </a>
                </div>
                
                <h2>📁 Directory Structure</h2>
                <pre style="background: #f5f5f5; padding: 20px; border-radius: 8px; overflow-x: auto;">
        """
        
        html += f"{self.output_dir}/\n"
        html += "├── 📊 master_dashboard.html (this file)\n"
        
        for stats in sorted(summary_stats, key=lambda x: x['folder']):
            folder = stats['folder']
            if 'over_under' in folder:
                icon = '⚽'
            elif 'btts' in folder:
                icon = '🥅'
            elif 'match' in folder:
                icon = '🏆'
            else:
                icon = '📁'
            
            html += f"├── {icon} {folder}/\n"
            html += f"│   ├── all_predictions.csv ({stats['total_fixtures']} fixtures)\n"
            html += f"│   ├── value_bets.csv\n"
            html += f"│   ├── confidence_*.csv\n"
            html += f"│   └── report.html\n"
        
        html += """
                </pre>
            </div>
        </body>
        </html>
        """
        
        # Save master dashboard
        dashboard_file = self.output_dir / "master_dashboard.html"
        with open(dashboard_file, 'w') as f:
            f.write(html)
        
        print(f"\n📊 Master dashboard saved to: {dashboard_file}")

# ============================================================================
# INTEGRATION FUNCTIONS
# ============================================================================

def integrate_with_pipeline(predictions_file: str, output_dir: Optional[str] = None):
    """
    Integrate market separator with existing pipeline
    
    Args:
        predictions_file: Path to your weekly predictions CSV
        output_dir: Where to save organized outputs
    """
    organizer = MarketOutputOrganizer(predictions_file, output_dir)
    organizer.organize_by_market()
    
    return organizer.output_dir

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║              MARKET OUTPUT ORGANIZER                          ║
    ║                                                                ║
    ║  Separates predictions into organized market folders          ║
    ║  Keeps ALL markets including Over/Under 0.5                   ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        
        if len(sys.argv) > 2:
            output_dir = sys.argv[2]
        else:
            output_dir = None
        
        print(f"\n📊 Input file: {input_file}")
        
        # Run organizer
        organizer = MarketOutputOrganizer(input_file, output_dir)
        organizer.organize_by_market()
        
        print(f"\n✅ SUCCESS!")
        print(f"📁 Organized outputs saved to: {organizer.output_dir}")
        print(f"📊 Open master_dashboard.html to navigate all markets")
        
    else:
        print("""
        Usage:
            python market_output_organizer.py <predictions_file> [output_dir]
        
        Example:
            python market_output_organizer.py weekly_bets.csv
            python market_output_organizer.py predictions.csv outputs/organized/
        
        This will:
        1. Read your predictions CSV
        2. Identify all markets (O/U 0.5, 1.5, 2.5, BTTS, etc.)
        3. Create a separate folder for each market
        4. Save market-specific CSVs in each folder
        5. Generate reports and a master dashboard
        
        ALL markets are retained - nothing is filtered out!
        """)

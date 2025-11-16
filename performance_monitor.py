#!/usr/bin/env python3
"""
performance_monitor.py
Real-time monitoring and performance tracking for the prediction system
Tracks accuracy, ROI, and provides insights for improvement
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Optional imports for visualization
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    print("Install plotly for interactive charts: pip install plotly")

# ============================================================================
# DATABASE SCHEMA
# ============================================================================

SCHEMA = """
-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_date DATE NOT NULL,
    fixture_date DATE NOT NULL,
    fixture_id INTEGER,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    league TEXT,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    odds REAL,
    probability REAL,
    expected_value REAL,
    kelly_stake REAL,
    confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Results table
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_id INTEGER,
    fixture_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    result TEXT,  -- 'H', 'D', 'A'
    total_goals INTEGER,
    btts INTEGER,  -- 0 or 1
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bets table (tracks actual bets placed)
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER,
    fixture_id INTEGER,
    bet_date DATE NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    odds REAL NOT NULL,
    stake REAL NOT NULL,
    result TEXT,  -- 'WON', 'LOST', 'VOID', 'PENDING'
    profit REAL,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    market TEXT,
    total_predictions INTEGER,
    correct_predictions INTEGER,
    accuracy REAL,
    total_stakes REAL,
    total_returns REAL,
    roi REAL,
    avg_odds REAL,
    avg_expected_value REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_predictions_fixture ON predictions(fixture_id);
CREATE INDEX IF NOT EXISTS idx_results_fixture ON results(fixture_id);
CREATE INDEX IF NOT EXISTS idx_bets_date ON bets(bet_date);
CREATE INDEX IF NOT EXISTS idx_performance_date ON performance_metrics(date);
"""

# ============================================================================
# PERFORMANCE MONITOR CLASS
# ============================================================================

class PerformanceMonitor:
    """Monitor and track system performance"""
    
    def __init__(self, db_path: str = "performance.db"):
        """Initialize performance monitor"""
        self.db_path = Path(db_path)
        self.conn = None
        self._init_database()
        
    def _init_database(self):
        """Initialize database with schema"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        print(f"✅ Performance database initialized: {self.db_path}")
    
    def log_predictions(self, predictions_df: pd.DataFrame):
        """Log predictions to database"""
        records_added = 0
        
        for idx, row in predictions_df.iterrows():
            # Extract predictions from row
            predictions = row.get('predictions', {})
            recommended_bets = predictions.get('recommended_bets', [])
            
            for bet in recommended_bets:
                try:
                    self.conn.execute("""
                        INSERT INTO predictions (
                            prediction_date, fixture_date, fixture_id,
                            home_team, away_team, league,
                            market, selection, odds, probability,
                            expected_value, kelly_stake, confidence
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        datetime.now().date(),
                        row.get('Date'),
                        row.get('fixture_id'),
                        row.get('HomeTeam'),
                        row.get('AwayTeam'),
                        row.get('League'),
                        bet.get('market'),
                        bet.get('selection'),
                        bet.get('odds'),
                        bet.get('probability'),
                        bet.get('expected_value'),
                        bet.get('kelly_stake'),
                        bet.get('confidence')
                    ))
                    records_added += 1
                except Exception as e:
                    print(f"Error logging prediction: {e}")
        
        self.conn.commit()
        print(f"✅ Logged {records_added} predictions")
        
    def update_results(self, results_df: pd.DataFrame):
        """Update results for fixtures"""
        records_updated = 0
        
        for idx, row in results_df.iterrows():
            try:
                # Calculate derived fields
                home_score = row.get('FTHG', row.get('home_score', 0))
                away_score = row.get('FTAG', row.get('away_score', 0))
                
                if home_score > away_score:
                    result = 'H'
                elif away_score > home_score:
                    result = 'A'
                else:
                    result = 'D'
                
                total_goals = home_score + away_score
                btts = 1 if home_score > 0 and away_score > 0 else 0
                
                self.conn.execute("""
                    INSERT OR REPLACE INTO results (
                        fixture_id, fixture_date, home_team, away_team,
                        home_score, away_score, result, total_goals, btts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get('fixture_id'),
                    row.get('Date'),
                    row.get('HomeTeam'),
                    row.get('AwayTeam'),
                    home_score,
                    away_score,
                    result,
                    total_goals,
                    btts
                ))
                records_updated += 1
                
            except Exception as e:
                print(f"Error updating result: {e}")
        
        self.conn.commit()
        print(f"✅ Updated {records_updated} results")
        
        # Update bet results
        self._update_bet_results()
    
    def _update_bet_results(self):
        """Update bet results based on fixture results"""
        cursor = self.conn.cursor()
        
        # Get pending bets
        cursor.execute("""
            SELECT b.id, b.fixture_id, b.market, b.selection, b.odds, b.stake,
                   r.result, r.total_goals, r.btts, r.home_score, r.away_score
            FROM bets b
            JOIN results r ON b.fixture_id = r.fixture_id
            WHERE b.result = 'PENDING' OR b.result IS NULL
        """)
        
        pending_bets = cursor.fetchall()
        
        for bet in pending_bets:
            bet_id, fixture_id, market, selection, odds, stake = bet[:6]
            result, total_goals, btts, home_score, away_score = bet[6:]
            
            # Determine if bet won
            bet_won = self._check_bet_result(
                market, selection, result, total_goals, btts, home_score, away_score
            )
            
            # Update bet result
            if bet_won:
                profit = (odds - 1) * stake
                bet_result = 'WON'
            else:
                profit = -stake
                bet_result = 'LOST'
            
            cursor.execute("""
                UPDATE bets 
                SET result = ?, profit = ?
                WHERE id = ?
            """, (bet_result, profit, bet_id))
        
        self.conn.commit()
        print(f"✅ Updated {len(pending_bets)} bet results")
    
    def _check_bet_result(self, market: str, selection: str, result: str, 
                         total_goals: int, btts: int, home_score: int, away_score: int) -> bool:
        """Check if a bet won based on the result"""
        market_lower = market.lower()
        
        # Match Result
        if 'match' in market_lower and 'result' in market_lower:
            if selection == 'Home' and result == 'H':
                return True
            elif selection == 'Draw' and result == 'D':
                return True
            elif selection == 'Away' and result == 'A':
                return True
        
        # Over/Under
        elif 'over' in market_lower or 'under' in market_lower:
            if 'over' in selection.lower():
                line = float(selection.split()[-1])
                return total_goals > line
            elif 'under' in selection.lower():
                line = float(selection.split()[-1])
                return total_goals < line
        
        # BTTS
        elif 'both' in market_lower and 'score' in market_lower:
            if selection == 'Yes':
                return btts == 1
            elif selection == 'No':
                return btts == 0
        
        # Asian Handicap
        elif 'asian' in market_lower or 'handicap' in market_lower:
            # Complex logic for Asian Handicap
            # Simplified version
            if 'home' in selection.lower():
                handicap = float(selection.split()[-1])
                return (home_score + handicap) > away_score
            elif 'away' in selection.lower():
                handicap = float(selection.split()[-1])
                return (away_score + handicap) > home_score
        
        # Correct Score
        elif 'correct' in market_lower and 'score' in market_lower:
            score_pred = selection.replace(':', '-')
            actual_score = f"{home_score}-{away_score}"
            return score_pred == actual_score
        
        return False
    
    def calculate_performance_metrics(self, period_days: int = 30) -> Dict:
        """Calculate performance metrics for a period"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        cursor = self.conn.cursor()
        
        # Overall performance
        cursor.execute("""
            SELECT 
                COUNT(*) as total_bets,
                SUM(CASE WHEN result = 'WON' THEN 1 ELSE 0 END) as won_bets,
                SUM(stake) as total_stakes,
                SUM(profit) as total_profit,
                AVG(odds) as avg_odds
            FROM bets
            WHERE bet_date >= ? AND result IN ('WON', 'LOST')
        """, (start_date,))
        
        overall = cursor.fetchone()
        
        if overall[0] > 0:
            metrics = {
                'period_days': period_days,
                'total_bets': overall[0],
                'won_bets': overall[1],
                'win_rate': overall[1] / overall[0] if overall[0] > 0 else 0,
                'total_stakes': overall[2] or 0,
                'total_profit': overall[3] or 0,
                'roi': (overall[3] / overall[2] * 100) if overall[2] else 0,
                'avg_odds': overall[4] or 0
            }
        else:
            metrics = {
                'period_days': period_days,
                'total_bets': 0,
                'won_bets': 0,
                'win_rate': 0,
                'total_stakes': 0,
                'total_profit': 0,
                'roi': 0,
                'avg_odds': 0
            }
        
        # Performance by market
        cursor.execute("""
            SELECT 
                market,
                COUNT(*) as bets,
                SUM(CASE WHEN result = 'WON' THEN 1 ELSE 0 END) as wins,
                SUM(profit) as profit,
                SUM(stake) as stakes
            FROM bets
            WHERE bet_date >= ? AND result IN ('WON', 'LOST')
            GROUP BY market
            ORDER BY profit DESC
        """, (start_date,))
        
        market_performance = []
        for row in cursor.fetchall():
            market_performance.append({
                'market': row[0],
                'bets': row[1],
                'wins': row[2],
                'win_rate': row[2] / row[1] if row[1] > 0 else 0,
                'profit': row[3],
                'roi': (row[3] / row[4] * 100) if row[4] else 0
            })
        
        metrics['by_market'] = market_performance
        
        # Performance by confidence
        cursor.execute("""
            SELECT 
                p.confidence,
                COUNT(b.id) as bets,
                SUM(CASE WHEN b.result = 'WON' THEN 1 ELSE 0 END) as wins,
                SUM(b.profit) as profit
            FROM bets b
            JOIN predictions p ON b.prediction_id = p.id
            WHERE b.bet_date >= ? AND b.result IN ('WON', 'LOST')
            GROUP BY p.confidence
        """, (start_date,))
        
        confidence_performance = []
        for row in cursor.fetchall():
            confidence_performance.append({
                'confidence': row[0],
                'bets': row[1],
                'wins': row[2],
                'win_rate': row[2] / row[1] if row[1] > 0 else 0,
                'profit': row[3]
            })
        
        metrics['by_confidence'] = confidence_performance
        
        return metrics
    
    def generate_performance_report(self, output_path: Optional[Path] = None) -> str:
        """Generate comprehensive performance report"""
        if output_path is None:
            output_path = Path("outputs") / f"performance_report_{datetime.now().strftime('%Y%m%d')}.html"
        
        # Calculate metrics for different periods
        metrics_7d = self.calculate_performance_metrics(7)
        metrics_30d = self.calculate_performance_metrics(30)
        metrics_90d = self.calculate_performance_metrics(90)
        
        # Generate HTML report
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Report - {datetime.now().strftime('%Y-%m-%d')}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                h1 {{
                    color: #333;
                    text-align: center;
                    font-size: 2.5em;
                    margin-bottom: 30px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }}
                .metric-card {{
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    transition: transform 0.3s;
                }}
                .metric-card:hover {{
                    transform: translateY(-5px);
                }}
                .metric-value {{
                    font-size: 2em;
                    font-weight: bold;
                    color: #4a5568;
                    margin: 10px 0;
                }}
                .metric-label {{
                    color: #718096;
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .positive {{ color: #48bb78; }}
                .negative {{ color: #f56565; }}
                .neutral {{ color: #4299e1; }}
                
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px;
                    text-align: left;
                }}
                td {{
                    padding: 10px;
                    border-bottom: 1px solid #e2e8f0;
                }}
                tr:hover {{
                    background: #f7fafc;
                }}
                
                .chart-container {{
                    margin: 30px 0;
                    padding: 20px;
                    background: #f7fafc;
                    border-radius: 10px;
                }}
                
                .period-selector {{
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    margin: 20px 0;
                }}
                .period-btn {{
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    background: #667eea;
                    color: white;
                    cursor: pointer;
                    transition: background 0.3s;
                }}
                .period-btn:hover {{
                    background: #764ba2;
                }}
                .period-btn.active {{
                    background: #764ba2;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Performance Report</h1>
                <p style="text-align: center; color: #718096;">
                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
                </p>
                
                <div class="period-selector">
                    <button class="period-btn active">Last 7 Days</button>
                    <button class="period-btn">Last 30 Days</button>
                    <button class="period-btn">Last 90 Days</button>
                </div>
                
                <h2>📊 Last 30 Days Overview</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">Total Bets</div>
                        <div class="metric-value neutral">{metrics_30d['total_bets']}</div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value {'positive' if metrics_30d['win_rate'] > 0.55 else 'negative'}">
                            {metrics_30d['win_rate']:.1%}
                        </div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">ROI</div>
                        <div class="metric-value {'positive' if metrics_30d['roi'] > 0 else 'negative'}">
                            {metrics_30d['roi']:.1f}%
                        </div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Total Profit</div>
                        <div class="metric-value {'positive' if metrics_30d['total_profit'] > 0 else 'negative'}">
                            €{metrics_30d['total_profit']:.2f}
                        </div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Avg Odds</div>
                        <div class="metric-value neutral">{metrics_30d['avg_odds']:.2f}</div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="metric-label">Total Stakes</div>
                        <div class="metric-value neutral">€{metrics_30d['total_stakes']:.2f}</div>
                    </div>
                </div>
                
                <h2>🎲 Performance by Market</h2>
                <table>
                    <tr>
                        <th>Market</th>
                        <th>Bets</th>
                        <th>Wins</th>
                        <th>Win Rate</th>
                        <th>Profit</th>
                        <th>ROI</th>
                    </tr>
        """
        
        for market in metrics_30d.get('by_market', []):
            roi_class = 'positive' if market['roi'] > 0 else 'negative'
            html += f"""
                    <tr>
                        <td><strong>{market['market']}</strong></td>
                        <td>{market['bets']}</td>
                        <td>{market['wins']}</td>
                        <td>{market['win_rate']:.1%}</td>
                        <td class="{roi_class}">€{market['profit']:.2f}</td>
                        <td class="{roi_class}">{market['roi']:.1f}%</td>
                    </tr>
            """
        
        html += """
                </table>
                
                <h2>🎯 Performance by Confidence</h2>
                <table>
                    <tr>
                        <th>Confidence</th>
                        <th>Bets</th>
                        <th>Wins</th>
                        <th>Win Rate</th>
                        <th>Profit</th>
                    </tr>
        """
        
        for conf in metrics_30d.get('by_confidence', []):
            profit_class = 'positive' if conf['profit'] > 0 else 'negative'
            html += f"""
                    <tr>
                        <td><strong>{conf['confidence'] or 'N/A'}</strong></td>
                        <td>{conf['bets']}</td>
                        <td>{conf['wins']}</td>
                        <td>{conf['win_rate']:.1%}</td>
                        <td class="{profit_class}">€{conf['profit']:.2f}</td>
                    </tr>
            """
        
        html += """
                </table>
                
                <h2>📈 Period Comparison</h2>
                <table>
                    <tr>
                        <th>Period</th>
                        <th>Bets</th>
                        <th>Win Rate</th>
                        <th>ROI</th>
                        <th>Profit</th>
                    </tr>
                    <tr>
                        <td><strong>Last 7 Days</strong></td>
                        <td>{}</td>
                        <td>{:.1%}</td>
                        <td class="{}">{:.1f}%</td>
                        <td class="{}">€{:.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>Last 30 Days</strong></td>
                        <td>{}</td>
                        <td>{:.1%}</td>
                        <td class="{}">{:.1f}%</td>
                        <td class="{}">€{:.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>Last 90 Days</strong></td>
                        <td>{}</td>
                        <td>{:.1%}</td>
                        <td class="{}">{:.1f}%</td>
                        <td class="{}">€{:.2f}</td>
                    </tr>
                </table>
        """.format(
            metrics_7d['total_bets'],
            metrics_7d['win_rate'],
            'positive' if metrics_7d['roi'] > 0 else 'negative',
            metrics_7d['roi'],
            'positive' if metrics_7d['total_profit'] > 0 else 'negative',
            metrics_7d['total_profit'],
            
            metrics_30d['total_bets'],
            metrics_30d['win_rate'],
            'positive' if metrics_30d['roi'] > 0 else 'negative',
            metrics_30d['roi'],
            'positive' if metrics_30d['total_profit'] > 0 else 'negative',
            metrics_30d['total_profit'],
            
            metrics_90d['total_bets'],
            metrics_90d['win_rate'],
            'positive' if metrics_90d['roi'] > 0 else 'negative',
            metrics_90d['roi'],
            'positive' if metrics_90d['total_profit'] > 0 else 'negative',
            metrics_90d['total_profit']
        )
        
        # Add insights section
        html += self._generate_insights_section(metrics_30d)
        
        html += """
            </div>
        </body>
        </html>
        """
        
        # Save report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html)
        
        print(f"✅ Performance report saved to {output_path}")
        return str(output_path)
    
    def _generate_insights_section(self, metrics: Dict) -> str:
        """Generate insights based on performance metrics"""
        insights = []
        
        # Win rate insight
        if metrics['win_rate'] > 0.60:
            insights.append(("✅", "Excellent win rate above 60%", "Keep current strategy"))
        elif metrics['win_rate'] > 0.52:
            insights.append(("👍", "Good win rate above break-even", "Consider increasing stakes"))
        else:
            insights.append(("⚠️", "Win rate below profitable threshold", "Review selection criteria"))
        
        # ROI insight
        if metrics['roi'] > 20:
            insights.append(("🚀", "Outstanding ROI above 20%", "System performing excellently"))
        elif metrics['roi'] > 5:
            insights.append(("📈", "Positive ROI showing profit", "Maintain discipline"))
        else:
            insights.append(("📉", "Negative or low ROI", "Reduce stakes and review"))
        
        # Market insights
        if metrics.get('by_market'):
            best_market = max(metrics['by_market'], key=lambda x: x['roi'])
            worst_market = min(metrics['by_market'], key=lambda x: x['roi'])
            
            if best_market['roi'] > 10:
                insights.append(("💰", f"Best market: {best_market['market']}", f"ROI: {best_market['roi']:.1f}%"))
            
            if worst_market['roi'] < -10:
                insights.append(("❌", f"Worst market: {worst_market['market']}", f"Consider avoiding"))
        
        html = """
            <h2>💡 Insights & Recommendations</h2>
            <div style="background: #f7fafc; padding: 20px; border-radius: 10px;">
        """
        
        for icon, title, desc in insights:
            html += f"""
                <div style="margin: 15px 0; padding: 15px; background: white; border-radius: 5px; border-left: 4px solid #667eea;">
                    <div style="font-size: 1.2em; margin-bottom: 5px;">
                        {icon} <strong>{title}</strong>
                    </div>
                    <div style="color: #718096;">{desc}</div>
                </div>
            """
        
        html += """
            </div>
        """
        
        return html
    
    def create_interactive_dashboard(self):
        """Create interactive dashboard with Plotly"""
        if not HAS_PLOTLY:
            print("❌ Plotly not installed. Run: pip install plotly")
            return
        
        # Get data for charts
        cursor = self.conn.cursor()
        
        # Daily profit chart
        cursor.execute("""
            SELECT 
                DATE(bet_date) as date,
                SUM(profit) as daily_profit,
                COUNT(*) as daily_bets
            FROM bets
            WHERE result IN ('WON', 'LOST')
            GROUP BY DATE(bet_date)
            ORDER BY date
        """)
        
        daily_data = pd.DataFrame(cursor.fetchall(), columns=['date', 'profit', 'bets'])
        daily_data['cumulative_profit'] = daily_data['profit'].cumsum()
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Cumulative Profit', 'Win Rate by Market', 
                          'Daily Bets', 'ROI Trend'),
            specs=[[{'type': 'scatter'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'scatter'}]]
        )
        
        # Cumulative profit line
        fig.add_trace(
            go.Scatter(
                x=daily_data['date'],
                y=daily_data['cumulative_profit'],
                mode='lines',
                name='Cumulative Profit',
                line=dict(color='#667eea', width=3)
            ),
            row=1, col=1
        )
        
        # Win rate by market
        cursor.execute("""
            SELECT 
                market,
                COUNT(*) as bets,
                SUM(CASE WHEN result = 'WON' THEN 1 ELSE 0 END) as wins
            FROM bets
            WHERE result IN ('WON', 'LOST')
            GROUP BY market
        """)
        
        market_data = pd.DataFrame(cursor.fetchall(), columns=['market', 'bets', 'wins'])
        market_data['win_rate'] = market_data['wins'] / market_data['bets'] * 100
        
        fig.add_trace(
            go.Bar(
                x=market_data['market'],
                y=market_data['win_rate'],
                name='Win Rate %',
                marker_color='#764ba2'
            ),
            row=1, col=2
        )
        
        # Daily bets
        fig.add_trace(
            go.Bar(
                x=daily_data['date'],
                y=daily_data['bets'],
                name='Daily Bets',
                marker_color='#48bb78'
            ),
            row=2, col=1
        )
        
        # ROI trend
        cursor.execute("""
            SELECT 
                DATE(bet_date) as date,
                SUM(profit) as profit,
                SUM(stake) as stakes
            FROM bets
            WHERE result IN ('WON', 'LOST')
            GROUP BY DATE(bet_date)
            ORDER BY date
        """)
        
        roi_data = pd.DataFrame(cursor.fetchall(), columns=['date', 'profit', 'stakes'])
        roi_data['roi'] = (roi_data['profit'] / roi_data['stakes'] * 100).fillna(0)
        roi_data['roi_ma'] = roi_data['roi'].rolling(window=7, min_periods=1).mean()
        
        fig.add_trace(
            go.Scatter(
                x=roi_data['date'],
                y=roi_data['roi_ma'],
                mode='lines',
                name='7-Day MA ROI',
                line=dict(color='#f56565', width=2)
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title_text="Performance Dashboard",
            showlegend=False,
            height=800,
            template='plotly_white'
        )
        
        # Save dashboard
        output_path = Path("outputs") / f"dashboard_{datetime.now().strftime('%Y%m%d')}.html"
        fig.write_html(output_path)
        
        print(f"✅ Interactive dashboard saved to {output_path}")
        return str(output_path)
    
    def get_best_performing_strategies(self, min_bets: int = 10) -> pd.DataFrame:
        """Get best performing betting strategies"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.market,
                p.confidence,
                COUNT(b.id) as bets,
                SUM(CASE WHEN b.result = 'WON' THEN 1 ELSE 0 END) as wins,
                AVG(b.odds) as avg_odds,
                SUM(b.profit) as total_profit,
                SUM(b.stake) as total_stakes,
                (SUM(b.profit) / SUM(b.stake) * 100) as roi
            FROM bets b
            JOIN predictions p ON b.prediction_id = p.id
            WHERE b.result IN ('WON', 'LOST')
            GROUP BY p.market, p.confidence
            HAVING COUNT(b.id) >= ?
            ORDER BY roi DESC
            LIMIT 20
        """, (min_bets,))
        
        strategies = pd.DataFrame(cursor.fetchall(), columns=[
            'market', 'confidence', 'bets', 'wins', 
            'avg_odds', 'total_profit', 'total_stakes', 'roi'
        ])
        
        strategies['win_rate'] = strategies['wins'] / strategies['bets']
        
        return strategies

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║          PERFORMANCE MONITORING DASHBOARD                 ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    monitor = PerformanceMonitor()
    
    # Generate reports
    print("\n📊 Generating performance report...")
    report_path = monitor.generate_performance_report()
    
    print("\n📈 Creating interactive dashboard...")
    dashboard_path = monitor.create_interactive_dashboard()
    
    # Show best strategies
    print("\n🎯 Best Performing Strategies:")
    strategies = monitor.get_best_performing_strategies()
    
    if not strategies.empty:
        print("\n{:<30} {:<15} {:<10} {:<10} {:<10}".format(
            "Market", "Confidence", "Bets", "Win Rate", "ROI"
        ))
        print("-" * 75)
        
        for _, row in strategies.head(10).iterrows():
            print("{:<30} {:<15} {:<10} {:<10.1%} {:<10.1f}%".format(
                row['market'][:30],
                row['confidence'] or 'N/A',
                row['bets'],
                row['win_rate'],
                row['roi']
            ))
    
    # Calculate current metrics
    print("\n📊 Current Performance (Last 30 Days):")
    metrics = monitor.calculate_performance_metrics(30)
    
    print(f"  • Total Bets: {metrics['total_bets']}")
    print(f"  • Win Rate: {metrics['win_rate']:.1%}")
    print(f"  • ROI: {metrics['roi']:.1f}%")
    print(f"  • Total Profit: €{metrics['total_profit']:.2f}")
    
    print("\n✅ Performance monitoring complete!")
    print(f"📄 Report: {report_path}")
    print(f"📊 Dashboard: {dashboard_path}")

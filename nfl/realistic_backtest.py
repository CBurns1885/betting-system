#!/usr/bin/env python3
"""
Realistic NFL Backtest

Includes realistic betting constraints:
- Line movement (odds change over time)
- Betting limits (max bet sizes)
- Vig/juice (standard -110 pricing)
- Kelly criterion bet sizing
- Bankroll management
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from config import OUTPUT_DIR, log_header
from backtest import NFLBacktestEngine


class RealisticNFLBacktest(NFLBacktestEngine):
    """Backtest with realistic betting constraints"""

    def __init__(self,
                 start_season: int,
                 end_season: int,
                 initial_bankroll: float = 1000.0,
                 max_bet_pct: float = 0.05,
                 kelly_fraction: float = 0.25,
                 vig_odds: int = -110,
                 **kwargs):
        """
        Initialize realistic backtest

        Args:
            start_season: First season to test
            end_season: Last season to test
            initial_bankroll: Starting bankroll in units
            max_bet_pct: Maximum bet as % of bankroll (default 5%)
            kelly_fraction: Fraction of Kelly to bet (default 25% = quarter Kelly)
            vig_odds: Standard odds with vig (default -110)
            **kwargs: Additional args for parent class
        """
        super().__init__(start_season, end_season, **kwargs)

        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.max_bet_pct = max_bet_pct
        self.kelly_fraction = kelly_fraction
        self.vig_odds = vig_odds

        self.bankroll_history = []
        self.bet_log = []

    def calculate_kelly_bet_size(self, probability: float, odds: int) -> float:
        """
        Calculate Kelly criterion bet size

        Args:
            probability: Win probability (0-1)
            odds: American odds

        Returns:
            Bet size as fraction of bankroll
        """
        # Convert American odds to decimal
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1

        # Kelly formula: f = (bp - q) / b
        # Where: b = decimal odds - 1, p = win prob, q = 1 - p
        b = decimal_odds - 1
        p = probability
        q = 1 - p

        kelly = (b * p - q) / b

        # Apply fractional Kelly
        kelly_fractional = kelly * self.kelly_fraction

        # Ensure non-negative and cap at max bet pct
        return max(0, min(kelly_fractional, self.max_bet_pct))

    def calculate_payout(self, stake: float, odds: int, won: bool) -> float:
        """
        Calculate payout for a bet

        Args:
            stake: Amount wagered
            odds: American odds
            won: Whether bet won

        Returns:
            Net profit/loss
        """
        if not won:
            return -stake

        # Convert odds to payout multiplier
        if odds > 0:
            payout = stake * (odds / 100)
        else:
            payout = stake * (100 / abs(odds))

        return payout

    def evaluate_predictions_realistic(self, predictions: pd.DataFrame) -> Dict:
        """
        Evaluate predictions with realistic betting constraints

        Args:
            predictions: DataFrame with predictions and actuals

        Returns:
            Dict with performance metrics including bankroll changes
        """
        if predictions.empty:
            return {}

        results = {
            'total_games': len(predictions),
            'total_bets': 0,
            'total_wagered': 0.0,
            'total_profit': 0.0,
            'markets': {}
        }

        period_bankroll_start = self.current_bankroll
        period_bets = []

        # Process each game
        for _, game in predictions.iterrows():
            # Moneyline betting
            if 'ml_pick' in game and 'actual_home_score' in game:
                if pd.notna(game['actual_home_score']) and pd.notna(game['actual_away_score']):
                    # Determine actual result
                    actual = 'HOME' if game['actual_home_score'] > game['actual_away_score'] else 'AWAY'

                    # Get predicted probability
                    if game['ml_pick'] == 'HOME':
                        prob = game.get('ml_home_prob', 0.5)
                    else:
                        prob = game.get('ml_away_prob', 0.5)

                    # Calculate bet size using Kelly
                    kelly_fraction = self.calculate_kelly_bet_size(prob, self.vig_odds)
                    bet_size = self.current_bankroll * kelly_fraction

                    # Minimum bet threshold
                    if bet_size >= 1.0:  # Don't bet if less than 1 unit
                        # Determine if won
                        won = (game['ml_pick'] == actual)

                        # Calculate payout
                        profit = self.calculate_payout(bet_size, self.vig_odds, won)

                        # Update bankroll
                        self.current_bankroll += profit

                        # Log bet
                        bet_log_entry = {
                            'season': game.get('season'),
                            'week': game.get('week'),
                            'home_team': game.get('home_team'),
                            'away_team': game.get('away_team'),
                            'market': 'MONEYLINE',
                            'pick': game['ml_pick'],
                            'probability': prob,
                            'bet_size': bet_size,
                            'odds': self.vig_odds,
                            'won': won,
                            'profit': profit,
                            'bankroll_after': self.current_bankroll
                        }

                        period_bets.append(bet_log_entry)
                        self.bet_log.append(bet_log_entry)

                        results['total_bets'] += 1
                        results['total_wagered'] += bet_size
                        results['total_profit'] += profit

        # Market-specific results
        if period_bets:
            ml_bets = [b for b in period_bets if b['market'] == 'MONEYLINE']
            if ml_bets:
                ml_won = sum(1 for b in ml_bets if b['won'])
                ml_total = len(ml_bets)
                ml_profit = sum(b['profit'] for b in ml_bets)

                results['markets']['MONEYLINE'] = {
                    'total': ml_total,
                    'correct': ml_won,
                    'accuracy': ml_won / ml_total if ml_total > 0 else 0,
                    'total_wagered': sum(b['bet_size'] for b in ml_bets),
                    'profit': ml_profit,
                    'roi': (ml_profit / sum(b['bet_size'] for b in ml_bets) * 100) if ml_total > 0 else 0
                }

        # Bankroll tracking
        period_profit = self.current_bankroll - period_bankroll_start
        self.bankroll_history.append({
            'period_start_bankroll': period_bankroll_start,
            'period_end_bankroll': self.current_bankroll,
            'period_profit': period_profit,
            'period_roi': (period_profit / period_bankroll_start * 100) if period_bankroll_start > 0 else 0
        })

        results['bankroll_change'] = period_profit

        return results

    def run_backtest(self) -> pd.DataFrame:
        """
        Run realistic backtest with bankroll management

        Returns:
            Summary DataFrame
        """
        log_header(f"Realistic NFL Backtest: {self.start_season}-{self.end_season}")

        print(f"💰 Initial Bankroll: ${self.initial_bankroll:.2f}")
        print(f"📊 Kelly Fraction: {self.kelly_fraction:.0%}")
        print(f"🎯 Max Bet: {self.max_bet_pct:.0%} of bankroll")
        print(f"📉 Vig: {self.vig_odds}")

        # Load data
        full_df = self.load_historical_data()

        # Filter to backtest seasons
        full_df = full_df[
            (full_df['season'] >= self.start_season) &
            (full_df['season'] <= self.end_season)
        ]

        # Get test periods
        test_periods = self.get_test_periods()
        print(f"\n📅 Testing {len(test_periods)} periods\n")

        all_results = []

        for season, week_start, week_end, period_id in test_periods:
            print(f"\n{'='*60}")
            print(f"Period {period_id}: Season {season}, Week {week_start}-{week_end}")
            print(f"💰 Current Bankroll: ${self.current_bankroll:.2f}")
            print('='*60)

            # Check if bankrupt
            if self.current_bankroll <= 0:
                print("💥 BANKRUPT - Stopping backtest")
                break

            # Split data
            train_df, test_df = self.split_data(full_df, season, week_start, week_end)

            if len(train_df) < self.min_training_games:
                print(f"   ⚠️ Skipping: insufficient training data")
                continue

            if len(test_df) == 0:
                print(f"   ⚠️ Skipping: no test games")
                continue

            print(f"   📊 Training: {len(train_df)} games | Testing: {len(test_df)} games")

            # Train models
            if not self.train_models_on_period(train_df):
                print(f"   ⚠️ Training failed, skipping")
                continue

            # Generate predictions
            predictions = self.generate_predictions(test_df, train_df)

            if predictions.empty:
                print(f"   ⚠️ No predictions generated")
                continue

            # Evaluate with realistic constraints
            period_results = self.evaluate_predictions_realistic(predictions)
            period_results['season'] = season
            period_results['week_start'] = week_start
            period_results['week_end'] = week_end

            all_results.append(period_results)

            # Print summary
            print(f"   📊 Bets: {period_results.get('total_bets', 0)}")
            print(f"   💰 Wagered: ${period_results.get('total_wagered', 0):.2f}")
            print(f"   📈 Profit: ${period_results.get('total_profit', 0):+.2f}")

            for market, stats in period_results.get('markets', {}).items():
                acc = stats.get('accuracy', 0)
                roi = stats.get('roi', 0)
                print(f"   • {market}: {acc:.1%} accuracy, {roi:+.1f}% ROI")

        self.results = all_results
        return self.generate_realistic_summary()

    def generate_realistic_summary(self) -> pd.DataFrame:
        """Generate summary with bankroll performance"""
        log_header("Realistic Backtest Summary")

        # Standard market summary
        summary_df = super().generate_summary()

        # Bankroll summary
        print("\n" + "="*60)
        print("💰 BANKROLL PERFORMANCE")
        print("="*60)

        final_bankroll = self.current_bankroll
        total_profit = final_bankroll - self.initial_bankroll
        total_roi = (total_profit / self.initial_bankroll * 100)

        print(f"\nInitial Bankroll: ${self.initial_bankroll:.2f}")
        print(f"Final Bankroll:   ${final_bankroll:.2f}")
        print(f"Total Profit:     ${total_profit:+.2f}")
        print(f"Total ROI:        {total_roi:+.1f}%")

        if self.bet_log:
            total_bets = len(self.bet_log)
            total_won = sum(1 for bet in self.bet_log if bet['won'])
            win_rate = total_won / total_bets if total_bets > 0 else 0

            print(f"\nTotal Bets:       {total_bets}")
            print(f"Bets Won:         {total_won}")
            print(f"Win Rate:         {win_rate:.1%}")

            # Max drawdown
            bankroll_values = [self.initial_bankroll] + [bet['bankroll_after'] for bet in self.bet_log]
            peak = self.initial_bankroll
            max_dd = 0

            for value in bankroll_values:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak
                if dd > max_dd:
                    max_dd = dd

            print(f"Max Drawdown:     {max_dd:.1%}")

        # Save bankroll history
        if self.bankroll_history:
            bankroll_df = pd.DataFrame(self.bankroll_history)
            bankroll_path = OUTPUT_DIR / "backtest_bankroll_history.csv"
            bankroll_df.to_csv(bankroll_path, index=False)
            print(f"\n✅ Saved bankroll history to {bankroll_path}")

        # Save bet log
        if self.bet_log:
            bets_df = pd.DataFrame(self.bet_log)
            bets_path = OUTPUT_DIR / "backtest_bet_log.csv"
            bets_df.to_csv(bets_path, index=False)
            print(f"✅ Saved bet log to {bets_path}")

        print("="*60)

        return summary_df


def main():
    """Main realistic backtest runner"""
    import argparse

    parser = argparse.ArgumentParser(description='Realistic NFL backtest with bankroll management')
    parser.add_argument('--start', type=int, default=2022,
                       help='Start season (default: 2022)')
    parser.add_argument('--end', type=int, default=2024,
                       help='End season (default: 2024)')
    parser.add_argument('--bankroll', type=float, default=1000.0,
                       help='Initial bankroll (default: 1000)')
    parser.add_argument('--kelly', type=float, default=0.25,
                       help='Kelly fraction (default: 0.25 = quarter Kelly)')
    parser.add_argument('--max-bet', type=float, default=0.05,
                       help='Max bet as fraction (default: 0.05 = 5%%)')

    args = parser.parse_args()

    engine = RealisticNFLBacktest(
        start_season=args.start,
        end_season=args.end,
        initial_bankroll=args.bankroll,
        kelly_fraction=args.kelly,
        max_bet_pct=args.max_bet
    )

    try:
        engine.run_backtest()
        engine.export_detailed_results()
    finally:
        engine.cleanup()

    print("\n✅ Realistic backtest complete!")
    print("   Check outputs/ for detailed results and bet log")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Tennis Betting Backtest

Backtests tennis betting strategies using historical data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

from config import (
    FEATURES_PARQUET, OUTPUT_DIR, RANDOM_SEED,
    log_header
)
from features import TennisFeatureEngineer
from models import TennisModelTrainer
from progress_utils import Timer

class TennisBacktester:
    """Backtests tennis betting strategies"""

    def __init__(self, initial_bankroll: float = 1000.0,
                kelly_fraction: float = 0.25,
                min_edge: float = 0.05,
                min_confidence: float = 0.60):
        self.initial_bankroll = initial_bankroll
        self.kelly_fraction = kelly_fraction
        self.min_edge = min_edge
        self.min_confidence = min_confidence

        self.feature_engineer = TennisFeatureEngineer()
        self.model_trainer = TennisModelTrainer()

    def walk_forward_backtest(self, df: pd.DataFrame,
                             train_size: int = 500,
                             test_size: int = 100) -> Dict:
        """
        Walk-forward backtesting

        Args:
            df: Historical matches with features
            train_size: Number of matches to train on
            test_size: Number of matches to test on

        Returns:
            Dictionary with backtest results
        """
        log_header("Tennis Walk-Forward Backtest")

        bankroll = self.initial_bankroll
        total_bets = 0
        winning_bets = 0
        total_profit = 0.0

        bet_history = []
        bankroll_history = [bankroll]

        # Ensure sorted by date
        if 'date' in df.columns:
            df = df.sort_values('date').reset_index(drop=True)

        print(f"Initial bankroll: ${bankroll:.2f}")
        print(f"Train size: {train_size}, Test size: {test_size}")
        print(f"Min edge: {self.min_edge:.1%}, Min confidence: {self.min_confidence:.1%}")

        # Walk forward through data
        for start_idx in range(0, len(df) - train_size - test_size, test_size):
            train_end = start_idx + train_size
            test_end = train_end + test_size

            if test_end > len(df):
                break

            train_df = df.iloc[start_idx:train_end]
            test_df = df.iloc[train_end:test_end]

            print(f"\n📅 Window {start_idx // test_size + 1}: Train [{start_idx}:{train_end}], Test [{train_end}:{test_end}]")

            # Prepare training data
            X_train, y_train, feature_cols = self.model_trainer.prepare_data(train_df)

            # Train models
            try:
                with Timer("Training models"):
                    self.model_trainer.train_model(X_train, y_train, market="MATCH_WINNER")
            except Exception as e:
                print(f"  ⚠️  Training failed: {e}")
                continue

            # Make predictions on test set
            X_test, y_test, _ = self.model_trainer.prepare_data(test_df)
            probas = self.model_trainer.predict(X_test, market="MATCH_WINNER")

            # Simulate betting
            for idx, (proba, actual) in enumerate(zip(probas, y_test)):
                player1_prob = proba[1]
                player2_prob = proba[0]

                # Determine if we have edge (assuming fair odds from probabilities)
                # In real backtest, we'd use actual historical odds
                # For simplicity, assume odds = 1/probability with 5% vig
                vig = 0.05
                implied_odds_p1 = (1 / player1_prob) * (1 + vig)
                implied_odds_p2 = (1 / player2_prob) * (1 + vig)

                # Calculate edge
                edge_p1 = player1_prob - (1 / implied_odds_p1)
                edge_p2 = player2_prob - (1 / implied_odds_p2)

                # Bet if we have sufficient edge and confidence
                bet_placed = False
                bet_on_player1 = False
                stake = 0.0

                if edge_p1 > self.min_edge and player1_prob > self.min_confidence:
                    # Kelly criterion bet sizing
                    kelly_stake = (player1_prob * (implied_odds_p1 - 1) - (1 - player1_prob)) / (implied_odds_p1 - 1)
                    kelly_stake = max(0, min(kelly_stake, 0.25))  # Cap at 25% of bankroll
                    stake = bankroll * kelly_stake * self.kelly_fraction
                    bet_on_player1 = True
                    bet_placed = True

                elif edge_p2 > self.min_edge and player2_prob > self.min_confidence:
                    kelly_stake = (player2_prob * (implied_odds_p2 - 1) - (1 - player2_prob)) / (implied_odds_p2 - 1)
                    kelly_stake = max(0, min(kelly_stake, 0.25))
                    stake = bankroll * kelly_stake * self.kelly_fraction
                    bet_on_player1 = False
                    bet_placed = True

                if bet_placed and stake > 0:
                    total_bets += 1

                    # Determine outcome
                    if bet_on_player1:
                        won = (actual == 1)
                        payout = stake * implied_odds_p1 if won else 0
                    else:
                        won = (actual == 0)
                        payout = stake * implied_odds_p2 if won else 0

                    profit = payout - stake
                    bankroll += profit
                    total_profit += profit

                    if won:
                        winning_bets += 1

                    bet_history.append({
                        'match_idx': train_end + idx,
                        'bet_on_player1': bet_on_player1,
                        'stake': stake,
                        'odds': implied_odds_p1 if bet_on_player1 else implied_odds_p2,
                        'won': won,
                        'profit': profit,
                        'bankroll': bankroll,
                    })

                    bankroll_history.append(bankroll)

            print(f"  Bets placed: {len([b for b in bet_history if b['match_idx'] >= train_end and b['match_idx'] < test_end])}")
            print(f"  Current bankroll: ${bankroll:.2f}")

        # Calculate final statistics
        win_rate = winning_bets / total_bets if total_bets > 0 else 0
        roi = (bankroll - self.initial_bankroll) / self.initial_bankroll if self.initial_bankroll > 0 else 0

        results = {
            'initial_bankroll': self.initial_bankroll,
            'final_bankroll': bankroll,
            'total_profit': total_profit,
            'total_bets': total_bets,
            'winning_bets': winning_bets,
            'losing_bets': total_bets - winning_bets,
            'win_rate': win_rate,
            'roi': roi,
            'bet_history': pd.DataFrame(bet_history) if bet_history else pd.DataFrame(),
            'bankroll_history': bankroll_history,
        }

        return results

    def print_results(self, results: Dict):
        """Print backtest results"""
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Initial Bankroll:  ${results['initial_bankroll']:,.2f}")
        print(f"Final Bankroll:    ${results['final_bankroll']:,.2f}")
        print(f"Total Profit:      ${results['total_profit']:,.2f}")
        print(f"ROI:               {results['roi']:.2%}")
        print(f"\nTotal Bets:        {results['total_bets']:,}")
        print(f"Winning Bets:      {results['winning_bets']:,}")
        print(f"Losing Bets:       {results['losing_bets']:,}")
        print(f"Win Rate:          {results['win_rate']:.2%}")
        print("="*60)

        # Save detailed results
        if not results['bet_history'].empty:
            output_file = OUTPUT_DIR / "tennis_backtest_results.csv"
            results['bet_history'].to_csv(output_file, index=False)
            print(f"\n✅ Detailed results saved to: {output_file}")


def main():
    """Run backtest"""
    import argparse

    parser = argparse.ArgumentParser(description='Backtest tennis betting strategy')
    parser.add_argument('--bankroll', type=float, default=1000.0,
                       help='Initial bankroll')
    parser.add_argument('--train-size', type=int, default=500,
                       help='Training window size')
    parser.add_argument('--test-size', type=int, default=100,
                       help='Testing window size')

    args = parser.parse_args()

    # Load features
    if not FEATURES_PARQUET.exists():
        print("⚠️  Features file not found. Run features.py first.")
        return

    print(f"Loading features from {FEATURES_PARQUET}")
    df = pd.read_parquet(FEATURES_PARQUET)
    df = df.dropna(subset=['target'])
    print(f"Loaded {len(df):,} completed matches")

    # Run backtest
    backtester = TennisBacktester(initial_bankroll=args.bankroll)
    results = backtester.walk_forward_backtest(
        df,
        train_size=args.train_size,
        test_size=args.test_size
    )

    # Print results
    backtester.print_results(results)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Rugby Union Betting Backtest

Backtests rugby betting strategies using historical data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict

from config import FEATURES_PARQUET, OUTPUT_DIR, log_header
from features import RugbyFeatureEngineer
from models import RugbyModelTrainer
from progress_utils import Timer

class RugbyBacktester:
    """Backtests rugby betting strategies"""

    def __init__(self, initial_bankroll: float = 1000.0,
                kelly_fraction: float = 0.25,
                min_edge: float = 0.05):
        self.initial_bankroll = initial_bankroll
        self.kelly_fraction = kelly_fraction
        self.min_edge = min_edge

        self.feature_engineer = RugbyFeatureEngineer()
        self.model_trainer = RugbyModelTrainer()

    def walk_forward_backtest(self, df: pd.DataFrame,
                             train_size: int = 200,
                             test_size: int = 50) -> Dict:
        """Walk-forward backtesting"""
        log_header("Rugby Walk-Forward Backtest")

        bankroll = self.initial_bankroll
        total_bets = 0
        winning_bets = 0

        bet_history = []
        bankroll_history = [bankroll]

        if 'date' in df.columns:
            df = df.sort_values('date').reset_index(drop=True)

        print(f"Initial bankroll: ${bankroll:.2f}")
        print(f"Train size: {train_size}, Test size: {test_size}")

        for start_idx in range(0, len(df) - train_size - test_size, test_size):
            train_end = start_idx + train_size
            test_end = train_end + test_size

            if test_end > len(df):
                break

            train_df = df.iloc[start_idx:train_end]
            test_df = df.iloc[train_end:test_end]

            print(f"\n📅 Window {start_idx // test_size + 1}")

            X_train, y_train, _ = self.model_trainer.prepare_data(train_df, 'target_winner')

            try:
                with Timer("Training"):
                    self.model_trainer.train_model(X_train, y_train, market="MATCH_WINNER")
            except Exception as e:
                print(f"  ⚠️  Training failed: {e}")
                continue

            X_test, y_test, _ = self.model_trainer.prepare_data(test_df, 'target_winner')
            probas = self.model_trainer.predict(X_test, market="MATCH_WINNER")

            # Simulate betting
            for idx, (proba, actual) in enumerate(zip(probas, y_test)):
                # probas: [away_win, draw, home_win]
                away_prob = proba[0]
                draw_prob = proba[1]
                home_prob = proba[2]

                # Simplified: bet on home win if high probability
                vig = 0.05
                implied_odds_home = (1 / home_prob) * (1 + vig)

                edge_home = home_prob - (1 / implied_odds_home)

                if edge_home > self.min_edge and home_prob > 0.50:
                    kelly_stake = (home_prob * (implied_odds_home - 1) - (1 - home_prob)) / (implied_odds_home - 1)
                    kelly_stake = max(0, min(kelly_stake, 0.25))
                    stake = bankroll * kelly_stake * self.kelly_fraction

                    if stake > 0:
                        total_bets += 1

                        won = (actual == 2)  # Home win
                        payout = stake * implied_odds_home if won else 0
                        profit = payout - stake
                        bankroll += profit

                        if won:
                            winning_bets += 1

                        bet_history.append({
                            'match_idx': train_end + idx,
                            'bet_type': 'home_win',
                            'stake': stake,
                            'odds': implied_odds_home,
                            'won': won,
                            'profit': profit,
                            'bankroll': bankroll,
                        })

                        bankroll_history.append(bankroll)

            print(f"  Current bankroll: ${bankroll:.2f}")

        win_rate = winning_bets / total_bets if total_bets > 0 else 0
        roi = (bankroll - self.initial_bankroll) / self.initial_bankroll

        results = {
            'initial_bankroll': self.initial_bankroll,
            'final_bankroll': bankroll,
            'total_profit': bankroll - self.initial_bankroll,
            'total_bets': total_bets,
            'winning_bets': winning_bets,
            'losing_bets': total_bets - winning_bets,
            'win_rate': win_rate,
            'roi': roi,
            'bet_history': pd.DataFrame(bet_history),
            'bankroll_history': bankroll_history,
        }

        return results

    def print_results(self, results: Dict):
        """Print backtest results"""
        print("\n" + "="*60)
        print("RUGBY BACKTEST RESULTS")
        print("="*60)
        print(f"Initial Bankroll:  ${results['initial_bankroll']:,.2f}")
        print(f"Final Bankroll:    ${results['final_bankroll']:,.2f}")
        print(f"Total Profit:      ${results['total_profit']:,.2f}")
        print(f"ROI:               {results['roi']:.2%}")
        print(f"\nTotal Bets:        {results['total_bets']:,}")
        print(f"Winning Bets:      {results['winning_bets']:,}")
        print(f"Win Rate:          {results['win_rate']:.2%}")
        print("="*60)

        if not results['bet_history'].empty:
            output_file = OUTPUT_DIR / "rugby_backtest_results.csv"
            results['bet_history'].to_csv(output_file, index=False)
            print(f"\n✅ Results saved to: {output_file}")


def main():
    """Run backtest"""
    if not FEATURES_PARQUET.exists():
        print("⚠️  Features file not found. Run features.py first.")
        return

    df = pd.read_parquet(FEATURES_PARQUET)
    df = df.dropna(subset=['target_winner'])
    print(f"Loaded {len(df):,} completed matches")

    backtester = RugbyBacktester(initial_bankroll=1000.0)
    results = backtester.walk_forward_backtest(df, train_size=200, test_size=50)

    backtester.print_results(results)


if __name__ == "__main__":
    main()

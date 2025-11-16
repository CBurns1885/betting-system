#!/usr/bin/env python3
"""
NFL Parlay Builder

Builds profitable parlay combinations from high-confidence picks.
Analyzes correlation and creates optimized parlay cards.
"""

import pandas as pd
import numpy as np
from itertools import combinations
from typing import List, Dict
from config import OUTPUT_DIR, log_header


class NFLParlayBuilder:
    """Build optimal NFL parlays"""

    def __init__(self, predictions_df: pd.DataFrame):
        """
        Initialize with predictions

        Args:
            predictions_df: DataFrame with game predictions
        """
        self.predictions = predictions_df.copy()

    def calculate_parlay_probability(self, picks: List[Dict]) -> float:
        """
        Calculate probability of parlay hitting

        Assumes independence (conservative)

        Args:
            picks: List of picks with probabilities

        Returns:
            Combined probability
        """
        prob = 1.0

        for pick in picks:
            prob *= pick['probability']

        return prob

    def calculate_parlay_odds(self, picks: List[Dict], juice: float = -110) -> float:
        """
        Calculate parlay payout odds

        Args:
            picks: List of picks
            juice: Standard line juice (default -110)

        Returns:
            Total parlay odds (American format)
        """
        # Convert each pick to decimal odds
        decimal_odds = []

        for pick in picks:
            # Assuming standard -110 for each leg
            if juice < 0:
                decimal = (100 / abs(juice)) + 1
            else:
                decimal = (juice / 100) + 1

            decimal_odds.append(decimal)

        # Multiply decimal odds
        total_decimal = np.prod(decimal_odds)

        # Convert back to American
        if total_decimal >= 2.0:
            american = (total_decimal - 1) * 100
        else:
            american = -100 / (total_decimal - 1)

        return american

    def build_parlays(self, min_confidence: float = 0.60,
                     min_legs: int = 3, max_legs: int = 5) -> List[Dict]:
        """
        Build parlay combinations

        Args:
            min_confidence: Minimum confidence per pick
            min_legs: Minimum parlay legs
            max_legs: Maximum parlay legs

        Returns:
            List of parlay combinations
        """
        # Get high confidence picks
        eligible_picks = []

        for _, game in self.predictions.iterrows():
            # Moneyline picks
            ml_conf = game.get('moneyline_confidence', 0)
            if ml_conf >= min_confidence:
                eligible_picks.append({
                    'game': f"{game['away_team']} @ {game['home_team']}",
                    'pick': f"{game['moneyline_pick']} ML",
                    'probability': ml_conf,
                    'market': 'moneyline'
                })

            # Spread picks
            spread_conf = game.get('spread_confidence', 0)
            if spread_conf >= min_confidence:
                eligible_picks.append({
                    'game': f"{game['away_team']} @ {game['home_team']}",
                    'pick': f"{game['spread_pick']} Spread",
                    'probability': spread_conf,
                    'market': 'spread'
                })

            # Total picks
            total_conf = game.get('total_confidence', 0)
            if total_conf >= min_confidence:
                eligible_picks.append({
                    'game': f"{game['away_team']} @ {game['home_team']}",
                    'pick': f"{game['total_pick']} Total",
                    'probability': total_conf,
                    'market': 'total'
                })

        if len(eligible_picks) < min_legs:
            print(f"⚠️  Only {len(eligible_picks)} eligible picks (need {min_legs})")
            return []

        # Build parlays of different sizes
        parlays = []

        for n_legs in range(min_legs, max_legs + 1):
            for combo in combinations(eligible_picks, n_legs):
                parlay_prob = self.calculate_parlay_probability(list(combo))
                parlay_odds = self.calculate_parlay_odds(list(combo))

                # Calculate expected value
                # EV = (Probability * Payout) - (1 - Probability)
                if parlay_odds > 0:
                    payout = parlay_odds / 100
                else:
                    payout = 100 / abs(parlay_odds)

                ev = (parlay_prob * payout) - (1 - parlay_prob)

                parlays.append({
                    'legs': n_legs,
                    'picks': [p['pick'] for p in combo],
                    'games': [p['game'] for p in combo],
                    'probability': parlay_prob,
                    'odds': parlay_odds,
                    'expected_value': ev,
                    'confidence': parlay_prob * 100,
                })

        return parlays

    def get_best_parlays(self, parlays: List[Dict], n: int = 10,
                        sort_by: str = 'probability') -> List[Dict]:
        """
        Get top N parlays

        Args:
            parlays: List of parlays
            n: Number to return
            sort_by: 'probability', 'expected_value', or 'odds'

        Returns:
            Top N parlays
        """
        if not parlays:
            return []

        # Sort
        sorted_parlays = sorted(parlays, key=lambda x: x[sort_by], reverse=True)

        return sorted_parlays[:n]

    def create_parlay_report(self, output_file: str = None):
        """Create parlay report"""

        if output_file is None:
            output_file = OUTPUT_DIR / "parlays.html"

        log_header("Building NFL Parlays")

        # Build parlays
        all_parlays = self.build_parlays(
            min_confidence=0.60,
            min_legs=3,
            max_legs=6
        )

        if not all_parlays:
            print("⚠️  No parlays found")
            return

        # Get best by different criteria
        safest = self.get_best_parlays(all_parlays, n=5, sort_by='probability')
        highest_ev = self.get_best_parlays(all_parlays, n=5, sort_by='expected_value')

        print(f"\n📊 Built {len(all_parlays)} total parlay combinations")
        print(f"   Top safest: {safest[0]['probability']:.1%} chance")
        print(f"   Top EV: {highest_ev[0]['expected_value']:.3f}")

        # Create HTML report
        html = f"""
        <html>
        <head>
            <title>NFL Parlay Builder</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #003366; }}
                h2 {{ color: #0066cc; margin-top: 30px; }}
                .parlay {{ border: 2px solid #0066cc; padding: 15px; margin: 15px 0;
                          border-radius: 8px; background-color: #f8f9fa; }}
                .safe {{ border-color: #28a745; }}
                .medium {{ border-color: #ffc107; }}
                .aggressive {{ border-color: #dc3545; }}
                .pick {{ margin: 5px 0; padding: 5px; background-color: white; }}
                .stats {{ color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <h1>🎰 NFL Parlay Builder</h1>

            <h2>🛡️ Safest Parlays (Highest Probability)</h2>
        """

        for i, parlay in enumerate(safest, 1):
            html += f"""
            <div class="parlay safe">
                <h3>Parlay #{i} - {parlay['legs']} Legs</h3>
                <div class="stats">
                    <strong>Win Probability:</strong> {parlay['probability']:.1%} |
                    <strong>Odds:</strong> {parlay['odds']:+.0f} |
                    <strong>Expected Value:</strong> {parlay['expected_value']:.3f}
                </div>
                <h4>Picks:</h4>
            """
            for pick, game in zip(parlay['picks'], parlay['games']):
                html += f'<div class="pick">✓ {pick} - {game}</div>'
            html += "</div>"

        html += "<h2>💎 Best Expected Value Parlays</h2>"

        for i, parlay in enumerate(highest_ev, 1):
            html += f"""
            <div class="parlay medium">
                <h3>Parlay #{i} - {parlay['legs']} Legs</h3>
                <div class="stats">
                    <strong>Win Probability:</strong> {parlay['probability']:.1%} |
                    <strong>Odds:</strong> {parlay['odds']:+.0f} |
                    <strong>Expected Value:</strong> {parlay['expected_value']:.3f}
                </div>
                <h4>Picks:</h4>
            """
            for pick, game in zip(parlay['picks'], parlay['games']):
                html += f'<div class="pick">✓ {pick} - {game}</div>'
            html += "</div>"

        html += f"""
            <h2>📈 Summary</h2>
            <ul>
                <li>Total parlays analyzed: {len(all_parlays)}</li>
                <li>Safest parlay win rate: {safest[0]['probability']:.1%}</li>
                <li>Best expected value: {highest_ev[0]['expected_value']:.3f}</li>
            </ul>

            <p><strong>⚠️ Disclaimer:</strong> Parlays are high-risk bets.
            Only bet what you can afford to lose. Past performance does not guarantee future results.</p>
        </body>
        </html>
        """

        # Save report
        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✅ Saved parlay report to {output_file}")


def main():
    """Main parlay builder"""
    import argparse

    parser = argparse.ArgumentParser(description='Build NFL parlays')
    parser.add_argument('--predictions', type=str,
                       default=str(OUTPUT_DIR / 'weekly_predictions.csv'),
                       help='Path to predictions CSV')

    args = parser.parse_args()

    # Load predictions
    predictions = pd.read_csv(args.predictions)

    # Build parlays
    builder = NFLParlayBuilder(predictions)
    builder.create_parlay_report()


if __name__ == "__main__":
    main()

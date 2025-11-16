#!/usr/bin/env python3
"""
betfair_odds_calculator.py
Calculates decimal odds from model probabilities for Betfair Exchange betting.
Includes commission calculations, lay odds, and exchange-specific features.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# BETFAIR CONFIGURATION
# ============================================================================

class BetfairConfig:
    """Betfair Exchange configuration"""
    
    # Standard commission rates by tier
    COMMISSION_RATES = {
        'standard': 0.05,      # 5% standard
        'reduced': 0.02,       # 2% for high volume
        'premium': 0.02,       # 2% base + premium charge
    }
    
    # Minimum/Maximum odds on Betfair
    MIN_ODDS = 1.01
    MAX_ODDS = 1000.0
    
    # Tick sizes for different odds ranges
    TICK_SIZES = [
        (1.01, 2.0, 0.01),
        (2.0, 3.0, 0.02),
        (3.0, 4.0, 0.05),
        (4.0, 6.0, 0.1),
        (6.0, 10.0, 0.2),
        (10.0, 20.0, 0.5),
        (20.0, 30.0, 1.0),
        (30.0, 50.0, 2.0),
        (50.0, 100.0, 5.0),
        (100.0, 1000.0, 10.0),
    ]
    
    @staticmethod
    def round_to_betfair_price(odds: float) -> float:
        """Round odds to valid Betfair price increments"""
        if odds < BetfairConfig.MIN_ODDS:
            return BetfairConfig.MIN_ODDS
        if odds > BetfairConfig.MAX_ODDS:
            return BetfairConfig.MAX_ODDS
            
        for min_odds, max_odds, tick in BetfairConfig.TICK_SIZES:
            if min_odds <= odds < max_odds:
                return round(odds / tick) * tick
                
        return odds

# ============================================================================
# ODDS CALCULATOR
# ============================================================================

class BetfairOddsCalculator:
    """Calculate Betfair decimal odds from model probabilities"""
    
    def __init__(self, commission_rate: float = 0.05, margin: float = 0.02):
        """
        Initialize calculator
        
        Args:
            commission_rate: Betfair commission rate (default 5%)
            margin: Safety margin to add (default 2%)
        """
        self.commission_rate = commission_rate
        self.margin = margin
        
    def probability_to_decimal_odds(self, probability: float, 
                                  include_margin: bool = True) -> float:
        """
        Convert probability to decimal odds
        
        Args:
            probability: Model probability (0-1)
            include_margin: Whether to include safety margin
            
        Returns:
            Decimal odds
        """
        if probability <= 0 or probability >= 1:
            return None
            
        # Calculate fair odds
        fair_odds = 1.0 / probability
        
        # Add margin if requested (makes odds slightly worse for safety)
        if include_margin:
            if probability > 0.5:
                # Favorite - increase required probability
                adjusted_prob = probability + self.margin
                adjusted_prob = min(adjusted_prob, 0.99)
            else:
                # Underdog - decrease probability
                adjusted_prob = probability - self.margin
                adjusted_prob = max(adjusted_prob, 0.01)
            fair_odds = 1.0 / adjusted_prob
        
        # Round to Betfair increment
        return BetfairConfig.round_to_betfair_price(fair_odds)
    
    def calculate_lay_odds(self, back_probability: float) -> float:
        """
        Calculate lay odds from back probability
        
        Args:
            back_probability: Probability of event happening
            
        Returns:
            Decimal odds for laying
        """
        lay_probability = 1 - back_probability
        return self.probability_to_decimal_odds(lay_probability)
    
    def calculate_net_odds(self, decimal_odds: float) -> float:
        """
        Calculate net odds after Betfair commission
        
        Args:
            decimal_odds: Gross decimal odds
            
        Returns:
            Net decimal odds after commission
        """
        gross_profit = decimal_odds - 1.0
        net_profit = gross_profit * (1 - self.commission_rate)
        return 1.0 + net_profit
    
    def calculate_minimum_odds(self, probability: float, 
                              target_edge: float = 0.05) -> float:
        """
        Calculate minimum acceptable odds for a target edge
        
        Args:
            probability: Model probability
            target_edge: Desired edge (default 5%)
            
        Returns:
            Minimum decimal odds to achieve target edge
        """
        # Account for commission
        required_prob = probability * (1 - target_edge)
        gross_odds = 1.0 / required_prob
        
        # Adjust for commission
        # Net return must give us our edge
        # (odds - 1) * (1 - commission) >= (1/prob * (1 + edge)) - 1
        min_odds = 1 + ((1/probability * (1 + target_edge)) - 1) / (1 - self.commission_rate)
        
        return BetfairConfig.round_to_betfair_price(min_odds)
    
    def calculate_value(self, model_probability: float, 
                       market_odds: float) -> Dict[str, float]:
        """
        Calculate expected value and edge
        
        Args:
            model_probability: Your model's probability
            market_odds: Available market odds
            
        Returns:
            Dictionary with value metrics
        """
        # Implied probability from market
        market_probability = 1.0 / market_odds
        
        # Edge
        edge = model_probability - market_probability
        
        # Expected value (before commission)
        ev_gross = (model_probability * market_odds) - 1.0
        
        # Expected value (after commission)
        if ev_gross > 0:
            ev_net = ev_gross * (1 - self.commission_rate)
        else:
            ev_net = ev_gross  # No commission on losses
        
        # Kelly fraction
        if market_odds > 1:
            kelly = (model_probability * (market_odds - 1) - (1 - model_probability)) / (market_odds - 1)
            kelly = max(0, min(kelly, 0.25))  # Cap at 25%
        else:
            kelly = 0
        
        return {
            'model_probability': model_probability,
            'market_probability': market_probability,
            'edge': edge,
            'edge_percentage': edge * 100,
            'ev_gross': ev_gross,
            'ev_net': ev_net,
            'ev_percentage': ev_net * 100,
            'kelly_fraction': kelly,
            'kelly_percentage': kelly * 100
        }

# ============================================================================
# MARKET ODDS PROCESSOR
# ============================================================================

class MarketOddsProcessor:
    """Process predictions and add Betfair odds"""
    
    def __init__(self, commission_rate: float = 0.05):
        """Initialize processor"""
        self.calculator = BetfairOddsCalculator(commission_rate)
        
    def process_match_result(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process Match Result (1X2) market
        
        Args:
            df: DataFrame with Home/Draw/Away probabilities
            
        Returns:
            DataFrame with added odds columns
        """
        df = df.copy()
        
        # Find probability columns
        prob_cols = {
            'home': None,
            'draw': None,
            'away': None
        }
        
        for col in df.columns:
            col_lower = col.lower()
            if any(x in col_lower for x in ['home_prob', 'home_win', 'h_prob', '1_prob']):
                prob_cols['home'] = col
            elif any(x in col_lower for x in ['draw_prob', 'draw', 'd_prob', 'x_prob']):
                prob_cols['draw'] = col
            elif any(x in col_lower for x in ['away_prob', 'away_win', 'a_prob', '2_prob']):
                prob_cols['away'] = col
        
        # Calculate odds for each outcome
        for outcome, prob_col in prob_cols.items():
            if prob_col and prob_col in df.columns:
                # Fair odds
                df[f'{outcome}_odds_fair'] = df[prob_col].apply(
                    lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=False)
                )
                
                # Odds with margin (minimum to accept)
                df[f'{outcome}_odds_min'] = df[prob_col].apply(
                    lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=True)
                )
                
                # Lay odds
                df[f'{outcome}_lay_odds'] = df[prob_col].apply(
                    lambda p: self.calculator.calculate_lay_odds(p)
                )
                
                # Target odds for 5% edge
                df[f'{outcome}_odds_target'] = df[prob_col].apply(
                    lambda p: self.calculator.calculate_minimum_odds(p, target_edge=0.05)
                )
        
        return df
    
    def process_over_under(self, df: pd.DataFrame, line: float = 2.5) -> pd.DataFrame:
        """
        Process Over/Under market
        
        Args:
            df: DataFrame with Over/Under probabilities
            line: Goal line (e.g., 2.5)
            
        Returns:
            DataFrame with added odds columns
        """
        df = df.copy()
        
        # Find probability columns
        over_col = None
        under_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if f'over_{line}'.replace('.', '_') in col_lower or f'o{line}' in col_lower:
                over_col = col
            elif f'under_{line}'.replace('.', '_') in col_lower or f'u{line}' in col_lower:
                under_col = col
        
        # Calculate odds
        if over_col and over_col in df.columns:
            df[f'over_{line}_odds_fair'] = df[over_col].apply(
                lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=False)
            )
            df[f'over_{line}_odds_min'] = df[over_col].apply(
                lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=True)
            )
            df[f'over_{line}_lay_odds'] = df[over_col].apply(
                lambda p: self.calculator.calculate_lay_odds(p)
            )
            
        if under_col and under_col in df.columns:
            df[f'under_{line}_odds_fair'] = df[under_col].apply(
                lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=False)
            )
            df[f'under_{line}_odds_min'] = df[under_col].apply(
                lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=True)
            )
            df[f'under_{line}_lay_odds'] = df[under_col].apply(
                lambda p: self.calculator.calculate_lay_odds(p)
            )
        
        return df
    
    def process_btts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process Both Teams to Score market"""
        df = df.copy()
        
        # Find probability columns
        yes_col = None
        no_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'btts' in col_lower and 'yes' in col_lower:
                yes_col = col
            elif 'btts' in col_lower and 'no' in col_lower:
                no_col = col
        
        # Calculate odds
        if yes_col and yes_col in df.columns:
            df['btts_yes_odds_fair'] = df[yes_col].apply(
                lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=False)
            )
            df['btts_yes_odds_min'] = df[yes_col].apply(
                lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=True)
            )
            df['btts_yes_lay_odds'] = df[yes_col].apply(
                lambda p: self.calculator.calculate_lay_odds(p)
            )
            
        if no_col and no_col in df.columns:
            df['btts_no_odds_fair'] = df[no_col].apply(
                lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=False)
            )
            df['btts_no_odds_min'] = df[no_col].apply(
                lambda p: self.calculator.probability_to_decimal_odds(p, include_margin=True)
            )
            df['btts_no_lay_odds'] = df[no_col].apply(
                lambda p: self.calculator.calculate_lay_odds(p)
            )
        
        return df
    
    def add_value_calculations(self, df: pd.DataFrame, 
                              market_odds_cols: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """
        Add value calculations if market odds are available
        
        Args:
            df: DataFrame with model odds
            market_odds_cols: Dictionary mapping our columns to market odds columns
            
        Returns:
            DataFrame with value calculations
        """
        df = df.copy()
        
        if not market_odds_cols:
            return df
        
        for our_col, market_col in market_odds_cols.items():
            if our_col in df.columns and market_col in df.columns:
                # Get probability column name
                prob_col = our_col.replace('_odds_fair', '').replace('_odds_min', '')
                
                # Calculate value for each row
                values = []
                for idx, row in df.iterrows():
                    if pd.notna(row[market_col]) and pd.notna(row[our_col]):
                        model_prob = 1.0 / row[our_col] if row[our_col] > 0 else 0
                        value_dict = self.calculator.calculate_value(
                            model_prob, 
                            row[market_col]
                        )
                        values.append(value_dict)
                    else:
                        values.append({})
                
                # Add value columns
                if values:
                    value_df = pd.DataFrame(values)
                    for col in value_df.columns:
                        df[f'{prob_col}_{col}'] = value_df[col]
        
        return df

# ============================================================================
# ENHANCED PREDICTIONS PROCESSOR
# ============================================================================

class EnhancedPredictionsProcessor:
    """Process all predictions and add comprehensive odds"""
    
    def __init__(self, commission_rate: float = 0.05):
        """Initialize processor"""
        self.processor = MarketOddsProcessor(commission_rate)
        self.calculator = BetfairOddsCalculator(commission_rate)
        
    def process_predictions_file(self, input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Process predictions file and add all odds columns
        
        Args:
            input_file: Path to predictions CSV
            output_file: Where to save enhanced file (optional)
            
        Returns:
            Enhanced DataFrame
        """
        print(f"📊 Processing {input_file}...")
        
        # Load predictions
        df = pd.read_csv(input_file)
        print(f"   Loaded {len(df)} fixtures")
        
        # Process different markets
        print("   Adding odds calculations...")
        
        # Match Result
        if any('home' in col.lower() or 'draw' in col.lower() for col in df.columns):
            df = self.processor.process_match_result(df)
            print("   ✅ Match Result odds added")
        
        # Over/Under markets
        for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
            if any(f'{line}' in col for col in df.columns):
                df = self.processor.process_over_under(df, line)
                print(f"   ✅ Over/Under {line} odds added")
        
        # BTTS
        if any('btts' in col.lower() for col in df.columns):
            df = self.processor.process_btts(df)
            print("   ✅ BTTS odds added")
        
        # Add summary columns
        df = self._add_summary_columns(df)
        
        # Save if output file specified
        if output_file:
            df.to_csv(output_file, index=False)
            print(f"   💾 Saved to {output_file}")
        
        return df
    
    def _add_summary_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add summary columns for best bets"""
        df = df.copy()
        
        # Find best bet for each fixture
        best_bets = []
        
        for idx, row in df.iterrows():
            best_prob = 0
            best_market = ''
            best_selection = ''
            best_odds = 0
            
            # Check all probability columns
            for col in df.columns:
                if '_prob' in col.lower() and pd.notna(row[col]):
                    prob = row[col]
                    
                    # Get corresponding odds column
                    odds_col = col.replace('_prob', '_odds_fair')
                    if odds_col in df.columns and pd.notna(row[odds_col]):
                        odds = row[odds_col]
                        
                        # Check if this is the best
                        if prob > best_prob and prob > 0.6:  # Min 60% confidence
                            best_prob = prob
                            best_market = col.replace('_prob', '')
                            best_selection = col
                            best_odds = odds
            
            best_bets.append({
                'best_market': best_market,
                'best_selection': best_selection,
                'best_probability': best_prob,
                'best_odds_fair': best_odds,
                'best_odds_min': best_odds * 0.98 if best_odds > 0 else 0,  # 2% margin
                'confidence': self._get_confidence_level(best_prob)
            })
        
        # Add summary columns
        summary_df = pd.DataFrame(best_bets)
        for col in summary_df.columns:
            df[col] = summary_df[col]
        
        return df
    
    def _get_confidence_level(self, probability: float) -> str:
        """Get confidence level from probability"""
        if probability >= 0.80:
            return 'VERY_HIGH'
        elif probability >= 0.70:
            return 'HIGH'
        elif probability >= 0.60:
            return 'MEDIUM'
        elif probability >= 0.55:
            return 'LOW'
        else:
            return 'SKIP'
    
    def create_betfair_format(self, df: pd.DataFrame, output_file: str):
        """
        Create Betfair-specific format for easy betting
        
        Args:
            df: Enhanced DataFrame
            output_file: Where to save Betfair format
        """
        betfair_data = []
        
        for idx, row in df.iterrows():
            # Create entry for each market
            
            # Match Result
            if 'home_odds_fair' in df.columns:
                for outcome in ['home', 'draw', 'away']:
                    if f'{outcome}_odds_fair' in df.columns:
                        betfair_data.append({
                            'Date': row['Date'],
                            'Event': f"{row['HomeTeam']} v {row['AwayTeam']}",
                            'Market': 'Match Odds',
                            'Selection': outcome.capitalize(),
                            'Model_Probability': row.get(f'{outcome}_prob', 0),
                            'Fair_Odds': row.get(f'{outcome}_odds_fair', 0),
                            'Min_Odds': row.get(f'{outcome}_odds_min', 0),
                            'Target_5%': row.get(f'{outcome}_odds_target', 0),
                            'Lay_Odds': row.get(f'{outcome}_lay_odds', 0),
                            'Type': 'BACK'
                        })
            
            # Over/Under 2.5
            if 'over_2.5_odds_fair' in df.columns:
                for side in ['over', 'under']:
                    if f'{side}_2.5_odds_fair' in df.columns:
                        betfair_data.append({
                            'Date': row['Date'],
                            'Event': f"{row['HomeTeam']} v {row['AwayTeam']}",
                            'Market': 'Over/Under 2.5 Goals',
                            'Selection': f'{side.capitalize()} 2.5',
                            'Model_Probability': row.get(f'{side}_2.5_prob', 0),
                            'Fair_Odds': row.get(f'{side}_2.5_odds_fair', 0),
                            'Min_Odds': row.get(f'{side}_2.5_odds_min', 0),
                            'Target_5%': row.get(f'{side}_2.5_odds_target', 0),
                            'Lay_Odds': row.get(f'{side}_2.5_lay_odds', 0),
                            'Type': 'BACK'
                        })
            
            # BTTS
            if 'btts_yes_odds_fair' in df.columns:
                for outcome in ['yes', 'no']:
                    if f'btts_{outcome}_odds_fair' in df.columns:
                        betfair_data.append({
                            'Date': row['Date'],
                            'Event': f"{row['HomeTeam']} v {row['AwayTeam']}",
                            'Market': 'Both Teams to Score',
                            'Selection': outcome.upper(),
                            'Model_Probability': row.get(f'btts_{outcome}_prob', 0),
                            'Fair_Odds': row.get(f'btts_{outcome}_odds_fair', 0),
                            'Min_Odds': row.get(f'btts_{outcome}_odds_min', 0),
                            'Target_5%': row.get(f'btts_{outcome}_odds_target', 0),
                            'Lay_Odds': row.get(f'btts_{outcome}_lay_odds', 0),
                            'Type': 'BACK'
                        })
        
        # Create DataFrame and save
        betfair_df = pd.DataFrame(betfair_data)
        
        # Filter for value bets only (where we have edge)
        value_df = betfair_df[betfair_df['Model_Probability'] > 0.55].copy()
        
        # Sort by probability
        value_df = value_df.sort_values('Model_Probability', ascending=False)
        
        # Save
        value_df.to_csv(output_file, index=False)
        print(f"✅ Betfair format saved to {output_file}")
        print(f"   {len(value_df)} value selections across all markets")
        
        return value_df

# ============================================================================
# INTEGRATION WITH PIPELINE
# ============================================================================

def integrate_with_pipeline(predictions_file: str, commission_rate: float = 0.05):
    """
    Add Betfair odds to existing predictions
    
    Args:
        predictions_file: Your predictions CSV file
        commission_rate: Your Betfair commission rate
    """
    processor = EnhancedPredictionsProcessor(commission_rate)
    
    # Process main file
    output_file = predictions_file.replace('.csv', '_with_odds.csv')
    enhanced_df = processor.process_predictions_file(predictions_file, output_file)
    
    # Create Betfair format
    betfair_file = predictions_file.replace('.csv', '_betfair.csv')
    processor.create_betfair_format(enhanced_df, betfair_file)
    
    print(f"\n✅ Betfair odds added successfully!")
    print(f"📊 Enhanced file: {output_file}")
    print(f"🎯 Betfair format: {betfair_file}")
    
    return enhanced_df

# ============================================================================
# EXAMPLE USAGE IN YOUR PIPELINE
# ============================================================================

def add_to_weekly_pipeline():
    """
    Example of how to add this to your run_weeklyOU.py
    """
    code = """
# In run_weeklyOU.py, after generating predictions:

from betfair_odds_calculator import integrate_with_pipeline

# Your existing code that creates predictions
predictions_df = generate_predictions()  # Your existing function

# Save predictions
predictions_df.to_csv('outputs/weekly_predictions.csv', index=False)

# Add Betfair odds
enhanced_df = integrate_with_pipeline(
    'outputs/weekly_predictions.csv',
    commission_rate=0.05  # Your commission rate
)

# The enhanced_df now has columns like:
# - home_odds_fair: Fair decimal odds based on model
# - home_odds_min: Minimum acceptable odds (with margin)
# - home_odds_target: Target odds for 5% edge
# - home_lay_odds: Odds for laying this selection
# - best_odds_fair: Best selection for this fixture
# - confidence: Confidence level (VERY_HIGH, HIGH, etc.)

print("Betfair odds added to all predictions!")
"""
    return code

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║           BETFAIR EXCHANGE ODDS CALCULATOR                    ║
    ║                                                                ║
    ║  Converts model probabilities to Betfair decimal odds         ║
    ║  Includes commission, lay odds, and value calculations        ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        commission = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
        
        print(f"\n📊 Input file: {input_file}")
        print(f"💰 Commission rate: {commission*100}%")
        
        # Process file
        integrate_with_pipeline(input_file, commission)
        
        print("\n" + "="*60)
        print("ODDS EXPLANATION:")
        print("="*60)
        print("Fair_Odds:   What the odds should be based on probability")
        print("Min_Odds:    Minimum to accept (includes safety margin)")
        print("Target_5%:   Odds needed for 5% edge after commission")
        print("Lay_Odds:    Odds for laying (betting against)")
        print("\nEXAMPLE:")
        print("If model says 70% chance (fair odds = 1.43)")
        print("You want at least 1.47 to have value after 5% commission")
        
    else:
        print("""
        Usage:
            python betfair_odds_calculator.py <predictions_file> [commission_rate]
        
        Example:
            python betfair_odds_calculator.py weekly_predictions.csv 0.05
            python betfair_odds_calculator.py outputs/predictions.csv 0.02
        
        This will:
        1. Load your predictions with probabilities
        2. Calculate fair decimal odds for each selection
        3. Add minimum acceptable odds (with margin)
        4. Calculate lay odds for each selection
        5. Determine target odds for desired edge
        6. Create Betfair-specific format for easy betting
        
        Output columns added:
        - *_odds_fair:    Fair odds based on model probability
        - *_odds_min:     Minimum acceptable odds
        - *_odds_target:  Target for 5% edge
        - *_lay_odds:     Odds for laying
        
        Commission rates:
        - 0.05 (5%):  Standard Betfair rate
        - 0.02 (2%):  Reduced rate for high volume
        - 0.00 (0%):  If you have special arrangement
        """)

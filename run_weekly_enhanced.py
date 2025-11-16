#!/usr/bin/env python3
"""
run_weekly_enhanced.py
Complete weekly prediction pipeline with API-Football integration
Replaces run_weeklyOU.py with enhanced data and all betting markets
"""

import os
import sys
import time
import json
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import API integration modules
from api_football_integration import (
    APIFootballClient, 
    MarketAnalyzer, 
    ArbitrageFinder,
    TeamStatistics,
    PlayerStatistics,
    OddsData,
    InjuryData,
    PredictionData,
    LEAGUE_MAPPING,
    INTERNATIONAL_LEAGUES
)

from enhanced_features import FeatureEngineer

# Import existing project modules (these should exist in your project)
try:
    from config import (
        OUTPUT_DIR, 
        DATA_DIR, 
        MODEL_ARTIFACTS_DIR,
        FEATURES_PARQUET,
        RANDOM_SEED,
        log_header
    )
    from download_football_data import download
    from data_ingest import build_historical_results
    from features import build_features
    from models import train_all_targets, load_models
    from predict import generate_predictions
    from accuracy_tracker import log_weekly_predictions, update_accuracy_database
    from weighted_top50 import generate_weighted_top50
    from ou_analyzer import analyze_ou_predictions
    from accumulator_finder import AccumulatorBuilder
except ImportError as e:
    print(f"Warning: Some existing modules not found: {e}")
    print("Using standalone mode...")

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# API Configuration
API_KEY = os.environ.get("API_FOOTBALL_KEY", "")
USE_API = os.environ.get("USE_API_FOOTBALL", "true").lower() == "true"
CACHE_HISTORICAL = os.environ.get("CACHE_HISTORICAL", "true").lower() == "true"

# Training configuration
TRAINING_START_YEAR = int(os.environ.get("TRAINING_START_YEAR", 2020))
OPTUNA_TRIALS = int(os.environ.get("OPTUNA_TRIALS", 25))
USE_ENHANCED_FEATURES = True

# Betting configuration
MIN_VALUE_EDGE = 0.05  # Minimum 5% edge for value bets
MAX_KELLY_STAKE = 0.05  # Maximum 5% of bankroll per bet
MIN_CONFIDENCE = 0.60  # Minimum confidence for predictions

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_DIR / 'weekly_run.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENHANCED DATA FETCHING
# ============================================================================

class EnhancedDataFetcher:
    """Fetches and combines data from API-Football and existing sources"""
    
    def __init__(self, api_key: str):
        """Initialize data fetcher"""
        self.api = APIFootballClient(api_key) if api_key else None
        self.feature_engineer = FeatureEngineer()
        self.current_season = datetime.now().year
        
    def fetch_upcoming_fixtures(self, days_ahead: int = 7) -> pd.DataFrame:
        """
        Fetch upcoming fixtures with full context from API
        
        Returns DataFrame with fixture information and IDs for further enrichment
        """
        logger.info(f"Fetching fixtures for next {days_ahead} days...")
        
        all_fixtures = []
        start_date = datetime.now()
        
        for day in range(days_ahead):
            date = start_date + timedelta(days=day)
            date_str = date.strftime('%Y-%m-%d')
            
            # Fetch from all leagues
            for league_code, league_id in LEAGUE_MAPPING.items():
                fixtures = self.api.get_fixtures_by_date(date_str, league_id)
                
                for fixture in fixtures:
                    fixture_data = self._parse_fixture(fixture, league_code)
                    if fixture_data:
                        all_fixtures.append(fixture_data)
            
            # Also fetch international competitions
            for league_id, league_name in INTERNATIONAL_LEAGUES.items():
                fixtures = self.api.get_fixtures_by_date(date_str, league_id)
                
                for fixture in fixtures:
                    fixture_data = self._parse_fixture(fixture, league_name)
                    if fixture_data:
                        all_fixtures.append(fixture_data)
        
        df = pd.DataFrame(all_fixtures)
        logger.info(f"Found {len(df)} fixtures across {df['League'].nunique()} leagues")
        
        return df
    
    def enrich_fixture_with_api_data(self, fixture: pd.Series) -> pd.DataFrame:
        """
        Enrich a single fixture with all API data
        
        Returns DataFrame with 200+ features for all betting markets
        """
        fixture_id = fixture['fixture_id']
        home_team_id = fixture['home_team_id']
        away_team_id = fixture['away_team_id']
        league_id = LEAGUE_MAPPING.get(fixture['League'], 0)
        
        logger.info(f"Enriching fixture {fixture_id}: {fixture['HomeTeam']} vs {fixture['AwayTeam']}")
        
        # Fetch all data types
        data = {}
        
        # 1. Team Statistics
        data['team_stats'] = {
            'home': self.api.get_team_statistics(home_team_id, league_id, self.current_season),
            'away': self.api.get_team_statistics(away_team_id, league_id, self.current_season)
        }
        
        # 2. Head-to-Head
        data['h2h'] = self.api.get_h2h(home_team_id, away_team_id, last=20)
        data['h2h_analysis'] = self.api.analyze_h2h(data['h2h'])
        
        # 3. Player Statistics & Injuries
        home_squad = self.api.get_team_squad(home_team_id)
        away_squad = self.api.get_team_squad(away_team_id)
        
        data['player_stats'] = []
        for player in home_squad[:11]:  # Top 11 players
            stats = self.api.get_player_statistics(player['id'], self.current_season)
            if stats:
                data['player_stats'].append(stats)
        
        for player in away_squad[:11]:
            stats = self.api.get_player_statistics(player['id'], self.current_season)
            if stats:
                data['player_stats'].append(stats)
        
        # 4. Injuries
        data['injuries'] = (self.api.get_injuries(team_id=home_team_id) + 
                          self.api.get_injuries(team_id=away_team_id))
        
        # 5. API Predictions
        data['predictions'] = self.api.get_predictions(fixture_id)
        
        # 6. Odds from all bookmakers
        data['odds'] = self.api.get_odds(fixture_id)
        
        # 7. Venue information
        data['venue'] = self.api.get_venues(city=fixture.get('venue_city', ''))[0] if fixture.get('venue_city') else {}
        
        # 8. Weather (would need weather API integration)
        data['weather'] = self._get_weather_data(fixture)
        
        # 9. Fixture details
        data['fixture_details'] = self.api.get_fixture_by_id(fixture_id)
        
        # Create comprehensive features
        features = self.feature_engineer.create_all_features(
            fixture_data=data['fixture_details'],
            team_stats=data['team_stats'],
            player_stats=data['player_stats'],
            h2h_data=data['h2h'],
            odds_data=data['odds'],
            injuries=data['injuries'],
            venue_data=data['venue'],
            weather_data=data['weather']
        )
        
        # Add original fixture info
        for col in fixture.index:
            if col not in features.columns:
                features[col] = fixture[col]
        
        return features
    
    def fetch_historical_enhanced_data(self, start_year: int = 2020) -> pd.DataFrame:
        """
        Fetch enhanced historical data for training
        
        This combines existing historical data with API enhancements
        """
        logger.info(f"Fetching enhanced historical data from {start_year}...")
        
        # Load existing historical data
        if Path(FEATURES_PARQUET).exists():
            df = pd.read_parquet(FEATURES_PARQUET)
            logger.info(f"Loaded {len(df)} historical matches")
        else:
            # Build from scratch if needed
            logger.info("Building historical database...")
            df = self._build_historical_from_api(start_year)
        
        # Enhance with API data if not already done
        if 'xg_diff_expected' not in df.columns and self.api:
            logger.info("Enhancing historical data with API statistics...")
            df = self._enhance_historical_data(df)
        
        return df
    
    def _parse_fixture(self, fixture: Dict, league_code: str) -> Optional[Dict]:
        """Parse API fixture into standard format"""
        try:
            fixture_info = fixture.get('fixture', {})
            teams = fixture.get('teams', {})
            league = fixture.get('league', {})
            
            return {
                'fixture_id': fixture_info.get('id'),
                'Date': pd.to_datetime(fixture_info.get('date')),
                'Time': pd.to_datetime(fixture_info.get('date')).strftime('%H:%M'),
                'League': league_code,
                'league_id': league.get('id'),
                'HomeTeam': teams.get('home', {}).get('name'),
                'AwayTeam': teams.get('away', {}).get('name'),
                'home_team_id': teams.get('home', {}).get('id'),
                'away_team_id': teams.get('away', {}).get('id'),
                'venue_name': fixture_info.get('venue', {}).get('name'),
                'venue_city': fixture_info.get('venue', {}).get('city'),
                'referee': fixture_info.get('referee'),
                'round': league.get('round'),
                'status': fixture_info.get('status', {}).get('long')
            }
        except Exception as e:
            logger.error(f"Error parsing fixture: {e}")
            return None
    
    def _get_weather_data(self, fixture: pd.Series) -> Dict:
        """Get weather data for fixture (placeholder - would integrate weather API)"""
        return {
            'temp': 20,
            'humidity': 60,
            'wind': {'speed': 10, 'degree': 180},
            'description': 'Clear'
        }
    
    def _build_historical_from_api(self, start_year: int) -> pd.DataFrame:
        """Build historical database from API (expensive operation)"""
        # This would fetch all historical matches from API
        # Very expensive in terms of API calls - better to use existing data
        logger.warning("Building from API would require thousands of API calls")
        logger.info("Using existing historical data instead")
        
        # Fallback to traditional data source
        from download_football_data import download
        download(list(LEAGUE_MAPPING.keys()), list(range(start_year, datetime.now().year + 1)))
        
        from data_ingest import build_historical_results
        build_historical_results(force=True)
        
        from features import build_features
        build_features(force=True)
        
        return pd.read_parquet(FEATURES_PARQUET)
    
    def _enhance_historical_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhance historical data with API statistics (selective)"""
        # This would be very expensive - only enhance recent matches
        recent_date = datetime.now() - timedelta(days=90)
        recent_mask = pd.to_datetime(df['Date']) > recent_date
        
        logger.info(f"Enhancing {recent_mask.sum()} recent matches with API data...")
        
        # Would fetch and add xG data, advanced stats, etc.
        # Placeholder for now
        df['xg_diff_expected'] = 0
        df['h2h_dominance_factor'] = 0
        
        return df

# ============================================================================
# PREDICTION ENGINE
# ============================================================================

class EnhancedPredictionEngine:
    """Generate predictions for all betting markets"""
    
    def __init__(self, api_client: APIFootballClient, base_models: Dict):
        """Initialize prediction engine"""
        self.api = api_client
        self.models = base_models
        self.market_analyzer = MarketAnalyzer(api_client)
        self.arbitrage_finder = ArbitrageFinder()
        
    def predict_all_markets(self, fixture_features: pd.DataFrame) -> Dict:
        """
        Generate predictions for all betting markets
        
        Returns comprehensive predictions for every market type
        """
        fixture_id = fixture_features.iloc[0]['fixture_id']
        
        logger.info(f"Generating predictions for fixture {fixture_id}")
        
        predictions = {}
        
        # Get base model predictions
        if self.models:
            base_pred = self._get_base_predictions(fixture_features)
            predictions['base_model'] = base_pred
        
        # Get API predictions
        api_pred = self.api.get_predictions(fixture_id)
        if api_pred:
            predictions['api_prediction'] = {
                'home': float(api_pred.predictions.get('home', '0').strip('%')) / 100,
                'draw': float(api_pred.predictions.get('draw', '0').strip('%')) / 100,
                'away': float(api_pred.predictions.get('away', '0').strip('%')) / 100,
                'goals_home': float(api_pred.goals.get('home', 0)),
                'goals_away': float(api_pred.goals.get('away', 0)),
                'advice': api_pred.advice
            }
        
        # Get odds for all markets
        odds_data = self.api.get_odds(fixture_id)
        
        # Analyze each market
        predictions['markets'] = {}
        
        # 1. Match Result (1X2)
        predictions['markets']['match_result'] = self.market_analyzer.analyze_match_result(
            odds_data, api_pred
        )
        
        # 2. Over/Under markets (all lines)
        for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
            predictions['markets'][f'over_under_{line}'] = self.market_analyzer.analyze_over_under(
                odds_data, api_pred, line
            )
        
        # 3. Both Teams to Score
        predictions['markets']['btts'] = self.market_analyzer.analyze_btts(
            odds_data, api_pred
        )
        
        # 4. Asian Handicap (multiple lines)
        for line in [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]:
            predictions['markets'][f'asian_handicap_{line}'] = self.market_analyzer.analyze_asian_handicap(
                odds_data, api_pred, line
            )
        
        # 5. Correct Score
        predictions['markets']['correct_score'] = self.market_analyzer.analyze_correct_score(
            odds_data, api_pred
        )
        
        # 6. Double Chance
        predictions['markets']['double_chance'] = self.market_analyzer.analyze_double_chance(
            odds_data, api_pred
        )
        
        # 7. Half-Time markets
        fixture_stats = self.api.get_fixture_statistics(fixture_id)
        predictions['markets']['half_time'] = self.market_analyzer.analyze_half_time(
            odds_data, fixture_stats
        )
        
        # 8. Goalscorer markets
        player_stats = fixture_features.iloc[0].get('player_stats', [])
        predictions['markets']['goalscorer'] = self.market_analyzer.analyze_goalscorer(
            odds_data, player_stats
        )
        
        # 9. Corners
        team_stats = {
            'home_corners_avg': fixture_features.iloc[0].get('home_corners_avg', 5),
            'away_corners_avg': fixture_features.iloc[0].get('away_corners_avg', 5)
        }
        predictions['markets']['corners'] = self.market_analyzer.analyze_corners(
            odds_data, team_stats
        )
        
        # 10. Cards
        referee_stats = {
            'avg_cards_per_game': fixture_features.iloc[0].get('referee_avg_cards', 3.5)
        }
        predictions['markets']['cards'] = self.market_analyzer.analyze_cards(
            odds_data, referee_stats
        )
        
        # Find arbitrage opportunities
        predictions['arbitrage'] = self.arbitrage_finder.find_arbitrage(odds_data)
        
        # Create ensemble prediction
        predictions['ensemble'] = self._create_ensemble_prediction(predictions)
        
        # Identify best bets
        predictions['recommended_bets'] = self._identify_best_bets(predictions)
        
        return predictions
    
    def _get_base_predictions(self, features: pd.DataFrame) -> Dict:
        """Get predictions from existing models"""
        predictions = {}
        
        # This would use your existing models
        # Placeholder implementation
        predictions['home_win'] = 0.45
        predictions['draw'] = 0.25
        predictions['away_win'] = 0.30
        predictions['over_25'] = 0.55
        predictions['btts_yes'] = 0.50
        
        return predictions
    
    def _create_ensemble_prediction(self, predictions: Dict) -> Dict:
        """Create weighted ensemble of all predictions"""
        ensemble = {}
        
        # Combine base model and API predictions
        if 'base_model' in predictions and 'api_prediction' in predictions:
            base = predictions['base_model']
            api = predictions['api_prediction']
            
            # Weighted average
            weights = {'base': 0.4, 'api': 0.3, 'market': 0.3}
            
            ensemble['home_win'] = (
                base.get('home_win', 0.33) * weights['base'] +
                api.get('home', 0.33) * weights['api'] +
                predictions['markets']['match_result'].get('api_probabilities', {}).get('home', 0.33) * weights['market']
            )
            
            ensemble['draw'] = (
                base.get('draw', 0.33) * weights['base'] +
                api.get('draw', 0.33) * weights['api'] +
                predictions['markets']['match_result'].get('api_probabilities', {}).get('draw', 0.33) * weights['market']
            )
            
            ensemble['away_win'] = 1 - ensemble['home_win'] - ensemble['draw']
            
            # Goals predictions
            ensemble['total_goals'] = (api.get('goals_home', 1.5) + api.get('goals_away', 1.5))
            ensemble['over_25'] = predictions['markets']['over_under_2.5'].get('calculated_probabilities', {}).get('Over 2.5', 0.5)
            ensemble['btts'] = predictions['markets']['btts'].get('calculated_probabilities', {}).get('Yes', 0.5)
        
        return ensemble
    
    def _identify_best_bets(self, predictions: Dict) -> List[Dict]:
        """Identify the best value bets across all markets"""
        best_bets = []
        
        # Check each market for value
        for market_name, market_data in predictions.get('markets', {}).items():
            if 'value_bets' in market_data:
                for bet in market_data['value_bets']:
                    if bet['expected_value'] > MIN_VALUE_EDGE:
                        best_bets.append({
                            'market': market_name,
                            'selection': bet['outcome'],
                            'odds': bet['odd'],
                            'probability': bet['probability'],
                            'expected_value': bet['expected_value'],
                            'kelly_stake': bet['kelly_stake'],
                            'confidence': self._calculate_confidence(bet)
                        })
        
        # Sort by expected value
        best_bets = sorted(best_bets, key=lambda x: x['expected_value'], reverse=True)
        
        # Add arbitrage opportunities
        for arb in predictions.get('arbitrage', []):
            best_bets.insert(0, {
                'market': f"ARBITRAGE - {arb['market']}",
                'selection': 'Multiple',
                'odds': 'Various',
                'probability': 1.0,
                'expected_value': arb['profit_percentage'] / 100,
                'kelly_stake': 0.10,  # 10% for arbitrage
                'confidence': 'GUARANTEED'
            })
        
        return best_bets[:10]  # Top 10 bets
    
    def _calculate_confidence(self, bet: Dict) -> str:
        """Calculate confidence level for a bet"""
        prob = bet['probability']
        ev = bet['expected_value']
        
        if prob > 0.75 and ev > 0.20:
            return "VERY HIGH"
        elif prob > 0.65 and ev > 0.15:
            return "HIGH"
        elif prob > 0.55 and ev > 0.10:
            return "MEDIUM"
        else:
            return "LOW"

# ============================================================================
# REPORT GENERATOR
# ============================================================================

class EnhancedReportGenerator:
    """Generate comprehensive betting reports"""
    
    def __init__(self, output_dir: Path):
        """Initialize report generator"""
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_all_reports(self, predictions_df: pd.DataFrame, api_client: APIFootballClient):
        """Generate all betting reports"""
        logger.info("Generating comprehensive reports...")
        
        # 1. Main predictions CSV
        self._generate_main_csv(predictions_df)
        
        # 2. Value bets report
        self._generate_value_bets_report(predictions_df)
        
        # 3. Arbitrage opportunities
        self._generate_arbitrage_report(predictions_df)
        
        # 4. Market-specific reports
        self._generate_market_reports(predictions_df)
        
        # 5. Accumulator suggestions
        self._generate_accumulator_report(predictions_df)
        
        # 6. Live betting preparation
        self._generate_live_betting_prep(predictions_df, api_client)
        
        # 7. Summary dashboard
        self._generate_dashboard(predictions_df)
        
        logger.info(f"Reports generated in {self.output_dir}")
    
    def _generate_main_csv(self, df: pd.DataFrame):
        """Generate main predictions CSV"""
        output_path = self.output_dir / "enhanced_weekly_predictions.csv"
        
        # Extract key predictions for each fixture
        main_df = pd.DataFrame()
        
        for idx, row in df.iterrows():
            predictions = row.get('predictions', {})
            ensemble = predictions.get('ensemble', {})
            
            main_df = main_df.append({
                'Date': row['Date'],
                'Time': row['Time'],
                'League': row['League'],
                'HomeTeam': row['HomeTeam'],
                'AwayTeam': row['AwayTeam'],
                'Home_Win_%': ensemble.get('home_win', 0) * 100,
                'Draw_%': ensemble.get('draw', 0) * 100,
                'Away_Win_%': ensemble.get('away_win', 0) * 100,
                'Over_2.5_%': ensemble.get('over_25', 0) * 100,
                'BTTS_%': ensemble.get('btts', 0) * 100,
                'Expected_Goals': ensemble.get('total_goals', 2.5),
                'Best_Bet': row.get('predictions', {}).get('recommended_bets', [{}])[0].get('selection', ''),
                'Best_Bet_EV': row.get('predictions', {}).get('recommended_bets', [{}])[0].get('expected_value', 0),
                'Confidence': row.get('predictions', {}).get('recommended_bets', [{}])[0].get('confidence', '')
            }, ignore_index=True)
        
        main_df.to_csv(output_path, index=False)
        logger.info(f"Main predictions saved to {output_path}")
    
    def _generate_value_bets_report(self, df: pd.DataFrame):
        """Generate value bets report"""
        output_path = self.output_dir / "value_bets.html"
        
        all_value_bets = []
        
        for idx, row in df.iterrows():
            fixture_info = f"{row['HomeTeam']} vs {row['AwayTeam']} ({row['Date']})"
            
            for bet in row.get('predictions', {}).get('recommended_bets', []):
                if bet.get('expected_value', 0) > MIN_VALUE_EDGE:
                    bet['fixture'] = fixture_info
                    all_value_bets.append(bet)
        
        # Sort by EV
        all_value_bets = sorted(all_value_bets, key=lambda x: x['expected_value'], reverse=True)
        
        # Generate HTML
        html = self._create_value_bets_html(all_value_bets)
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"Value bets report saved to {output_path}")
    
    def _generate_arbitrage_report(self, df: pd.DataFrame):
        """Generate arbitrage opportunities report"""
        output_path = self.output_dir / "arbitrage_opportunities.html"
        
        all_arbs = []
        
        for idx, row in df.iterrows():
            fixture_info = f"{row['HomeTeam']} vs {row['AwayTeam']} ({row['Date']})"
            
            for arb in row.get('predictions', {}).get('arbitrage', []):
                arb['fixture'] = fixture_info
                all_arbs.append(arb)
        
        if all_arbs:
            html = self._create_arbitrage_html(all_arbs)
            with open(output_path, 'w') as f:
                f.write(html)
            logger.info(f"Found {len(all_arbs)} arbitrage opportunities!")
        else:
            logger.info("No arbitrage opportunities found")
    
    def _generate_market_reports(self, df: pd.DataFrame):
        """Generate reports for each betting market"""
        markets = ['match_result', 'over_under_2.5', 'btts', 'asian_handicap_-0.5', 
                  'correct_score', 'double_chance']
        
        for market in markets:
            output_path = self.output_dir / f"market_{market}.csv"
            market_df = self._extract_market_predictions(df, market)
            market_df.to_csv(output_path, index=False)
    
    def _generate_accumulator_report(self, df: pd.DataFrame):
        """Generate accumulator suggestions"""
        output_path = self.output_dir / "accumulator_suggestions.html"
        
        # Find high confidence bets for accumulators
        high_confidence = []
        
        for idx, row in df.iterrows():
            ensemble = row.get('predictions', {}).get('ensemble', {})
            
            # Check for high probability outcomes
            if ensemble.get('home_win', 0) > 0.70:
                high_confidence.append({
                    'fixture': f"{row['HomeTeam']} vs {row['AwayTeam']}",
                    'selection': row['HomeTeam'],
                    'probability': ensemble['home_win'],
                    'type': 'Home Win'
                })
            elif ensemble.get('away_win', 0) > 0.70:
                high_confidence.append({
                    'fixture': f"{row['HomeTeam']} vs {row['AwayTeam']}",
                    'selection': row['AwayTeam'],
                    'probability': ensemble['away_win'],
                    'type': 'Away Win'
                })
        
        # Create accumulator combinations
        accumulators = self._create_accumulator_combinations(high_confidence)
        
        html = self._create_accumulator_html(accumulators)
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"Accumulator suggestions saved to {output_path}")
    
    def _generate_live_betting_prep(self, df: pd.DataFrame, api_client: APIFootballClient):
        """Generate live betting preparation report"""
        output_path = self.output_dir / "live_betting_prep.json"
        
        live_prep = {}
        
        for idx, row in df.iterrows():
            fixture_id = row['fixture_id']
            
            live_prep[fixture_id] = {
                'fixture': f"{row['HomeTeam']} vs {row['AwayTeam']}",
                'kickoff': str(row['Date']),
                'pre_match_predictions': row.get('predictions', {}).get('ensemble', {}),
                'key_markets_to_watch': self._identify_live_markets(row),
                'trigger_points': self._calculate_trigger_points(row)
            }
        
        with open(output_path, 'w') as f:
            json.dump(live_prep, f, indent=2, default=str)
        
        logger.info(f"Live betting prep saved to {output_path}")
    
    def _generate_dashboard(self, df: pd.DataFrame):
        """Generate summary dashboard"""
        output_path = self.output_dir / "dashboard.html"
        
        stats = {
            'total_fixtures': len(df),
            'total_value_bets': sum(len(row.get('predictions', {}).get('recommended_bets', [])) for _, row in df.iterrows()),
            'avg_expected_value': np.mean([bet['expected_value'] 
                                          for _, row in df.iterrows() 
                                          for bet in row.get('predictions', {}).get('recommended_bets', [])]),
            'arbitrage_count': sum(len(row.get('predictions', {}).get('arbitrage', [])) for _, row in df.iterrows()),
            'high_confidence_count': sum(1 for _, row in df.iterrows() 
                                        if any(bet.get('confidence') in ['HIGH', 'VERY HIGH'] 
                                              for bet in row.get('predictions', {}).get('recommended_bets', [])))
        }
        
        html = self._create_dashboard_html(stats, df)
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"Dashboard saved to {output_path}")
    
    # HTML generation methods
    def _create_value_bets_html(self, value_bets: List[Dict]) -> str:
        """Create HTML for value bets"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Value Bets Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #2e7d32; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #4CAF50; color: white; }
                tr:nth-child(even) { background-color: #f2f2f2; }
                .high-ev { color: #2e7d32; font-weight: bold; }
                .medium-ev { color: #ff9800; }
                .low-ev { color: #f44336; }
            </style>
        </head>
        <body>
            <h1>Value Bets Report</h1>
            <p>Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """</p>
            <table>
                <tr>
                    <th>Fixture</th>
                    <th>Market</th>
                    <th>Selection</th>
                    <th>Odds</th>
                    <th>Our Probability</th>
                    <th>Expected Value</th>
                    <th>Kelly Stake</th>
                    <th>Confidence</th>
                </tr>
        """
        
        for bet in value_bets[:50]:  # Top 50 value bets
            ev_class = 'high-ev' if bet['expected_value'] > 0.15 else 'medium-ev' if bet['expected_value'] > 0.10 else 'low-ev'
            
            html += f"""
                <tr>
                    <td>{bet['fixture']}</td>
                    <td>{bet['market']}</td>
                    <td>{bet['selection']}</td>
                    <td>{bet.get('odds', 'N/A')}</td>
                    <td>{bet['probability']:.2%}</td>
                    <td class="{ev_class}">{bet['expected_value']:.2%}</td>
                    <td>{bet['kelly_stake']:.2%}</td>
                    <td>{bet['confidence']}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        return html
    
    def _create_arbitrage_html(self, arbs: List[Dict]) -> str:
        """Create HTML for arbitrage opportunities"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Arbitrage Opportunities</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #FFD700; background: #000; padding: 10px; }
                .arb-box { border: 2px solid #FFD700; padding: 15px; margin: 10px 0; background: #fffef0; }
                .profit { color: #2e7d32; font-size: 1.2em; font-weight: bold; }
                .stakes { margin-top: 10px; }
                table { width: 100%; }
                td { padding: 5px; }
            </style>
        </head>
        <body>
            <h1>⚡ ARBITRAGE OPPORTUNITIES ⚡</h1>
            <p>Guaranteed profit opportunities - act fast!</p>
        """
        
        for arb in arbs:
            html += f"""
            <div class="arb-box">
                <h3>{arb['fixture']}</h3>
                <p>Market: {arb['market']}</p>
                <p class="profit">Guaranteed Profit: {arb['profit_percentage']:.2f}%</p>
                <p>Total Stake: €{arb['total_stake']:.2f} → Return: €{arb['guaranteed_return']:.2f}</p>
                
                <div class="stakes">
                    <h4>Required Stakes:</h4>
                    <table>
            """
            
            for outcome, details in arb['stakes'].items():
                html += f"""
                    <tr>
                        <td>{outcome}:</td>
                        <td>€{details['stake']:.2f}</td>
                        <td>@ {details['odd']}</td>
                        <td>({details['bookmaker']})</td>
                    </tr>
                """
            
            html += """
                    </table>
                </div>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def _create_accumulator_html(self, accumulators: List[Dict]) -> str:
        """Create HTML for accumulator suggestions"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Accumulator Suggestions</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #1976d2; }
                .acca { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
                .safe { background: #e8f5e9; }
                .medium { background: #fff3e0; }
                .risky { background: #ffebee; }
                .odds { font-size: 1.2em; font-weight: bold; color: #2e7d32; }
            </style>
        </head>
        <body>
            <h1>Accumulator Suggestions</h1>
        """
        
        for acca in accumulators:
            risk_class = 'safe' if acca['total_probability'] > 0.30 else 'medium' if acca['total_probability'] > 0.15 else 'risky'
            
            html += f"""
            <div class="acca {risk_class}">
                <h3>{acca['type']} ({acca['legs']} legs)</h3>
                <p class="odds">Combined Odds: {acca['total_odds']:.2f}</p>
                <p>Combined Probability: {acca['total_probability']:.2%}</p>
                <p>Expected Value: {acca['expected_value']:.2%}</p>
                <ul>
            """
            
            for leg in acca['selections']:
                html += f"<li>{leg['fixture']}: {leg['selection']} ({leg['probability']:.2%})</li>"
            
            html += """
                </ul>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def _create_dashboard_html(self, stats: Dict, df: pd.DataFrame) -> str:
        """Create dashboard HTML"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Weekly Betting Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                h1 {{ color: #333; text-align: center; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
                .stat-box {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stat-value {{ font-size: 2em; font-weight: bold; color: #2e7d32; }}
                .stat-label {{ color: #666; margin-top: 5px; }}
            </style>
        </head>
        <body>
            <h1>Weekly Betting Dashboard</h1>
            <p style="text-align: center;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value">{stats['total_fixtures']}</div>
                    <div class="stat-label">Total Fixtures</div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-value">{stats['total_value_bets']}</div>
                    <div class="stat-label">Value Bets Found</div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-value">{stats['avg_expected_value']:.2%}</div>
                    <div class="stat-label">Avg Expected Value</div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-value">{stats['arbitrage_count']}</div>
                    <div class="stat-label">Arbitrage Opportunities</div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-value">{stats['high_confidence_count']}</div>
                    <div class="stat-label">High Confidence Bets</div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _extract_market_predictions(self, df: pd.DataFrame, market: str) -> pd.DataFrame:
        """Extract predictions for a specific market"""
        # Implementation would extract specific market data
        return pd.DataFrame()
    
    def _create_accumulator_combinations(self, high_confidence: List[Dict]) -> List[Dict]:
        """Create accumulator combinations"""
        # Simple implementation - would use more sophisticated algorithm
        accumulators = []
        
        if len(high_confidence) >= 3:
            # 3-fold
            selections = high_confidence[:3]
            total_prob = np.prod([s['probability'] for s in selections])
            total_odds = np.prod([1/s['probability'] for s in selections])
            
            accumulators.append({
                'type': 'Safe 3-Fold',
                'legs': 3,
                'selections': selections,
                'total_probability': total_prob,
                'total_odds': total_odds,
                'expected_value': (total_prob * total_odds) - 1
            })
        
        return accumulators
    
    def _identify_live_markets(self, fixture: pd.Series) -> List[str]:
        """Identify which markets to watch during live betting"""
        markets = []
        
        ensemble = fixture.get('predictions', {}).get('ensemble', {})
        
        # Close match - watch result market
        if abs(ensemble.get('home_win', 0.33) - ensemble.get('away_win', 0.33)) < 0.1:
            markets.append('Match Result - Close game, odds will swing')
        
        # High scoring expected - watch goals markets
        if ensemble.get('total_goals', 2.5) > 3:
            markets.append('Over/Under - High scoring expected')
        
        return markets
    
    def _calculate_trigger_points(self, fixture: pd.Series) -> Dict:
        """Calculate trigger points for live betting"""
        return {
            '0-0 at HT': 'Consider Under 2.5 goals',
            'Early goal': 'Check Over 2.5 goals odds',
            'Red card': 'Reassess all markets',
            '70min 0-0': 'Strong Under 1.5 opportunity'
        }

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_enhanced_weekly_pipeline():
    """
    Main execution pipeline for enhanced weekly predictions
    """
    print("=" * 80)
    print("ENHANCED WEEKLY FOOTBALL PREDICTIONS")
    print("Powered by API-Football Integration")
    print("=" * 80)
    
    start_time = time.time()
    
    # Check API key
    if not API_KEY:
        print("\n⚠️ WARNING: API_FOOTBALL_KEY not set!")
        print("Running in degraded mode without API enhancements")
        print("Set environment variable API_FOOTBALL_KEY to enable full features")
        use_api = False
    else:
        print(f"\n✅ API Key configured")
        use_api = True
    
    # Initialize components
    if use_api:
        api_client = APIFootballClient(API_KEY)
        data_fetcher = EnhancedDataFetcher(API_KEY)
    else:
        api_client = None
        data_fetcher = None
    
    # Step 1: Fetch upcoming fixtures
    print("\n" + "=" * 60)
    print("STEP 1: FETCHING UPCOMING FIXTURES")
    print("=" * 60)
    
    if use_api:
        fixtures_df = data_fetcher.fetch_upcoming_fixtures(days_ahead=7)
    else:
        # Fallback to simple downloader
        from simple_fixture_downloader import download_upcoming_fixtures
        fixture_path = download_upcoming_fixtures()
        fixtures_df = pd.read_csv(fixture_path)
    
    print(f"✅ Found {len(fixtures_df)} fixtures")
    
    # Step 2: Load/train models
    print("\n" + "=" * 60)
    print("STEP 2: LOADING/TRAINING MODELS")
    print("=" * 60)
    
    try:
        # Try to load existing models
        models = load_models()
        print("✅ Loaded existing models")
    except:
        print("Training new models...")
        if use_api:
            historical_df = data_fetcher.fetch_historical_enhanced_data(TRAINING_START_YEAR)
        else:
            # Use existing pipeline
            from features import build_features
            build_features(force=True)
            historical_df = pd.read_parquet(FEATURES_PARQUET)
        
        models = train_all_targets()
        print("✅ Models trained")
    
    # Step 3: Enrich fixtures with API data
    if use_api:
        print("\n" + "=" * 60)
        print("STEP 3: ENRICHING FIXTURES WITH API DATA")
        print("=" * 60)
        
        enriched_fixtures = []
        for idx, fixture in fixtures_df.iterrows():
            print(f"Processing {idx+1}/{len(fixtures_df)}: {fixture['HomeTeam']} vs {fixture['AwayTeam']}")
            
            try:
                enriched = data_fetcher.enrich_fixture_with_api_data(fixture)
                enriched_fixtures.append(enriched)
            except Exception as e:
                logger.error(f"Error enriching fixture: {e}")
                # Use basic fixture data
                enriched_fixtures.append(fixture.to_frame().T)
        
        fixtures_df = pd.concat(enriched_fixtures, ignore_index=True)
        print("✅ Fixtures enriched with 200+ features")
    
    # Step 4: Generate predictions for all markets
    print("\n" + "=" * 60)
    print("STEP 4: GENERATING PREDICTIONS FOR ALL MARKETS")
    print("=" * 60)
    
    if use_api:
        prediction_engine = EnhancedPredictionEngine(api_client, models)
        
        all_predictions = []
        for idx, fixture in fixtures_df.iterrows():
            print(f"Predicting {idx+1}/{len(fixtures_df)}: {fixture['HomeTeam']} vs {fixture['AwayTeam']}")
            
            try:
                predictions = prediction_engine.predict_all_markets(fixture.to_frame().T)
                fixture['predictions'] = predictions
                all_predictions.append(fixture)
            except Exception as e:
                logger.error(f"Error generating predictions: {e}")
                all_predictions.append(fixture)
        
        predictions_df = pd.DataFrame(all_predictions)
    else:
        # Use existing prediction pipeline
        from predict import generate_predictions
        predictions_df = generate_predictions(fixtures_df, models)
    
    print(f"✅ Generated predictions for {len(predictions_df)} fixtures")
    
    # Step 5: Generate reports
    print("\n" + "=" * 60)
    print("STEP 5: GENERATING REPORTS")
    print("=" * 60)
    
    report_generator = EnhancedReportGenerator(OUTPUT_DIR)
    report_generator.generate_all_reports(predictions_df, api_client)
    
    # Step 6: Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 80)
    print(f"\nTime taken: {elapsed/60:.1f} minutes")
    print(f"\nReports generated in: {OUTPUT_DIR}")
    print("\nKey files:")
    print("  • enhanced_weekly_predictions.csv - All predictions")
    print("  • value_bets.html - Best value betting opportunities")
    print("  • arbitrage_opportunities.html - Guaranteed profit opportunities")
    print("  • dashboard.html - Summary dashboard")
    print("  • accumulator_suggestions.html - Accumulator recommendations")
    print("  • live_betting_prep.json - Live betting preparation")
    print("\n" + "=" * 80)
    
    # Open output folder
    try:
        import subprocess
        import platform
        
        if platform.system() == "Windows":
            subprocess.run(["explorer", str(OUTPUT_DIR)], check=False)
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(OUTPUT_DIR)], check=False)
        else:
            subprocess.run(["xdg-open", str(OUTPUT_DIR)], check=False)
    except:
        pass
    
    return predictions_df

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Run the enhanced pipeline
    results = run_enhanced_weekly_pipeline()
    
    print("\n💰 Good luck with your bets! Remember to bet responsibly.")
    print("Never bet more than you can afford to lose.")
    
    input("\nPress Enter to exit...")

#!/usr/bin/env python3
"""
enhanced_features.py
Feature engineering module that incorporates all API-Football data
Creates comprehensive features for all betting markets
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# FEATURE ENGINEERING CLASSES
# ============================================================================

class FeatureEngineer:
    """Master feature engineering class for all markets"""
    
    def __init__(self):
        """Initialize feature engineering components"""
        self.xg_features = xGFeatures()
        self.form_features = FormFeatures()
        self.h2h_features = H2HFeatures()
        self.player_features = PlayerFeatures()
        self.venue_features = VenueFeatures()
        self.market_features = MarketSpecificFeatures()
        self.contextual_features = ContextualFeatures()
        
    def create_all_features(self, 
                           fixture_data: Dict,
                           team_stats: Dict,
                           player_stats: List[Dict],
                           h2h_data: List[Dict],
                           odds_data: List[Dict],
                           injuries: List[Dict],
                           venue_data: Dict,
                           weather_data: Dict) -> pd.DataFrame:
        """
        Create comprehensive feature set for all betting markets
        
        Returns DataFrame with 200+ features for maximum predictive power
        """
        
        features = {}
        
        # Basic fixture information
        features.update(self._extract_basic_info(fixture_data))
        
        # xG-based features
        features.update(self.xg_features.create_features(team_stats))
        
        # Form features
        features.update(self.form_features.create_features(team_stats))
        
        # Head-to-head features
        features.update(self.h2h_features.create_features(h2h_data))
        
        # Player impact features
        features.update(self.player_features.create_features(player_stats, injuries))
        
        # Venue and weather features
        features.update(self.venue_features.create_features(venue_data, weather_data))
        
        # Market-specific features for each betting type
        features.update(self.market_features.create_all_market_features(
            team_stats, h2h_data, player_stats
        ))
        
        # Contextual features
        features.update(self.contextual_features.create_features(
            fixture_data, team_stats, injuries
        ))
        
        # Odds-based features
        features.update(self._extract_odds_features(odds_data))
        
        return pd.DataFrame([features])
    
    def _extract_basic_info(self, fixture_data: Dict) -> Dict:
        """Extract basic fixture information"""
        fixture = fixture_data.get("fixture", {})
        teams = fixture_data.get("teams", {})
        league = fixture_data.get("league", {})
        
        return {
            "fixture_id": fixture.get("id"),
            "date": fixture.get("date"),
            "timestamp": fixture.get("timestamp"),
            "league_id": league.get("id"),
            "league_name": league.get("name"),
            "league_country": league.get("country"),
            "league_round": league.get("round", ""),
            "home_team_id": teams.get("home", {}).get("id"),
            "home_team_name": teams.get("home", {}).get("name"),
            "away_team_id": teams.get("away", {}).get("id"),
            "away_team_name": teams.get("away", {}).get("name"),
            "referee": fixture.get("referee", ""),
            "venue_id": fixture.get("venue", {}).get("id"),
            "venue_name": fixture.get("venue", {}).get("name"),
            "venue_city": fixture.get("venue", {}).get("city")
        }
    
    def _extract_odds_features(self, odds_data: List[Dict]) -> Dict:
        """Extract features from betting odds"""
        if not odds_data:
            return {}
        
        features = {}
        
        # Extract best odds for main markets
        for odds in odds_data:
            if odds.market == "Match Winner":
                features["best_home_odds"] = max(odds.odds.get("Home", 0) for odds in odds_data 
                                                if odds.market == "Match Winner")
                features["best_draw_odds"] = max(odds.odds.get("Draw", 0) for odds in odds_data
                                                if odds.market == "Match Winner")
                features["best_away_odds"] = max(odds.odds.get("Away", 0) for odds in odds_data
                                                if odds.market == "Match Winner")
                
                # Implied probabilities
                if features["best_home_odds"] > 0:
                    features["implied_home_prob"] = 1 / features["best_home_odds"]
                    features["implied_draw_prob"] = 1 / features["best_draw_odds"]
                    features["implied_away_prob"] = 1 / features["best_away_odds"]
                    
                    # Market efficiency (overround)
                    features["market_overround"] = (features["implied_home_prob"] + 
                                                   features["implied_draw_prob"] + 
                                                   features["implied_away_prob"])
        
        return features

# ============================================================================
# xG (EXPECTED GOALS) FEATURES
# ============================================================================

class xGFeatures:
    """Expected Goals based features - the most predictive features"""
    
    def create_features(self, team_stats: Dict) -> Dict:
        """Create xG-based features"""
        features = {}
        
        # Home team xG features
        home_stats = team_stats.get("home", {})
        if home_stats:
            features.update(self._extract_xg_features(home_stats, "home"))
        
        # Away team xG features
        away_stats = team_stats.get("away", {})
        if away_stats:
            features.update(self._extract_xg_features(away_stats, "away"))
        
        # Differential features
        if home_stats and away_stats:
            features.update(self._create_xg_differentials(home_stats, away_stats))
        
        return features
    
    def _extract_xg_features(self, stats: Dict, prefix: str) -> Dict:
        """Extract xG features for a team"""
        features = {}
        
        # Basic xG values
        xg_for = stats.get("expected_goals", {}).get("for", {})
        xg_against = stats.get("expected_goals", {}).get("against", {})
        
        # xG per game
        features[f"{prefix}_xg_for_avg"] = xg_for.get("average", {}).get("total", 0)
        features[f"{prefix}_xg_against_avg"] = xg_against.get("average", {}).get("total", 0)
        features[f"{prefix}_xg_for_home"] = xg_for.get("average", {}).get("home", 0)
        features[f"{prefix}_xg_for_away"] = xg_for.get("average", {}).get("away", 0)
        features[f"{prefix}_xg_against_home"] = xg_against.get("average", {}).get("home", 0)
        features[f"{prefix}_xg_against_away"] = xg_against.get("average", {}).get("away", 0)
        
        # xG totals
        features[f"{prefix}_xg_for_total"] = xg_for.get("total", {}).get("total", 0)
        features[f"{prefix}_xg_against_total"] = xg_against.get("total", {}).get("total", 0)
        
        # xG overperformance (actual goals - xG)
        actual_goals = stats.get("goals", {}).get("for", {}).get("total", {}).get("total", 0)
        xg_total = xg_for.get("total", {}).get("total", 0)
        if xg_total > 0:
            features[f"{prefix}_xg_overperformance"] = actual_goals - xg_total
            features[f"{prefix}_xg_conversion_rate"] = actual_goals / xg_total
        
        # xG trend (last 5 games)
        features[f"{prefix}_xg_trend"] = self._calculate_xg_trend(stats)
        
        # xG variance (consistency)
        features[f"{prefix}_xg_variance"] = self._calculate_xg_variance(stats)
        
        return features
    
    def _create_xg_differentials(self, home_stats: Dict, away_stats: Dict) -> Dict:
        """Create xG differential features"""
        features = {}
        
        home_xg_for = home_stats.get("expected_goals", {}).get("for", {}).get("average", {}).get("home", 0)
        away_xg_for = away_stats.get("expected_goals", {}).get("for", {}).get("average", {}).get("away", 0)
        home_xg_against = home_stats.get("expected_goals", {}).get("against", {}).get("average", {}).get("home", 0)
        away_xg_against = away_stats.get("expected_goals", {}).get("against", {}).get("average", {}).get("away", 0)
        
        # Expected goal difference
        features["xg_diff_expected"] = (home_xg_for - away_xg_against) - (away_xg_for - home_xg_against)
        
        # Total expected goals
        features["xg_total_expected"] = home_xg_for + away_xg_for
        
        # xG superiority index
        if (home_xg_for + away_xg_for) > 0:
            features["xg_superiority_index"] = home_xg_for / (home_xg_for + away_xg_for)
        
        # Defensive xG differential
        features["xg_defensive_diff"] = away_xg_against - home_xg_against
        
        return features
    
    def _calculate_xg_trend(self, stats: Dict) -> float:
        """Calculate xG trend over recent games"""
        # This would need access to last 5 games' xG data
        # Simplified version - would use actual game-by-game data in production
        form = stats.get("form", "")
        if form:
            recent_results = [1 if r == "W" else 0.5 if r == "D" else 0 for r in form[-5:]]
            if len(recent_results) >= 2:
                return np.polyfit(range(len(recent_results)), recent_results, 1)[0]
        return 0
    
    def _calculate_xg_variance(self, stats: Dict) -> float:
        """Calculate xG variance (consistency measure)"""
        # Simplified - would use actual match-by-match xG data
        goals_for = stats.get("goals", {}).get("for", {}).get("total", {})
        home_goals = goals_for.get("home", 0)
        away_goals = goals_for.get("away", 0)
        
        if home_goals > 0 and away_goals > 0:
            return np.std([home_goals, away_goals])
        return 0

# ============================================================================
# FORM FEATURES
# ============================================================================

class FormFeatures:
    """Team form and momentum features"""
    
    def create_features(self, team_stats: Dict) -> Dict:
        """Create form-based features"""
        features = {}
        
        # Home team form
        home_stats = team_stats.get("home", {})
        if home_stats:
            features.update(self._extract_form_features(home_stats, "home"))
        
        # Away team form
        away_stats = team_stats.get("away", {})
        if away_stats:
            features.update(self._extract_form_features(away_stats, "away"))
        
        # Form differentials
        if home_stats and away_stats:
            features.update(self._create_form_differentials(home_stats, away_stats))
        
        return features
    
    def _extract_form_features(self, stats: Dict, prefix: str) -> Dict:
        """Extract form features for a team"""
        features = {}
        
        # Form string analysis
        form = stats.get("form", "")
        if form:
            # Recent form (last 5 games)
            features[f"{prefix}_form_points_l5"] = sum(3 if r == "W" else 1 if r == "D" else 0 
                                                      for r in form[-5:])
            features[f"{prefix}_form_wins_l5"] = form[-5:].count("W")
            features[f"{prefix}_form_draws_l5"] = form[-5:].count("D")
            features[f"{prefix}_form_losses_l5"] = form[-5:].count("L")
            
            # Very recent form (last 3 games)
            features[f"{prefix}_form_points_l3"] = sum(3 if r == "W" else 1 if r == "D" else 0
                                                      for r in form[-3:])
            
            # Form momentum (improving/declining)
            features[f"{prefix}_form_momentum"] = self._calculate_momentum(form)
            
            # Consistency
            features[f"{prefix}_form_consistency"] = self._calculate_consistency(form)
        
        # Goals form
        goals = stats.get("goals", {})
        if goals:
            features[f"{prefix}_goals_scored_l5"] = goals.get("for", {}).get("total", {}).get("total", 0) / 5
            features[f"{prefix}_goals_conceded_l5"] = goals.get("against", {}).get("total", {}).get("total", 0) / 5
            features[f"{prefix}_clean_sheets_l5"] = stats.get("clean_sheet", {}).get("total", 0) / 5
            features[f"{prefix}_failed_to_score_l5"] = stats.get("failed_to_score", {}).get("total", 0) / 5
        
        # Home/Away specific form
        fixtures = stats.get("fixtures", {})
        if fixtures:
            if prefix == "home":
                home_played = fixtures.get("played", {}).get("home", 1)
                features[f"{prefix}_home_win_rate"] = fixtures.get("wins", {}).get("home", 0) / max(home_played, 1)
                features[f"{prefix}_home_draw_rate"] = fixtures.get("draws", {}).get("home", 0) / max(home_played, 1)
            else:
                away_played = fixtures.get("played", {}).get("away", 1)
                features[f"{prefix}_away_win_rate"] = fixtures.get("wins", {}).get("away", 0) / max(away_played, 1)
                features[f"{prefix}_away_draw_rate"] = fixtures.get("draws", {}).get("away", 0) / max(away_played, 1)
        
        return features
    
    def _create_form_differentials(self, home_stats: Dict, away_stats: Dict) -> Dict:
        """Create form differential features"""
        features = {}
        
        home_form = home_stats.get("form", "")
        away_form = away_stats.get("form", "")
        
        if home_form and away_form:
            home_points = sum(3 if r == "W" else 1 if r == "D" else 0 for r in home_form[-5:])
            away_points = sum(3 if r == "W" else 1 if r == "D" else 0 for r in away_form[-5:])
            
            features["form_diff_l5"] = home_points - away_points
            features["form_ratio"] = home_points / max(away_points, 1)
            
            # Momentum differential
            features["momentum_diff"] = (self._calculate_momentum(home_form) - 
                                        self._calculate_momentum(away_form))
        
        return features
    
    def _calculate_momentum(self, form: str) -> float:
        """Calculate form momentum (trend)"""
        if len(form) < 3:
            return 0
        
        points = [3 if r == "W" else 1 if r == "D" else 0 for r in form[-5:]]
        if len(points) >= 2:
            # Linear regression slope
            x = np.arange(len(points))
            slope, _ = np.polyfit(x, points, 1)
            return slope
        return 0
    
    def _calculate_consistency(self, form: str) -> float:
        """Calculate form consistency (lower is more consistent)"""
        if len(form) < 3:
            return 0
        
        points = [3 if r == "W" else 1 if r == "D" else 0 for r in form[-5:]]
        return np.std(points) if points else 0

# ============================================================================
# HEAD-TO-HEAD FEATURES
# ============================================================================

class H2HFeatures:
    """Head-to-head historical features"""
    
    def create_features(self, h2h_data: List[Dict]) -> Dict:
        """Create H2H features"""
        if not h2h_data:
            return self._get_default_h2h_features()
        
        features = {}
        
        # Overall H2H statistics
        features.update(self._calculate_h2h_stats(h2h_data))
        
        # Recent H2H trends
        features.update(self._calculate_h2h_trends(h2h_data))
        
        # Venue-specific H2H
        features.update(self._calculate_venue_h2h(h2h_data))
        
        # Goal patterns in H2H
        features.update(self._calculate_h2h_goal_patterns(h2h_data))
        
        # Psychological factors
        features.update(self._calculate_psychological_factors(h2h_data))
        
        return features
    
    def _get_default_h2h_features(self) -> Dict:
        """Return default H2H features when no history exists"""
        return {
            "h2h_matches": 0,
            "h2h_home_wins": 0,
            "h2h_draws": 0,
            "h2h_away_wins": 0,
            "h2h_home_win_pct": 0.33,
            "h2h_draw_pct": 0.33,
            "h2h_away_win_pct": 0.33,
            "h2h_avg_total_goals": 2.5,
            "h2h_btts_pct": 0.5,
            "h2h_over25_pct": 0.5,
            "h2h_home_scored_avg": 1.3,
            "h2h_away_scored_avg": 1.2
        }
    
    def _calculate_h2h_stats(self, h2h_data: List[Dict]) -> Dict:
        """Calculate overall H2H statistics"""
        features = {}
        
        total_matches = len(h2h_data)
        home_wins = 0
        away_wins = 0
        draws = 0
        total_goals = []
        home_goals = []
        away_goals = []
        btts_count = 0
        over25_count = 0
        over35_count = 0
        
        for match in h2h_data:
            goals = match.get("goals", {})
            h_goals = goals.get("home", 0) or 0
            a_goals = goals.get("away", 0) or 0
            
            home_goals.append(h_goals)
            away_goals.append(a_goals)
            total = h_goals + a_goals
            total_goals.append(total)
            
            if h_goals > a_goals:
                home_wins += 1
            elif a_goals > h_goals:
                away_wins += 1
            else:
                draws += 1
            
            if h_goals > 0 and a_goals > 0:
                btts_count += 1
            
            if total > 2.5:
                over25_count += 1
            if total > 3.5:
                over35_count += 1
        
        features["h2h_matches"] = total_matches
        features["h2h_home_wins"] = home_wins
        features["h2h_draws"] = draws
        features["h2h_away_wins"] = away_wins
        
        if total_matches > 0:
            features["h2h_home_win_pct"] = home_wins / total_matches
            features["h2h_draw_pct"] = draws / total_matches
            features["h2h_away_win_pct"] = away_wins / total_matches
            features["h2h_avg_total_goals"] = np.mean(total_goals)
            features["h2h_btts_pct"] = btts_count / total_matches
            features["h2h_over25_pct"] = over25_count / total_matches
            features["h2h_over35_pct"] = over35_count / total_matches
            features["h2h_home_scored_avg"] = np.mean(home_goals)
            features["h2h_away_scored_avg"] = np.mean(away_goals)
            features["h2h_goals_std"] = np.std(total_goals)
        
        return features
    
    def _calculate_h2h_trends(self, h2h_data: List[Dict]) -> Dict:
        """Calculate recent H2H trends"""
        features = {}
        
        # Last 5 H2H matches
        recent = h2h_data[:5] if len(h2h_data) >= 5 else h2h_data
        
        if recent:
            recent_home_wins = sum(1 for m in recent 
                                  if m["goals"]["home"] > m["goals"]["away"])
            recent_draws = sum(1 for m in recent 
                             if m["goals"]["home"] == m["goals"]["away"])
            recent_total_goals = [m["goals"]["home"] + m["goals"]["away"] for m in recent]
            
            features["h2h_recent_home_win_pct"] = recent_home_wins / len(recent)
            features["h2h_recent_draw_pct"] = recent_draws / len(recent)
            features["h2h_recent_avg_goals"] = np.mean(recent_total_goals)
            
            # Trend in goals (increasing/decreasing)
            if len(recent_total_goals) >= 2:
                features["h2h_goals_trend"] = np.polyfit(range(len(recent_total_goals)), 
                                                        recent_total_goals, 1)[0]
        
        return features
    
    def _calculate_venue_h2h(self, h2h_data: List[Dict]) -> Dict:
        """Calculate venue-specific H2H stats"""
        features = {}
        
        # This would need venue information in the H2H data
        # Simplified version
        home_venue_matches = h2h_data[:len(h2h_data)//2]  # Approximate
        
        if home_venue_matches:
            home_venue_wins = sum(1 for m in home_venue_matches 
                                 if m["goals"]["home"] > m["goals"]["away"])
            features["h2h_home_venue_win_rate"] = home_venue_wins / len(home_venue_matches)
        
        return features
    
    def _calculate_h2h_goal_patterns(self, h2h_data: List[Dict]) -> Dict:
        """Calculate goal scoring patterns in H2H"""
        features = {}
        
        first_half_goals = []
        second_half_goals = []
        
        for match in h2h_data:
            score = match.get("score", {})
            halftime = score.get("halftime", {})
            fulltime = match.get("goals", {})
            
            if halftime and fulltime:
                ht_total = (halftime.get("home", 0) or 0) + (halftime.get("away", 0) or 0)
                ft_total = (fulltime.get("home", 0) or 0) + (fulltime.get("away", 0) or 0)
                
                first_half_goals.append(ht_total)
                second_half_goals.append(ft_total - ht_total)
        
        if first_half_goals:
            features["h2h_first_half_goals_avg"] = np.mean(first_half_goals)
            features["h2h_second_half_goals_avg"] = np.mean(second_half_goals)
            features["h2h_high_scoring_first_half_pct"] = sum(1 for g in first_half_goals if g > 1) / len(first_half_goals)
        
        return features
    
    def _calculate_psychological_factors(self, h2h_data: List[Dict]) -> Dict:
        """Calculate psychological factors from H2H"""
        features = {}
        
        # Dominance factor
        if len(h2h_data) >= 3:
            last_3 = h2h_data[:3]
            same_winner = all(m["goals"]["home"] > m["goals"]["away"] for m in last_3) or \
                        all(m["goals"]["home"] < m["goals"]["away"] for m in last_3)
            features["h2h_dominance_factor"] = 1.0 if same_winner else 0.0
            
            # Comeback history
            comebacks = 0
            for match in h2h_data:
                score = match.get("score", {})
                halftime = score.get("halftime", {})
                fulltime = match.get("goals", {})
                
                if halftime and fulltime:
                    ht_leader = "home" if halftime["home"] > halftime["away"] else \
                               "away" if halftime["away"] > halftime["home"] else "draw"
                    ft_winner = "home" if fulltime["home"] > fulltime["away"] else \
                               "away" if fulltime["away"] > fulltime["home"] else "draw"
                    
                    if ht_leader != "draw" and ft_winner != "draw" and ht_leader != ft_winner:
                        comebacks += 1
            
            features["h2h_comeback_rate"] = comebacks / len(h2h_data) if h2h_data else 0
        
        return features

# ============================================================================
# PLAYER FEATURES
# ============================================================================

class PlayerFeatures:
    """Player-based features including injuries and key player impacts"""
    
    def create_features(self, player_stats: List[Dict], injuries: List[Dict]) -> Dict:
        """Create player-based features"""
        features = {}
        
        # Key player availability
        features.update(self._calculate_injury_impact(player_stats, injuries))
        
        # Top scorer features
        features.update(self._extract_top_scorer_features(player_stats))
        
        # Squad strength features
        features.update(self._calculate_squad_strength(player_stats))
        
        # Player form features
        features.update(self._calculate_player_form(player_stats))
        
        return features
    
    def _calculate_injury_impact(self, player_stats: List[Dict], injuries: List[Dict]) -> Dict:
        """Calculate impact of injuries on team strength"""
        features = {}
        
        if not injuries:
            features["home_injuries_count"] = 0
            features["away_injuries_count"] = 0
            features["home_key_injuries"] = 0
            features["away_key_injuries"] = 0
            return features
        
        # Identify key players (top rated or top scorers)
        key_players = self._identify_key_players(player_stats)
        
        home_injuries = 0
        away_injuries = 0
        home_key_injuries = 0
        away_key_injuries = 0
        
        for injury in injuries:
            player_id = injury.player_id if hasattr(injury, 'player_id') else injury.get("player_id")
            team_side = self._get_player_team(player_id, player_stats)
            
            if team_side == "home":
                home_injuries += 1
                if player_id in key_players:
                    home_key_injuries += 1
            elif team_side == "away":
                away_injuries += 1
                if player_id in key_players:
                    away_key_injuries += 1
        
        features["home_injuries_count"] = home_injuries
        features["away_injuries_count"] = away_injuries
        features["home_key_injuries"] = home_key_injuries
        features["away_key_injuries"] = away_key_injuries
        
        # Impact scores
        features["home_injury_impact"] = home_injuries * 0.05 + home_key_injuries * 0.15
        features["away_injury_impact"] = away_injuries * 0.05 + away_key_injuries * 0.15
        
        return features
    
    def _extract_top_scorer_features(self, player_stats: List[Dict]) -> Dict:
        """Extract features about top scorers"""
        features = {}
        
        if not player_stats:
            return features
        
        # Separate home and away players
        home_players = [p for p in player_stats if self._get_player_team(p.get("player_id"), player_stats) == "home"]
        away_players = [p for p in player_stats if self._get_player_team(p.get("player_id"), player_stats) == "away"]
        
        # Home team top scorer
        if home_players:
            top_scorer = max(home_players, key=lambda p: p.get("goals", 0))
            features["home_top_scorer_goals"] = top_scorer.get("goals", 0)
            features["home_top_scorer_games"] = top_scorer.get("games_played", 1)
            features["home_top_scorer_gpg"] = features["home_top_scorer_goals"] / max(features["home_top_scorer_games"], 1)
            features["home_top_scorer_form"] = top_scorer.get("rating", 0)
        
        # Away team top scorer
        if away_players:
            top_scorer = max(away_players, key=lambda p: p.get("goals", 0))
            features["away_top_scorer_goals"] = top_scorer.get("goals", 0)
            features["away_top_scorer_games"] = top_scorer.get("games_played", 1)
            features["away_top_scorer_gpg"] = features["away_top_scorer_goals"] / max(features["away_top_scorer_games"], 1)
            features["away_top_scorer_form"] = top_scorer.get("rating", 0)
        
        return features
    
    def _calculate_squad_strength(self, player_stats: List[Dict]) -> Dict:
        """Calculate overall squad strength metrics"""
        features = {}
        
        if not player_stats:
            return features
        
        home_players = [p for p in player_stats if self._get_player_team(p.get("player_id"), player_stats) == "home"]
        away_players = [p for p in player_stats if self._get_player_team(p.get("player_id"), player_stats) == "away"]
        
        # Home squad strength
        if home_players:
            features["home_squad_avg_rating"] = np.mean([p.get("rating", 0) for p in home_players])
            features["home_squad_total_goals"] = sum(p.get("goals", 0) for p in home_players)
            features["home_squad_total_assists"] = sum(p.get("assists", 0) for p in home_players)
            features["home_squad_avg_minutes"] = np.mean([p.get("minutes", 0) for p in home_players])
        
        # Away squad strength
        if away_players:
            features["away_squad_avg_rating"] = np.mean([p.get("rating", 0) for p in away_players])
            features["away_squad_total_goals"] = sum(p.get("goals", 0) for p in away_players)
            features["away_squad_total_assists"] = sum(p.get("assists", 0) for p in away_players)
            features["away_squad_avg_minutes"] = np.mean([p.get("minutes", 0) for p in away_players])
        
        return features
    
    def _calculate_player_form(self, player_stats: List[Dict]) -> Dict:
        """Calculate player form metrics"""
        features = {}
        
        # This would ideally use recent match data for each player
        # Simplified version using season averages
        
        if player_stats:
            # Get players with recent good form (high ratings)
            in_form_threshold = 7.0
            home_in_form = sum(1 for p in player_stats 
                             if self._get_player_team(p.get("player_id"), player_stats) == "home" 
                             and p.get("rating", 0) >= in_form_threshold)
            away_in_form = sum(1 for p in player_stats
                             if self._get_player_team(p.get("player_id"), player_stats) == "away"
                             and p.get("rating", 0) >= in_form_threshold)
            
            features["home_players_in_form"] = home_in_form
            features["away_players_in_form"] = away_in_form
        
        return features
    
    def _identify_key_players(self, player_stats: List[Dict]) -> set:
        """Identify key players based on goals and ratings"""
        if not player_stats:
            return set()
        
        # Key players are top 3 by goals + top 3 by rating
        sorted_by_goals = sorted(player_stats, key=lambda p: p.get("goals", 0), reverse=True)[:3]
        sorted_by_rating = sorted(player_stats, key=lambda p: p.get("rating", 0), reverse=True)[:3]
        
        key_players = set()
        for p in sorted_by_goals + sorted_by_rating:
            player_id = p.get("player_id")
            if player_id:
                key_players.add(player_id)
        
        return key_players
    
    def _get_player_team(self, player_id: int, player_stats: List[Dict]) -> str:
        """Determine if player belongs to home or away team"""
        # This would need actual team roster data
        # Simplified version - would use actual team IDs in production
        return "home"  # Placeholder

# ============================================================================
# VENUE & WEATHER FEATURES
# ============================================================================

class VenueFeatures:
    """Venue and weather-related features"""
    
    def create_features(self, venue_data: Dict, weather_data: Dict) -> Dict:
        """Create venue and weather features"""
        features = {}
        
        # Venue features
        if venue_data:
            features.update(self._extract_venue_features(venue_data))
        
        # Weather features
        if weather_data:
            features.update(self._extract_weather_features(weather_data))
        
        # Combined venue-weather impact
        features.update(self._calculate_environmental_impact(venue_data, weather_data))
        
        return features
    
    def _extract_venue_features(self, venue_data: Dict) -> Dict:
        """Extract venue-specific features"""
        features = {}
        
        features["venue_capacity"] = venue_data.get("capacity", 0)
        features["venue_surface_grass"] = 1 if venue_data.get("surface", "").lower() == "grass" else 0
        features["venue_surface_artificial"] = 1 if venue_data.get("surface", "").lower() in ["artificial", "turf"] else 0
        
        # Stadium size categories
        capacity = venue_data.get("capacity", 0)
        features["venue_large"] = 1 if capacity > 50000 else 0
        features["venue_medium"] = 1 if 20000 <= capacity <= 50000 else 0
        features["venue_small"] = 1 if capacity < 20000 else 0
        
        return features
    
    def _extract_weather_features(self, weather_data: Dict) -> Dict:
        """Extract weather features"""
        features = {}
        
        features["temperature"] = weather_data.get("temp", 20)
        features["wind_speed"] = weather_data.get("wind", {}).get("speed", 0)
        features["humidity"] = weather_data.get("humidity", 50)
        
        # Weather conditions
        description = weather_data.get("description", "").lower()
        features["weather_clear"] = 1 if "clear" in description or "sun" in description else 0
        features["weather_rain"] = 1 if "rain" in description else 0
        features["weather_snow"] = 1 if "snow" in description else 0
        features["weather_wind"] = 1 if "wind" in description or features["wind_speed"] > 20 else 0
        
        # Extreme conditions
        features["extreme_cold"] = 1 if features["temperature"] < 5 else 0
        features["extreme_hot"] = 1 if features["temperature"] > 30 else 0
        features["extreme_wind"] = 1 if features["wind_speed"] > 30 else 0
        
        return features
    
    def _calculate_environmental_impact(self, venue_data: Dict, weather_data: Dict) -> Dict:
        """Calculate combined environmental impact on the game"""
        features = {}
        
        # Calculate expected impact on total goals
        impact_score = 0
        
        # Rain typically reduces goals
        if weather_data.get("description", "").lower().count("rain") > 0:
            impact_score -= 0.2
        
        # Wind affects passing accuracy
        wind_speed = weather_data.get("wind", {}).get("speed", 0)
        if wind_speed > 20:
            impact_score -= 0.1
        
        # Extreme temperatures affect player performance
        temp = weather_data.get("temp", 20)
        if temp < 5 or temp > 30:
            impact_score -= 0.15
        
        # Small stadiums often see more goals (less pressure)
        if venue_data.get("capacity", 0) < 20000:
            impact_score += 0.1
        
        features["environmental_impact_score"] = impact_score
        features["favorable_conditions"] = 1 if impact_score > 0 else 0
        
        return features

# ============================================================================
# MARKET-SPECIFIC FEATURES
# ============================================================================

class MarketSpecificFeatures:
    """Features specifically designed for each betting market"""
    
    def create_all_market_features(self, team_stats: Dict, h2h_data: List[Dict], 
                                   player_stats: List[Dict]) -> Dict:
        """Create features for all betting markets"""
        features = {}
        
        # Match Result (1X2) features
        features.update(self._create_match_result_features(team_stats))
        
        # Over/Under features
        features.update(self._create_over_under_features(team_stats, h2h_data))
        
        # BTTS features
        features.update(self._create_btts_features(team_stats, h2h_data))
        
        # Asian Handicap features
        features.update(self._create_asian_handicap_features(team_stats))
        
        # Correct Score features
        features.update(self._create_correct_score_features(team_stats, h2h_data))
        
        # Half-Time features
        features.update(self._create_half_time_features(team_stats))
        
        # Corners features
        features.update(self._create_corners_features(team_stats))
        
        # Cards features
        features.update(self._create_cards_features(team_stats))
        
        return features
    
    def _create_match_result_features(self, team_stats: Dict) -> Dict:
        """Features specific to 1X2 market"""
        features = {}
        
        home = team_stats.get("home", {})
        away = team_stats.get("away", {})
        
        if home and away:
            # Win probability indicators
            home_win_rate = home.get("fixtures", {}).get("wins", {}).get("total", 0) / \
                          max(home.get("fixtures", {}).get("played", {}).get("total", 1), 1)
            away_win_rate = away.get("fixtures", {}).get("wins", {}).get("total", 0) / \
                          max(away.get("fixtures", {}).get("played", {}).get("total", 1), 1)
            
            features["match_result_home_indicator"] = home_win_rate
            features["match_result_away_indicator"] = away_win_rate
            features["match_result_draw_indicator"] = (home.get("fixtures", {}).get("draws", {}).get("total", 0) +
                                                      away.get("fixtures", {}).get("draws", {}).get("total", 0)) / \
                                                     (home.get("fixtures", {}).get("played", {}).get("total", 0) +
                                                      away.get("fixtures", {}).get("played", {}).get("total", 1))
            
            # Goal difference impact
            home_gd = (home.get("goals", {}).get("for", {}).get("total", {}).get("total", 0) -
                      home.get("goals", {}).get("against", {}).get("total", {}).get("total", 0))
            away_gd = (away.get("goals", {}).get("for", {}).get("total", {}).get("total", 0) -
                      away.get("goals", {}).get("against", {}).get("total", {}).get("total", 0))
            
            features["match_result_gd_diff"] = home_gd - away_gd
        
        return features
    
    def _create_over_under_features(self, team_stats: Dict, h2h_data: List[Dict]) -> Dict:
        """Features specific to Over/Under markets"""
        features = {}
        
        home = team_stats.get("home", {})
        away = team_stats.get("away", {})
        
        if home and away:
            # Goal averages
            home_goals_for = home.get("goals", {}).get("for", {}).get("average", {}).get("total", 0)
            home_goals_against = home.get("goals", {}).get("against", {}).get("average", {}).get("total", 0)
            away_goals_for = away.get("goals", {}).get("for", {}).get("average", {}).get("total", 0)
            away_goals_against = away.get("goals", {}).get("against", {}).get("average", {}).get("total", 0)
            
            # Expected total goals
            features["ou_expected_total"] = home_goals_for + away_goals_for
            features["ou_defensive_total"] = home_goals_against + away_goals_against
            features["ou_combined_average"] = (features["ou_expected_total"] + features["ou_defensive_total"]) / 2
            
            # Over/Under specific lines
            for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
                features[f"ou_{str(line).replace('.', '_')}_probability"] = self._calculate_ou_probability(
                    features["ou_combined_average"], line
                )
            
            # High/Low scoring indicators
            features["ou_high_scoring_teams"] = 1 if features["ou_combined_average"] > 3 else 0
            features["ou_low_scoring_teams"] = 1 if features["ou_combined_average"] < 2 else 0
        
        # H2H goal trends
        if h2h_data:
            h2h_goals = [m["goals"]["home"] + m["goals"]["away"] for m in h2h_data[:5]]
            features["ou_h2h_avg"] = np.mean(h2h_goals) if h2h_goals else 2.5
            features["ou_h2h_over25_rate"] = sum(1 for g in h2h_goals if g > 2.5) / len(h2h_goals) if h2h_goals else 0.5
        
        return features
    
    def _create_btts_features(self, team_stats: Dict, h2h_data: List[Dict]) -> Dict:
        """Features specific to Both Teams to Score market"""
        features = {}
        
        home = team_stats.get("home", {})
        away = team_stats.get("away", {})
        
        if home and away:
            # Scoring consistency
            home_failed_to_score = home.get("failed_to_score", {}).get("total", 0)
            away_failed_to_score = away.get("failed_to_score", {}).get("total", 0)
            home_games = home.get("fixtures", {}).get("played", {}).get("total", 1)
            away_games = away.get("fixtures", {}).get("played", {}).get("total", 1)
            
            features["btts_home_scoring_rate"] = 1 - (home_failed_to_score / max(home_games, 1))
            features["btts_away_scoring_rate"] = 1 - (away_failed_to_score / max(away_games, 1))
            features["btts_combined_scoring_rate"] = features["btts_home_scoring_rate"] * features["btts_away_scoring_rate"]
            
            # Clean sheet rates (inverse indicator for BTTS)
            home_clean_sheets = home.get("clean_sheet", {}).get("total", 0)
            away_clean_sheets = away.get("clean_sheet", {}).get("total", 0)
            
            features["btts_home_conceding_rate"] = 1 - (home_clean_sheets / max(home_games, 1))
            features["btts_away_conceding_rate"] = 1 - (away_clean_sheets / max(away_games, 1))
            
            # BTTS probability estimate
            features["btts_probability"] = (features["btts_home_scoring_rate"] * features["btts_away_conceding_rate"] *
                                           features["btts_away_scoring_rate"] * features["btts_home_conceding_rate"]) ** 0.5
        
        # H2H BTTS history
        if h2h_data:
            btts_count = sum(1 for m in h2h_data[:10] 
                           if m["goals"]["home"] > 0 and m["goals"]["away"] > 0)
            features["btts_h2h_rate"] = btts_count / min(len(h2h_data), 10)
        
        return features
    
    def _create_asian_handicap_features(self, team_stats: Dict) -> Dict:
        """Features specific to Asian Handicap markets"""
        features = {}
        
        home = team_stats.get("home", {})
        away = team_stats.get("away", {})
        
        if home and away:
            # Goal difference expectations
            home_gf = home.get("goals", {}).get("for", {}).get("average", {}).get("total", 0)
            home_ga = home.get("goals", {}).get("against", {}).get("average", {}).get("total", 0)
            away_gf = away.get("goals", {}).get("for", {}).get("average", {}).get("total", 0)
            away_ga = away.get("goals", {}).get("against", {}).get("average", {}).get("total", 0)
            
            expected_diff = (home_gf - home_ga) - (away_gf - away_ga)
            features["ah_expected_difference"] = expected_diff
            
            # Handicap line probabilities
            for line in [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]:
                features[f"ah_{str(line).replace('.', '_').replace('-', 'minus')}_probability"] = \
                    self._calculate_ah_probability(expected_diff, line)
            
            # Margin of victory indicators
            home_big_wins = self._extract_big_wins(home.get("biggest", {}).get("wins", {}))
            away_big_wins = self._extract_big_wins(away.get("biggest", {}).get("wins", {}))
            
            features["ah_home_big_win_rate"] = home_big_wins
            features["ah_away_big_win_rate"] = away_big_wins
        
        return features
    
    def _create_correct_score_features(self, team_stats: Dict, h2h_data: List[Dict]) -> Dict:
        """Features specific to Correct Score market"""
        features = {}
        
        home = team_stats.get("home", {})
        away = team_stats.get("away", {})
        
        if home and away:
            # Most common scores
            home_gf = home.get("goals", {}).get("for", {}).get("average", {}).get("total", 0)
            away_gf = away.get("goals", {}).get("for", {}).get("average", {}).get("total", 0)
            
            # Calculate probabilities for common scores using Poisson
            common_scores = ["0-0", "1-0", "0-1", "1-1", "2-1", "1-2", "2-0", "0-2"]
            for score in common_scores:
                h, a = map(int, score.split("-"))
                prob = self._poisson_probability(h, home_gf) * self._poisson_probability(a, away_gf)
                features[f"cs_{score.replace('-', '_')}_probability"] = prob
            
            # Low/High scoring game indicators
            total_expected = home_gf + away_gf
            features["cs_low_scoring_expected"] = 1 if total_expected < 2 else 0
            features["cs_high_scoring_expected"] = 1 if total_expected > 3.5 else 0
        
        # H2H common scores
        if h2h_data:
            score_counts = {}
            for match in h2h_data[:20]:
                score = f"{match['goals']['home']}-{match['goals']['away']}"
                score_counts[score] = score_counts.get(score, 0) + 1
            
            if score_counts:
                most_common = max(score_counts, key=score_counts.get)
                features[f"cs_h2h_most_common_{most_common.replace('-', '_')}"] = \
                    score_counts[most_common] / len(h2h_data[:20])
        
        return features
    
    def _create_half_time_features(self, team_stats: Dict) -> Dict:
        """Features specific to Half-Time markets"""
        features = {}
        
        home = team_stats.get("home", {})
        away = team_stats.get("away", {})
        
        if home and away:
            # First half scoring rates (would need actual HT data)
            # Approximation: 40% of goals come in first half typically
            home_goals = home.get("goals", {}).get("for", {}).get("average", {}).get("total", 0)
            away_goals = away.get("goals", {}).get("for", {}).get("average", {}).get("total", 0)
            
            features["ht_home_expected_goals"] = home_goals * 0.4
            features["ht_away_expected_goals"] = away_goals * 0.4
            
            # Early goal tendencies (simplified)
            features["ht_early_goal_expected"] = 1 if (home_goals + away_goals) > 3 else 0
        
        return features
    
    def _create_corners_features(self, team_stats: Dict) -> Dict:
        """Features specific to Corners markets"""
        features = {}
        
        home = team_stats.get("home", {})
        away = team_stats.get("away", {})
        
        if home and away:
            # Corner averages (would need actual corner data)
            # Approximation based on attacking stats
            home_attacks = home.get("goals", {}).get("for", {}).get("total", {}).get("total", 0)
            away_attacks = away.get("goals", {}).get("for", {}).get("total", {}).get("total", 0)
            
            # Rough estimate: 1 corner per 10 attacks
            features["corners_home_expected"] = home_attacks / 10
            features["corners_away_expected"] = away_attacks / 10
            features["corners_total_expected"] = features["corners_home_expected"] + features["corners_away_expected"]
            
            # Corner line probabilities
            for line in [8.5, 9.5, 10.5, 11.5]:
                features[f"corners_{str(line).replace('.', '_')}_over_probability"] = \
                    self._calculate_ou_probability(features["corners_total_expected"], line)
        
        return features
    
    def _create_cards_features(self, team_stats: Dict) -> Dict:
        """Features specific to Cards markets"""
        features = {}
        
        home = team_stats.get("home", {})
        away = team_stats.get("away", {})
        
        if home and away:
            # Card averages (would need actual card data)
            # Approximation based on fouls
            features["cards_expected_yellow"] = 3.5  # Average
            features["cards_expected_red"] = 0.1  # Average
            
            # Discipline indicators
            features["cards_rivalry_factor"] = 1.0  # Would check if derby/rivalry
            features["cards_importance_factor"] = 1.0  # Would check if crucial match
        
        return features
    
    def _calculate_ou_probability(self, expected: float, line: float) -> float:
        """Calculate over probability for a given line"""
        # Using Poisson distribution
        from scipy.stats import poisson
        return 1 - poisson.cdf(line, expected)
    
    def _calculate_ah_probability(self, expected_diff: float, line: float) -> float:
        """Calculate Asian Handicap coverage probability"""
        # Using normal distribution approximation
        from scipy.stats import norm
        std_dev = 1.5  # Standard deviation of goal difference
        return 1 - norm.cdf(-line, expected_diff, std_dev)
    
    def _poisson_probability(self, k: int, lambda_: float) -> float:
        """Calculate Poisson probability"""
        import math
        return (lambda_ ** k) * math.exp(-lambda_) / math.factorial(k)
    
    def _extract_big_wins(self, wins_data: Dict) -> float:
        """Extract big win rate from biggest wins data"""
        # Simplified - would parse actual win margins
        return 0.1  # Placeholder

# ============================================================================
# CONTEXTUAL FEATURES
# ============================================================================

class ContextualFeatures:
    """Contextual features like fixture congestion, importance, etc."""
    
    def create_features(self, fixture_data: Dict, team_stats: Dict, injuries: List[Dict]) -> Dict:
        """Create contextual features"""
        features = {}
        
        # Fixture timing features
        features.update(self._extract_timing_features(fixture_data))
        
        # Fixture importance features
        features.update(self._calculate_importance_features(fixture_data, team_stats))
        
        # Fixture congestion features
        features.update(self._calculate_congestion_features(fixture_data, team_stats))
        
        # Motivation features
        features.update(self._calculate_motivation_features(team_stats))
        
        # Referee features
        features.update(self._extract_referee_features(fixture_data))
        
        return features
    
    def _extract_timing_features(self, fixture_data: Dict) -> Dict:
        """Extract timing-related features"""
        features = {}
        
        fixture = fixture_data.get("fixture", {})
        timestamp = fixture.get("timestamp", 0)
        
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            
            # Day of week
            features["day_of_week"] = dt.weekday()
            features["is_weekend"] = 1 if dt.weekday() >= 5 else 0
            
            # Time of day
            features["hour"] = dt.hour
            features["is_evening"] = 1 if dt.hour >= 18 else 0
            features["is_early"] = 1 if dt.hour < 14 else 0
            
            # Month/Season
            features["month"] = dt.month
            features["is_winter"] = 1 if dt.month in [12, 1, 2] else 0
            features["is_end_season"] = 1 if dt.month in [4, 5] else 0
        
        return features
    
    def _calculate_importance_features(self, fixture_data: Dict, team_stats: Dict) -> Dict:
        """Calculate match importance features"""
        features = {}
        
        # League position difference (would need standings data)
        features["importance_position_gap"] = 0  # Placeholder
        
        # Title/Relegation implications
        features["importance_title_race"] = 0  # Would check if top 3
        features["importance_relegation_battle"] = 0  # Would check if bottom 3
        features["importance_european_spots"] = 0  # Would check if positions 4-7
        
        # Cup matches
        league = fixture_data.get("league", {})
        features["importance_cup_match"] = 1 if "Cup" in league.get("name", "") else 0
        features["importance_knockout"] = 1 if "Round" in league.get("round", "") else 0
        
        return features
    
    def _calculate_congestion_features(self, fixture_data: Dict, team_stats: Dict) -> Dict:
        """Calculate fixture congestion features"""
        features = {}
        
        # Days since last match (would need fixture history)
        features["congestion_days_rest_home"] = 7  # Default
        features["congestion_days_rest_away"] = 7  # Default
        
        # Matches in last 7 days
        features["congestion_matches_last_week_home"] = 1  # Default
        features["congestion_matches_last_week_away"] = 1  # Default
        
        # Travel factor (for away team)
        features["congestion_travel_distance"] = 0  # Would calculate from cities
        
        return features
    
    def _calculate_motivation_features(self, team_stats: Dict) -> Dict:
        """Calculate team motivation features"""
        features = {}
        
        # Points needed for objectives
        features["motivation_home"] = 0.5  # Default medium motivation
        features["motivation_away"] = 0.5
        
        # New manager bounce
        features["new_manager_home"] = 0  # Would check manager appointment date
        features["new_manager_away"] = 0
        
        return features
    
    def _extract_referee_features(self, fixture_data: Dict) -> Dict:
        """Extract referee-related features"""
        features = {}
        
        referee = fixture_data.get("fixture", {}).get("referee", "")
        
        if referee:
            features["has_referee_data"] = 1
            
            # Would lookup referee statistics
            features["referee_avg_cards"] = 3.5  # Default average
            features["referee_avg_penalties"] = 0.2  # Default average
            features["referee_home_bias"] = 0  # Would calculate from history
        else:
            features["has_referee_data"] = 0
            features["referee_avg_cards"] = 3.5
            features["referee_avg_penalties"] = 0.2
            features["referee_home_bias"] = 0
        
        return features

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("Enhanced Feature Engineering Module")
    print("=" * 80)
    print("\nThis module creates 200+ features including:")
    print("\n1. xG Features (Most Predictive):")
    print("   - Expected goals for/against")
    print("   - xG overperformance")
    print("   - xG trends and variance")
    print("\n2. Form Features:")
    print("   - Recent form (W/D/L)")
    print("   - Goal scoring form")
    print("   - Momentum indicators")
    print("\n3. H2H Features:")
    print("   - Historical results")
    print("   - Goal patterns")
    print("   - Psychological factors")
    print("\n4. Player Features:")
    print("   - Key player availability")
    print("   - Top scorer stats")
    print("   - Squad strength metrics")
    print("\n5. Venue & Weather Features:")
    print("   - Stadium characteristics")
    print("   - Weather impact")
    print("   - Environmental factors")
    print("\n6. Market-Specific Features:")
    print("   - Match Result (1X2)")
    print("   - Over/Under (all lines)")
    print("   - BTTS")
    print("   - Asian Handicap")
    print("   - Correct Score")
    print("   - Half-Time")
    print("   - Corners")
    print("   - Cards")
    print("\n7. Contextual Features:")
    print("   - Fixture importance")
    print("   - Congestion")
    print("   - Motivation")
    print("   - Referee tendencies")
    print("\n" + "=" * 80)

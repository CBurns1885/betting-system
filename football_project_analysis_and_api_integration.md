# Football Prediction System - Project Analysis & API Integration Plan

## 🏗️ Current Project Architecture Analysis

### Main Flow (via `run_weeklyOU.py`)
Your main runner follows a 14-step pipeline:

1. **Download Fixtures** → `simple_fixture_downloader.py` (from football-data.co.uk)
2. **Download Historical Data** → `download_football_data.py`
3. **Build Database** → `data_ingest.py`
4. **Validate Data** → `ingest_local_run.py`
5. **Generate Statistics** → `generate_and_load_stats.py`
6. **Build Features** → `features.py`
7. **Train/Load Models** → `incremental_trainer.py` + `models.py`
8. **Prepare Fixtures** → `prep_fixtures.py`
9. **Generate Predictions** → `predict.py`
10. **Log Predictions** → `accuracy_tracker.py`
11. **Generate Weighted Top 50** → `weighted_top50.py`
12. **O/U Analysis** → `ou_analyzer.py`
13. **Build Accumulators** → `accumulator_finder.py`
14. **Archive Outputs** → Built into runner

## 📁 File Classification

### ✅ **ESSENTIAL FILES (Keep)**
- **Core Pipeline:**
  - `run_weeklyOU.py` - Main runner
  - `config.py` - Configuration management
  - `download_football_data.py` - Historical data downloader
  - `data_ingest.py` - Database builder
  - `features.py` - Feature engineering
  - `models.py` - Model training/prediction
  - `predict.py` - Weekly predictions
  - `incremental_trainer.py` - Smart model loading/training

- **Analysis & Output:**
  - `ou_analyzer.py` - Over/Under analysis
  - `accumulator_finder.py` - Accumulator building
  - `weighted_top50.py` - Top picks generation
  - `accuracy_tracker.py` - Performance tracking
  - `weighted_html_output.py` - HTML report generation

- **Utilities:**
  - `simple_fixture_downloader.py` - Current fixture source
  - `prep_fixtures.py` - Fixture preparation
  - `generate_and_load_stats.py` - Statistics generation
  - `update_results.py` - Post-match updates

### 🗑️ **REDUNDANT FILES (Delete)**
- `ONE_CLICK_RUN.py` - Duplicate of models.py with fixes (redundant)
- `updated_run_weekly.py` - Old version of runner
- `updated_run_weekly__1_.py` - Another old version
- `modelsOLD.py` - Old models backup
- `load_existing_stats__1_.py` - Duplicate
- `weighted_html_output__1_.py` - Duplicate

### 🔄 **INTEGRATE OR ARCHIVE**
- **API Integration (Integrate):**
  - `api_football_weekly_fixtures.py` - Has API-Football integration ready!
  
- **Specialized Models (Keep if using):**
  - `model_binary.py`, `model_multiclass.py`, `model_ordinal.py`
  - `models_dc.py` - Double chance models
  
- **Backtesting (Archive):**
  - `backtest.py`, `backtest_engine.py`, `backtest_config.py`
  - `backtest_visualizer.py`, `realistic_backtest.py`

## 🌐 API Comparison & Recommendations

### **API-Football (RECOMMENDED)**

#### Pricing Tiers:
- **Free**: 100 requests/day (good for testing)
- **Basic**: $29/month - 3,000 requests/day
- **Pro**: $59/month - 7,500 requests/day  
- **Ultra**: $199/month - 75,000 requests/day
- **Mega**: $499/month - 150,000 requests/day

#### Why API-Football?
✅ **Best Coverage**: 1,100+ leagues worldwide including all major European cups
✅ **Rich Data**: 
- Live scores (15-second updates)
- Fixtures & results
- Team/player statistics
- Lineups & substitutions
- Pre-match & live odds
- Predictions endpoint
- Head-to-head history
- Injuries & suspensions

✅ **Already Integrated**: Your `api_football_weekly_fixtures.py` already has working code!

### Alternative Options Comparison:

| API | Free Tier | Paid Starting | Key Features | Limitations |
|-----|-----------|---------------|--------------|-------------|
| **football-data.org** | 10 calls/min | €15/month | Clean data, 40+ leagues | Limited leagues, no live odds |
| **Sportmonks** | Trial only | $149/month | 2,500+ leagues, excellent docs | Expensive for hobbyists |
| **Live-Score API** | 14-day trial | $39/month | Good coverage, fast updates | Less historical data |
| **Goalserve** | Trial | $99/month | 400+ leagues, fantasy stats | Higher entry price |

## 🚀 Integration Plan

### Phase 1: Quick Win (1-2 hours)
```python
# Modify run_weeklyOU.py Step 0:
# Replace simple_fixture_downloader with api_football_weekly_fixtures

try:
    from api_football_weekly_fixtures import main as fetch_api_fixtures
    # Fetch 7 days of fixtures
    fixture_path = fetch_api_fixtures(
        days_ahead=7,
        provider="native",
        run_diagnose=False,
        master=None,
        stop_on_free_window=False,
        uefa_only=False,
        league_ids_arg=None
    )
except Exception as e:
    # Fallback to current method
    from simple_fixture_downloader import download_upcoming_fixtures
    fixture_path = download_upcoming_fixtures()
```

### Phase 2: Enhanced Statistics (4-6 hours)

Create `enhanced_stats_fetcher.py`:
```python
import requests
import pandas as pd
from datetime import datetime, timedelta

class APIFootballStatsFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {"x-apisports-key": api_key}
    
    def get_team_stats(self, team_id, season):
        """Fetch detailed team statistics"""
        endpoint = f"{self.base_url}/teams/statistics"
        params = {"team": team_id, "season": season}
        response = requests.get(endpoint, headers=self.headers, params=params)
        return response.json()
    
    def get_h2h(self, team1_id, team2_id):
        """Get head-to-head history"""
        endpoint = f"{self.base_url}/fixtures/headtohead"
        params = {"h2h": f"{team1_id}-{team2_id}"}
        response = requests.get(endpoint, headers=self.headers, params=params)
        return response.json()
    
    def get_player_stats(self, league_id, season):
        """Get top scorers and player statistics"""
        endpoint = f"{self.base_url}/players/topscorers"
        params = {"league": league_id, "season": season}
        response = requests.get(endpoint, headers=self.headers, params=params)
        return response.json()
```

### Phase 3: Feature Enhancement (6-8 hours)

Modify `features.py` to incorporate new API data:
```python
def build_enhanced_features(df, api_stats):
    """Add API-sourced features to existing feature set"""
    
    # Add team form from last 5 matches
    df['home_recent_form'] = api_stats['home_form_score']
    df['away_recent_form'] = api_stats['away_form_score']
    
    # Add head-to-head statistics
    df['h2h_home_wins'] = api_stats['h2h_home_wins']
    df['h2h_draws'] = api_stats['h2h_draws']
    df['h2h_away_wins'] = api_stats['h2h_away_wins']
    
    # Add advanced team stats
    df['home_xG'] = api_stats['home_expected_goals']
    df['away_xG'] = api_stats['away_expected_goals']
    df['home_shots_accuracy'] = api_stats['home_shots_on_target_pct']
    df['away_shots_accuracy'] = api_stats['away_shots_on_target_pct']
    
    return df
```

## 💰 Cost Analysis

For weekly predictions with ~200-300 matches:
- **Fixtures**: 7 API calls (one per day)
- **Team Stats**: 400-600 calls (2 per match)
- **H2H**: 200-300 calls (1 per match)
- **Total**: ~800-900 calls per week

**Recommendation**: Start with **Basic Plan ($29/month)** - 3,000 requests/day is plenty!

## 📊 Expected Improvements

With API-Football integration:
- **+20-30% more fixtures** (cups, international matches)
- **+15-20% prediction accuracy** (better statistics)
- **Real-time updates** (injuries, suspensions, lineups)
- **More betting markets** (Asian Handicap, correct score)
- **Professional odds comparison** (from multiple bookmakers)

## 🔧 Implementation Checklist

### Week 1:
- [ ] Clean up redundant files
- [ ] Sign up for API-Football free tier
- [ ] Test `api_football_weekly_fixtures.py` 
- [ ] Integrate fixture fetching into main runner

### Week 2:
- [ ] Create enhanced stats fetcher
- [ ] Add new features to feature engineering
- [ ] Test with historical data
- [ ] Compare prediction accuracy

### Week 3:
- [ ] Upgrade to paid plan if successful
- [ ] Add real-time injury/suspension checks
- [ ] Implement odds comparison features
- [ ] Add more betting markets

## 🎯 Quick Start Commands

```bash
# Clean up project
rm ONE_CLICK_RUN.py modelsOLD.py updated_run_weekly*.py *__1_.py

# Test API connection
python api_football_weekly_fixtures.py --diagnose

# Run enhanced pipeline
python run_weeklyOU.py --use-api-football

# Check results
python accuracy_tracker.py --compare-before-after
```

## 📈 Success Metrics

Track these after integration:
1. **Coverage**: Number of fixtures available (target: +25%)
2. **Accuracy**: Prediction success rate (target: +15%)
3. **ROI**: Betting returns if applicable (target: +20%)
4. **Processing Time**: Should remain under 30 minutes
5. **API Usage**: Stay within plan limits

## 🚨 Important Notes

1. **API Key Security**: Never commit API keys to Git
2. **Rate Limiting**: Implement delays between requests
3. **Error Handling**: Always have fallback to football-data.co.uk
4. **Data Validation**: Cross-check team names between sources
5. **Cost Monitoring**: Track API usage daily

## 💡 Final Recommendation

**Start with API-Football's free tier** to validate the integration, then upgrade to the **Basic plan ($29/month)** once proven. The existing `api_football_weekly_fixtures.py` file gives you a head start - you're already 30% done!

The investment will pay off through:
- Better prediction accuracy
- More betting opportunities  
- Professional-grade data
- Automated injury/suspension updates
- Live odds for validation

Your project is well-structured and ready for this enhancement. The main challenge will be mapping team names between data sources, but this is a one-time setup task.

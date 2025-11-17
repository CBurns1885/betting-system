#!/usr/bin/env python3
"""
NFL Backtest Configuration Presets

Provides easy-to-use configuration presets for backtesting.
"""

from datetime import datetime
from backtest import NFLBacktestEngine
from config import log_header


# ============================================================================
# BACKTEST CONFIGURATIONS
# ============================================================================

BACKTEST_CONFIGS = {
    'last_season': {
        'name': 'Last Full Season',
        'start_season': datetime.now().year - 1,
        'end_season': datetime.now().year - 1,
        'weeks': 1,
        'description': 'Test on previous NFL season (weekly)'
    },
    'last_2_seasons': {
        'name': 'Last 2 Seasons',
        'start_season': datetime.now().year - 2,
        'end_season': datetime.now().year - 1,
        'weeks': 1,
        'description': 'Test on last 2 NFL seasons (weekly)'
    },
    'last_3_seasons': {
        'name': 'Last 3 Seasons',
        'start_season': datetime.now().year - 3,
        'end_season': datetime.now().year - 1,
        'weeks': 1,
        'description': 'Long-term validation (3 seasons)'
    },
    '2023_season': {
        'name': '2023 Season',
        'start_season': 2023,
        'end_season': 2023,
        'weeks': 1,
        'description': '2023 NFL season validation'
    },
    '2024_season': {
        'name': '2024 Season',
        'start_season': 2024,
        'end_season': 2024,
        'weeks': 1,
        'description': '2024 NFL season validation'
    },
    'multi_week': {
        'name': 'Multi-Week Blocks',
        'start_season': datetime.now().year - 1,
        'end_season': datetime.now().year - 1,
        'weeks': 4,
        'description': 'Test in 4-week blocks (monthly)'
    },
    'custom': {
        'name': 'Custom Period',
        'start_season': 2023,
        'end_season': 2024,
        'weeks': 1,
        'description': 'User-defined period'
    }
}


# ============================================================================
# INTERACTIVE RUNNER
# ============================================================================

def select_backtest_config():
    """Interactive configuration selection"""
    print("\n🔬 NFL BACKTESTING CONFIGURATION")
    print("="*60)
    print("\nAvailable configurations:")

    configs = list(BACKTEST_CONFIGS.keys())
    for i, key in enumerate(configs, 1):
        config = BACKTEST_CONFIGS[key]
        print(f"\n{i}. {config['name']}")
        print(f"   {config['description']}")
        print(f"   Seasons: {config['start_season']} to {config['end_season']}")
        print(f"   Test window: {config['weeks']} week(s)")

    choice = input(f"\nSelect configuration (1-{len(configs)}, default=1): ").strip() or "1"

    try:
        selected_key = configs[int(choice) - 1]
        return BACKTEST_CONFIGS[selected_key], selected_key
    except:
        print("Invalid choice, using default (Last Season)")
        return BACKTEST_CONFIGS['last_season'], 'last_season'


def run_backtest_with_config(config: dict, config_name: str):
    """Run backtest with selected configuration"""
    log_header(f"Running: {config['name']}")

    # Create engine
    engine = NFLBacktestEngine(
        start_season=config['start_season'],
        end_season=config['end_season'],
        test_window_weeks=config['weeks']
    )

    # Run backtest
    try:
        summary = engine.run_backtest()
        engine.export_detailed_results()

        # Print insights
        print_backtest_insights(summary, config_name)

        return summary

    finally:
        engine.cleanup()


def print_backtest_insights(summary, config_name: str):
    """Print actionable insights from backtest"""
    if summary is None or summary.empty:
        print("⚠️ No results to analyze")
        return

    print("\n" + "="*60)
    print("💡 KEY INSIGHTS")
    print("="*60)

    # Best performing market
    if len(summary) > 0:
        best_market = summary['Accuracy'].idxmax()
        best_acc = summary.loc[best_market, 'Accuracy']
        best_roi = summary.loc[best_market, 'ROI']

        print(f"\n🏆 Best Market: {best_market}")
        print(f"   • Accuracy: {best_acc:.1%}")
        print(f"   • ROI: {best_roi:+.1f}%")
        print(f"   • Games: {summary.loc[best_market, 'Total_Games']:.0f}")

        # Worst performing
        if len(summary) > 1:
            worst_market = summary['Accuracy'].idxmin()
            worst_acc = summary.loc[worst_market, 'Accuracy']

            print(f"\n⚠️ Weakest Market: {worst_market}")
            print(f"   • Accuracy: {worst_acc:.1%}")

    # Overall profitability
    total_profit = summary['Profit_Units'].sum()
    total_games = summary['Total_Games'].sum()
    overall_roi = (total_profit / total_games * 100) if total_games > 0 else 0

    print(f"\n💰 Overall Performance:")
    print(f"   • Total Profit/Loss: {total_profit:+.1f} units")
    print(f"   • Overall ROI: {overall_roi:+.1f}%")
    print(f"   • Status: {'PROFITABLE ✅' if total_profit > 0 else 'LOSING ❌'}")

    # Recommendations
    print(f"\n📋 Recommendations:")

    profitable_markets = summary[summary['ROI'] > 0].index.tolist()
    if profitable_markets:
        print(f"   ✅ Focus on: {', '.join(profitable_markets)}")

    unprofitable_markets = summary[summary['ROI'] < 0].index.tolist()
    if unprofitable_markets:
        print(f"   ❌ Avoid/improve: {', '.join(unprofitable_markets)}")

    # Accuracy thresholds
    high_accuracy = summary[summary['Accuracy'] > 0.55].index.tolist()
    if high_accuracy:
        print(f"   🎯 High accuracy markets: {', '.join(high_accuracy)}")

    print("\n" + "="*60)


# ============================================================================
# COMPARISON RUNNER
# ============================================================================

def compare_multiple_periods():
    """Compare backtest performance across multiple periods"""
    log_header("Multi-Period Comparison")

    periods = ['last_season', 'last_2_seasons', 'last_3_seasons']
    all_summaries = {}

    for period_key in periods:
        config = BACKTEST_CONFIGS[period_key]
        print(f"\n▶ Testing: {config['name']}")

        try:
            summary = run_backtest_with_config(config, period_key)
            all_summaries[period_key] = summary
        except Exception as e:
            print(f"   ❌ Failed: {e}")

    # Generate comparison report
    print("\n" + "="*60)
    print("📈 PERIOD COMPARISON")
    print("="*60)

    for period_key, summary in all_summaries.items():
        config = BACKTEST_CONFIGS[period_key]
        print(f"\n{config['name']}:")

        if summary is not None and not summary.empty:
            avg_acc = summary['Accuracy'].mean()
            total_roi = summary['ROI'].mean()
            print(f"   • Avg Accuracy: {avg_acc:.1%}")
            print(f"   • Avg ROI: {total_roi:+.1f}%")
        else:
            print("   • No data")


# ============================================================================
# MAIN INTERFACE
# ============================================================================

def main():
    """Main backtest runner"""
    print("="*60)
    print("🏈 NFL PREDICTION BACKTESTING SYSTEM")
    print("="*60)

    print("\nOptions:")
    print("1. Single backtest (choose period)")
    print("2. Compare multiple periods")
    print("3. Custom season range")

    choice = input("\nSelect option (1-3, default=1): ").strip() or "1"

    if choice == "1":
        config, config_name = select_backtest_config()
        run_backtest_with_config(config, config_name)

    elif choice == "2":
        compare_multiple_periods()

    elif choice == "3":
        start = input("Start season (e.g., 2022): ")
        end = input("End season (e.g., 2024): ")
        weeks = input("Window weeks (default=1): ").strip() or "1"

        custom_config = {
            'name': 'Custom Period',
            'start_season': int(start),
            'end_season': int(end),
            'weeks': int(weeks),
            'description': f'Seasons {start} to {end}'
        }

        run_backtest_with_config(custom_config, 'custom')

    print("\n✅ Backtesting complete!")
    print("📂 Results saved in outputs/")
    print("   • backtest_summary.csv - Overall stats by market")
    print("   • backtest_predictions.csv - All predictions")


if __name__ == "__main__":
    main()

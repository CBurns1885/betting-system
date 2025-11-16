#!/usr/bin/env python3
"""
smart_tuning_config.py
Intelligent hyperparameter tuning configuration based on market complexity
"""

import os
from typing import Dict, Tuple

# Market complexity categories
BINARY_MARKETS = {
    "y_BTTS",           # Both Teams To Score (Y/N)
    "y_OU_0_5",         # Over/Under 0.5 goals
    "y_OU_1_5",         # Over/Under 1.5 goals
    "y_OU_2_5",         # Over/Under 2.5 goals
    "y_OU_3_5",         # Over/Under 3.5 goals
    "y_OU_4_5",         # Over/Under 4.5 goals
}

TERNARY_MARKETS = {
    "y_1X2",            # Home/Draw/Away (3 classes)
    "y_DC",             # Double Chance (3 combinations)
}

MULTICLASS_MARKETS = {
    "y_CS",             # Correct Score (20+ classes)
    "y_HT_FT",          # Half Time / Full Time (9 classes)
    "y_BOTH_HALVES",    # Both Halves Result (4 classes)
    "y_TEAM_SCORE",     # Team to Score First (3 classes)
}

ORDINAL_MARKETS = {
    "y_AH_0_0",         # Asian Handicap 0.0
    "y_AH_0_5",         # Asian Handicap 0.5
    "y_AH_1_0",         # Asian Handicap 1.0
    "y_AH_1_5",         # Asian Handicap 1.5
    "y_AH_2_0",         # Asian Handicap 2.0
    "y_EH",             # European Handicap
}

def get_market_complexity(market_name: str) -> str:
    """
    Determine market complexity category

    Args:
        market_name: Market identifier (e.g., "y_1X2", "y_BTTS")

    Returns:
        "binary", "ternary", "multiclass", "ordinal", or "unknown"
    """
    # Check exact matches first
    if market_name in BINARY_MARKETS:
        return "binary"
    elif market_name in TERNARY_MARKETS:
        return "ternary"
    elif market_name in MULTICLASS_MARKETS:
        return "multiclass"
    elif market_name in ORDINAL_MARKETS:
        return "ordinal"

    # Check prefixes for dynamic markets
    if market_name.startswith("y_OU_"):
        return "binary"
    elif market_name.startswith("y_AH_"):
        return "ordinal"
    elif market_name.startswith("y_CS_"):
        return "multiclass"

    return "unknown"

def get_optimal_trials(market_name: str, num_classes: int = None) -> int:
    """
    Get optimal number of Optuna trials for a market

    Strategy:
    - Binary (2 classes): 10-15 trials (simple problem)
    - Ternary (3 classes): 15 trials (moderately simple)
    - Ordinal (ordered): 20 trials (medium complexity)
    - Multiclass (4-9 classes): 25 trials (complex)
    - Multiclass (10+ classes): 30 trials (very complex)

    Args:
        market_name: Market identifier
        num_classes: Number of classes (optional, auto-detect if not provided)

    Returns:
        Optimal number of trials
    """
    complexity = get_market_complexity(market_name)

    # Read from environment variables
    trials_binary = int(os.environ.get("OPTUNA_TRIALS_BINARY", "15"))
    trials_multiclass = int(os.environ.get("OPTUNA_TRIALS_MULTICLASS", "30"))
    trials_ordinal = int(os.environ.get("OPTUNA_TRIALS_ORDINAL", "20"))
    trials_fallback = int(os.environ.get("OPTUNA_TRIALS_FALLBACK", "15"))

    if complexity == "binary":
        return 10  # Very simple, 2 classes
    elif complexity == "ternary":
        return trials_binary  # 3 classes, use binary setting
    elif complexity == "ordinal":
        return trials_ordinal  # 20 trials for ordered outcomes
    elif complexity == "multiclass":
        # Adjust based on number of classes if provided
        if num_classes is not None:
            if num_classes <= 4:
                return 20  # Small multiclass
            elif num_classes <= 9:
                return 25  # Medium multiclass
            else:
                return trials_multiclass  # 30 for complex (10+ classes)
        return trials_multiclass  # Default to 30 if unknown
    else:
        return trials_fallback  # 15 for unknown markets

def get_optimal_estimators(market_name: str, num_classes: int = None) -> Tuple[int, int]:
    """
    Get optimal estimator range for a market

    Returns:
        (min_estimators, max_estimators) tuple
    """
    complexity = get_market_complexity(market_name)

    base_estimators = int(os.environ.get("N_ESTIMATORS", "400"))

    if complexity in ["binary", "ternary"]:
        # Simpler markets need fewer estimators
        return (200, 400)
    elif complexity == "ordinal":
        # Medium complexity
        return (250, 450)
    elif complexity == "multiclass":
        # Complex markets benefit from more estimators
        if num_classes and num_classes >= 10:
            return (300, 500)
        return (250, 450)
    else:
        # Unknown markets use balanced range
        return (200, 400)

def get_optimal_depth(market_name: str, num_classes: int = None) -> Tuple[int, int]:
    """
    Get optimal tree depth range for a market

    Returns:
        (min_depth, max_depth) tuple
    """
    complexity = get_market_complexity(market_name)

    max_depth_config = int(os.environ.get("MAX_DEPTH", "12"))

    if complexity in ["binary", "ternary"]:
        # Shallower trees for simple problems
        return (6, 10)
    elif complexity == "ordinal":
        # Medium depth
        return (8, 12)
    elif complexity == "multiclass":
        # Deeper trees for complex problems
        if num_classes and num_classes >= 10:
            return (10, max_depth_config)
        return (8, 12)
    else:
        # Balanced for unknown
        return (6, 10)

def print_tuning_summary():
    """Print summary of tuning configuration"""
    print("\n" + "="*60)
    print("SMART MARKET-SPECIFIC TUNING CONFIGURATION")
    print("="*60)

    # Binary markets
    print("\n📊 Binary Markets (2 classes):")
    print(f"   Markets: {', '.join(sorted(BINARY_MARKETS))}")
    print(f"   Trials: 10")
    print(f"   Estimators: 200-400")
    print(f"   Depth: 6-10")
    print(f"   Rationale: Simple problem, fewer trials needed")

    # Ternary markets
    print("\n📊 Ternary Markets (3 classes):")
    print(f"   Markets: {', '.join(sorted(TERNARY_MARKETS))}")
    print(f"   Trials: {os.environ.get('OPTUNA_TRIALS_BINARY', '15')}")
    print(f"   Estimators: 200-400")
    print(f"   Depth: 6-10")
    print(f"   Rationale: Moderately simple, use binary settings")

    # Ordinal markets
    print("\n📊 Ordinal Markets (ordered outcomes):")
    print(f"   Markets: {', '.join(sorted(ORDINAL_MARKETS))}")
    print(f"   Trials: {os.environ.get('OPTUNA_TRIALS_ORDINAL', '20')}")
    print(f"   Estimators: 250-450")
    print(f"   Depth: 8-12")
    print(f"   Rationale: Medium complexity, ordered relationships")

    # Multiclass markets
    print("\n📊 Multiclass Markets (4+ classes):")
    print(f"   Markets: {', '.join(sorted(MULTICLASS_MARKETS))}")
    print(f"   Trials: 20-30 (based on num_classes)")
    print(f"   Estimators: 250-500")
    print(f"   Depth: 8-12")
    print(f"   Rationale: Complex problem, more exploration needed")

    print("\n💡 Total Trials Saved:")
    print(f"   Old system: 50 trials × 15 markets = 750 trials")
    print(f"   New system: ~15-20 avg × 15 markets = ~270 trials")
    print(f"   ⚡ 64% reduction in training time!")

    print("="*60 + "\n")

def get_market_tuning_config(market_name: str, num_classes: int = None) -> Dict:
    """
    Get complete tuning configuration for a market

    Args:
        market_name: Market identifier
        num_classes: Number of classes (optional)

    Returns:
        Dictionary with tuning configuration
    """
    complexity = get_market_complexity(market_name)
    trials = get_optimal_trials(market_name, num_classes)
    min_est, max_est = get_optimal_estimators(market_name, num_classes)
    min_depth, max_depth = get_optimal_depth(market_name, num_classes)

    return {
        "market_name": market_name,
        "complexity": complexity,
        "num_classes": num_classes,
        "n_trials": trials,
        "n_estimators_range": (min_est, max_est),
        "max_depth_range": (min_depth, max_depth),
        "min_samples_split": int(os.environ.get("MIN_SAMPLES_SPLIT", "5")),
        "learning_rate": float(os.environ.get("LEARNING_RATE", "0.02")),
    }

if __name__ == "__main__":
    print_tuning_summary()

    # Test examples
    print("\n" + "="*60)
    print("EXAMPLE CONFIGURATIONS")
    print("="*60)

    test_markets = [
        ("y_1X2", 3),
        ("y_BTTS", 2),
        ("y_OU_2_5", 2),
        ("y_CS", 25),
        ("y_AH_0_0", 3),
        ("y_HT_FT", 9),
    ]

    for market, classes in test_markets:
        config = get_market_tuning_config(market, classes)
        print(f"\n{market} ({classes} classes):")
        print(f"  Complexity: {config['complexity']}")
        print(f"  Trials: {config['n_trials']}")
        print(f"  Estimators: {config['n_estimators_range'][0]}-{config['n_estimators_range'][1]}")
        print(f"  Depth: {config['max_depth_range'][0]}-{config['max_depth_range'][1]}")

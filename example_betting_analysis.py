"""Advanced example: Analyzing betting data with Claude"""

from src.claude_client import ClaudeClient


def main():
    """Example of analyzing structured betting data"""

    # Initialize the client
    client = ClaudeClient()

    # Example betting data structure
    betting_data = {
        "match": "Team A vs Team B",
        "sport": "Football",
        "date": "2025-11-20",
        "odds": {
            "Team A": 1.75,
            "Draw": 3.50,
            "Team B": 4.20
        },
        "statistics": {
            "Team A": {
                "wins_last_5": 4,
                "losses_last_5": 1,
                "goals_scored_avg": 2.1,
                "goals_conceded_avg": 0.8
            },
            "Team B": {
                "wins_last_5": 2,
                "losses_last_5": 2,
                "goals_scored_avg": 1.3,
                "goals_conceded_avg": 1.5
            }
        },
        "head_to_head": [
            "Team A won 2-0",
            "Team A won 1-0",
            "Draw 1-1",
            "Team A won 3-1",
            "Team B won 2-1"
        ],
        "additional_info": {
            "Team A home_advantage": True,
            "Team B injuries": 2,
            "weather": "Clear"
        }
    }

    # Perform different types of analysis
    print("=== GENERAL ANALYSIS ===")
    general_analysis = client.analyze_betting_data(
        data=betting_data,
        analysis_type="general"
    )
    print(general_analysis)
    print("\n" + "=" * 70 + "\n")

    print("=== RISK ANALYSIS ===")
    risk_analysis = client.analyze_betting_data(
        data=betting_data,
        analysis_type="risk"
    )
    print(risk_analysis)
    print("\n" + "=" * 70 + "\n")

    print("=== VALUE ANALYSIS ===")
    value_analysis = client.analyze_betting_data(
        data=betting_data,
        analysis_type="value"
    )
    print(value_analysis)


if __name__ == "__main__":
    main()

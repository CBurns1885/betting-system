"""Basic example of using the Claude API client"""

from src.claude_client import ClaudeClient


def main():
    """Basic example of Claude API usage"""

    # Initialize the client (reads API key from .env file)
    client = ClaudeClient()

    # Simple analysis example
    print("=== Simple Analysis ===")
    response = client.analyze(
        prompt="What are the key factors to consider when analyzing sports betting odds?"
    )
    print(response)
    print("\n" + "=" * 50 + "\n")

    # Custom system prompt example
    print("=== Custom System Prompt ===")
    response = client.analyze(
        prompt="Should I bet on a favorite with -200 odds or an underdog with +300 odds?",
        system_prompt="You are a conservative betting advisor focused on risk management."
    )
    print(response)


if __name__ == "__main__":
    main()

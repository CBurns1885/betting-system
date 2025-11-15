# Betting System - Claude API Integration

A Python template for integrating Claude API into betting analysis systems. This provides a clean, reusable foundation for sending betting data to Claude for AI-powered analysis.

## Features

- Simple Claude API client wrapper
- Environment-based configuration
- Structured betting data analysis
- Multiple analysis types (general, risk, value, statistical)
- Easy to extend and customize
- Type hints for better IDE support

## Prerequisites

- Python 3.8 or higher
- Anthropic API key ([Get one here](https://console.anthropic.com/))

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd betting-system
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables:
```bash
cp .env.example .env
```

5. Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_actual_api_key_here
```

## Quick Start

### Basic Usage

```python
from src.claude_client import ClaudeClient

# Initialize the client
client = ClaudeClient()

# Send a simple prompt
response = client.analyze(
    prompt="What factors should I consider in sports betting?"
)
print(response)
```

### Analyzing Betting Data

```python
from src.claude_client import ClaudeClient

client = ClaudeClient()

# Structure your betting data
betting_data = {
    "match": "Team A vs Team B",
    "odds": {
        "Team A": 1.75,
        "Team B": 4.20
    },
    "statistics": {
        "Team A": {
            "wins_last_5": 4,
            "goals_scored_avg": 2.1
        }
    }
}

# Get analysis
analysis = client.analyze_betting_data(
    data=betting_data,
    analysis_type="value"  # Options: general, risk, value, statistical
)
print(analysis)
```

## Project Structure

```
betting-system/
├── src/
│   ├── __init__.py
│   └── claude_client.py      # Main Claude API client
├── example_basic.py           # Basic usage examples
├── example_betting_analysis.py # Advanced betting analysis
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore
└── README.md
```

## API Client Reference

### ClaudeClient

Main class for interacting with Claude API.

#### Initialization

```python
client = ClaudeClient(
    api_key="optional_key",           # Defaults to ANTHROPIC_API_KEY env var
    model="claude-3-5-sonnet-20241022",  # Defaults to CLAUDE_MODEL env var
    max_tokens=4096                   # Defaults to MAX_TOKENS env var
)
```

#### Methods

**analyze(prompt, system_prompt=None, temperature=1.0, **kwargs)**

Send a prompt to Claude for analysis.

- `prompt` (str): The main question or prompt
- `system_prompt` (str, optional): System prompt to set context
- `temperature` (float): Sampling temperature (0-1)
- Returns: Claude's response as string

**analyze_betting_data(data, analysis_type="general")**

Analyze structured betting data.

- `data` (dict): Dictionary containing betting information
- `analysis_type` (str): Type of analysis - "general", "risk", "value", or "statistical"
- Returns: Analysis as string

## Examples

Run the included example scripts:

```bash
# Basic examples
python example_basic.py

# Betting analysis examples
python example_betting_analysis.py
```

## Configuration

Configure the client using environment variables in `.env`:

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional
CLAUDE_MODEL=claude-3-5-sonnet-20241022  # Model to use
MAX_TOKENS=4096                           # Max response tokens
```

## Extending for Your Project

This template is designed to be easily customized:

1. **Add custom analysis types**: Modify `analyze_betting_data()` system prompts
2. **Add new methods**: Create specialized methods for your betting domain
3. **Custom data formatting**: Extend `_format_betting_data()` for your data structure
4. **Error handling**: Add retry logic, logging, or custom error handling
5. **Caching**: Add response caching to reduce API calls

Example extension:

```python
class MyCustomClient(ClaudeClient):
    def analyze_live_odds(self, odds_data):
        """Custom method for live odds analysis"""
        prompt = f"Analyze these live odds: {odds_data}"
        return self.analyze(
            prompt,
            system_prompt="You are a live betting expert."
        )
```

## Best Practices

1. **API Key Security**: Never commit `.env` to version control
2. **Rate Limiting**: Be mindful of API rate limits
3. **Error Handling**: Wrap API calls in try-except blocks for production use
4. **Cost Management**: Monitor token usage via Anthropic console
5. **Prompt Engineering**: Craft clear, specific prompts for better results

## Available Claude Models

- `claude-3-5-sonnet-20241022` - Best balance of performance and cost (recommended)
- `claude-3-5-haiku-20241022` - Fastest and most cost-effective
- `claude-3-opus-20240229` - Most capable model

## Troubleshooting

**Error: API key must be provided**
- Ensure `.env` file exists and contains `ANTHROPIC_API_KEY`
- Check that `python-dotenv` is installed

**Error: Module not found**
- Ensure you're running from the project root directory
- Check virtual environment is activated

**Slow responses**
- Consider using a faster model (haiku)
- Reduce `max_tokens` setting
- Simplify prompts

## Resources

- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Claude API Reference](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)

## License

MIT License - feel free to use this template for your projects.

## Contributing

This is a template project. Fork it and customize for your needs!

---

**Note**: This is a template designed for easy reuse. Customize the client, add your domain logic, and build your betting analysis system!

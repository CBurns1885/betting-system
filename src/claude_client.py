"""Claude API Client for Betting Analysis"""

import os
from typing import Optional, Dict, Any
from anthropic import Anthropic
from dotenv import load_dotenv


class ClaudeClient:
    """
    A simple client for interacting with the Claude API.

    This client provides methods for sending data to Claude for analysis
    and receiving structured responses.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize the Claude API client.

        Args:
            api_key: Anthropic API key. If not provided, reads from ANTHROPIC_API_KEY env var
            model: Claude model to use. Defaults to claude-3-5-sonnet-20241022
            max_tokens: Maximum tokens in response. Defaults to 4096
        """
        # Load environment variables
        load_dotenv()

        # Set API key
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set in ANTHROPIC_API_KEY environment variable"
            )

        # Configure client
        self.client = Anthropic(api_key=self.api_key)
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.max_tokens = max_tokens or int(os.getenv("MAX_TOKENS", "4096"))

    def analyze(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 1.0,
        **kwargs
    ) -> str:
        """
        Send a prompt to Claude for analysis.

        Args:
            prompt: The main prompt/question to send to Claude
            system_prompt: Optional system prompt to set context/behavior
            temperature: Sampling temperature (0-1). Higher = more random
            **kwargs: Additional arguments to pass to the API

        Returns:
            Claude's response as a string
        """
        message_params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        # Add system prompt if provided
        if system_prompt:
            message_params["system"] = system_prompt

        # Merge any additional kwargs
        message_params.update(kwargs)

        # Make API call
        response = self.client.messages.create(**message_params)

        # Extract text from response
        return response.content[0].text

    def analyze_betting_data(
        self,
        data: Dict[str, Any],
        analysis_type: str = "general"
    ) -> str:
        """
        Analyze betting-related data using Claude.

        Args:
            data: Dictionary containing betting data (odds, teams, statistics, etc.)
            analysis_type: Type of analysis to perform (general, risk, value, etc.)

        Returns:
            Claude's analysis as a string
        """
        # Format the data for Claude
        data_str = self._format_betting_data(data)

        # Create system prompt based on analysis type
        system_prompts = {
            "general": "You are a betting analyst. Analyze the provided data and give insights.",
            "risk": "You are a risk analyst. Evaluate the risk factors in the betting data provided.",
            "value": "You are a value betting expert. Identify value opportunities in the data.",
            "statistical": "You are a statistical analyst. Perform statistical analysis on the betting data."
        }

        system_prompt = system_prompts.get(
            analysis_type,
            system_prompts["general"]
        )

        # Create the analysis prompt
        prompt = f"""Please analyze the following betting data:

{data_str}

Provide a comprehensive analysis including:
1. Key observations
2. Potential opportunities or risks
3. Recommendations (if applicable)
"""

        return self.analyze(prompt, system_prompt=system_prompt)

    def _format_betting_data(self, data: Dict[str, Any]) -> str:
        """
        Format betting data dictionary into a readable string.

        Args:
            data: Dictionary containing betting data

        Returns:
            Formatted string representation of the data
        """
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  {sub_key}: {sub_value}")
            elif isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")

        return "\n".join(lines)

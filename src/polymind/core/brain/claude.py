"""Claude API client for AI-powered trading decisions."""

import json
import re
from typing import Any

import anthropic

from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision

SYSTEM_PROMPT = """\
You are a trading assistant that evaluates copy trade signals.

Your goal: COPY PROFITABLE TRADERS while managing risk.

WALLET PERFORMANCE SCORING (use this to determine trust level):
- ELITE (>20 trades, >60% win rate, >5% ROI): Trust level 90% - copy up to 80% size
- PROVEN (>10 trades, >55% win rate, >0% ROI): Trust level 70% - copy up to 60% size
- MODERATE (5-10 trades, >50% win rate): Trust level 50% - copy up to 40% size
- NEW (1-5 trades): Trust level 30% - copy up to 25% size to test
- UNPROVEN (0 trades): Trust level 20% - copy 10-15% size to discover

MARKET CONDITIONS:
- Liquidity >$5000: Good - no adjustment needed
- Liquidity $1000-$5000: Reduce size by 25%
- Liquidity <$1000: REJECT - too risky to enter/exit
- Spread >5%: REJECT - too expensive

RISK RULES:
- Never exceed remaining daily loss budget
- Scale position size by wallet trust level
- Higher spread = lower confidence

Calculate final size as: signal_size * trust_level * liquidity_factor

Respond with ONLY this JSON (no markdown, no extra text):
{
    "execute": boolean,
    "size": number,
    "confidence": number,
    "urgency": "high" | "normal" | "low",
    "reasoning": string
}"""


class ClaudeClient:
    """Client for Claude API to evaluate trading decisions.

    Uses Claude to analyze trade signals and make intelligent decisions
    about whether to execute trades based on wallet performance,
    market conditions, and risk state.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 512,
    ) -> None:
        """Initialize the Claude client.

        Args:
            api_key: Anthropic API key for authentication
            model: Claude model to use (default: claude-sonnet-4-20250514)
            max_tokens: Maximum tokens in response (default: 512)
        """
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def _build_prompt(self, context: DecisionContext) -> str:
        """Build the user prompt from decision context.

        Formats the context data into a structured prompt for Claude
        to evaluate and make a trading decision.

        Args:
            context: DecisionContext with all relevant trading data

        Returns:
            Formatted prompt string for Claude
        """
        context_dict = context.to_dict()

        prompt = f"""Evaluate this trade signal and decide whether to execute:

SIGNAL:
- Wallet: {context_dict['signal']['wallet']}
- Market: {context_dict['signal']['market_id']}
- Side: {context_dict['signal']['side']}
- Size: ${context_dict['signal']['size']:.2f}
- Price: {context_dict['signal']['price']:.4f}

WALLET PERFORMANCE:
- Win Rate: {context_dict['wallet_metrics']['win_rate']:.1%}
- Avg ROI: {context_dict['wallet_metrics']['avg_roi']:.1%}
- Total Trades: {context_dict['wallet_metrics']['total_trades']}
- Recent Performance: {context_dict['wallet_metrics']['recent_performance']:.1%}

MARKET CONDITIONS:
- Liquidity: ${context_dict['market_data']['liquidity']:,.2f}
- Spread: {context_dict['market_data']['spread']:.2%}

RISK STATE:
- Daily P&L: ${context_dict['risk_state']['daily_pnl']:,.2f}
- Open Exposure: ${context_dict['risk_state']['open_exposure']:,.2f}
- Max Daily Loss: ${context_dict['risk_state']['max_daily_loss']:,.2f}
- Remaining Budget: ${
    context_dict['risk_state']['max_daily_loss']
    + context_dict['risk_state']['daily_pnl']:,.2f}

Provide your decision as JSON."""

        return prompt

    async def evaluate(self, context: DecisionContext) -> AIDecision:
        """Evaluate a trade signal using Claude.

        Sends the decision context to Claude for analysis and returns
        the AI's decision on whether to execute the trade.

        Args:
            context: DecisionContext containing all relevant data

        Returns:
            AIDecision with execute decision, sizing, and reasoning
        """
        prompt = self._build_prompt(context)

        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text content from response
            response_text = message.content[0].text

            # Parse JSON response
            decision_data: dict[str, Any] = json.loads(response_text)
            return AIDecision.from_dict(decision_data)

        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            extracted = self._extract_json(response_text)
            if extracted:
                try:
                    decision_data = json.loads(extracted)
                    return AIDecision.from_dict(decision_data)
                except json.JSONDecodeError:
                    pass
            return AIDecision.reject("Failed to parse AI response as JSON")

        except Exception as e:
            return AIDecision.reject(f"API error: {e!s}")

    def _extract_json(self, text: str) -> str | None:
        """Extract JSON from markdown code blocks or raw text.

        Args:
            text: Raw response text that may contain JSON

        Returns:
            Extracted JSON string or None if not found
        """
        # Try to find JSON in code blocks
        code_block_pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
        match = re.search(code_block_pattern, text)
        if match:
            return match.group(1)

        # Try to find raw JSON object
        json_pattern = r"\{[\s\S]*?\}"
        match = re.search(json_pattern, text)
        if match:
            return match.group(0)

        return None

"""Claude API client for AI-powered trading decisions."""

import json
from typing import Any

import anthropic

from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision

SYSTEM_PROMPT = """\
You are a conservative trading assistant that evaluates trade signals \
and decides whether to execute them.

Your primary goal is to PROTECT CAPITAL while seeking profitable opportunities.

When evaluating a trade signal, consider:
1. Wallet Performance: Higher win rate and ROI indicate more reliable signals
2. Market Liquidity: Ensure sufficient liquidity to enter/exit positions
3. Risk Exposure: Current P&L and open exposure vs. max allowed loss
4. Signal Quality: Size, price, and side relative to market conditions

Decision Guidelines:
- Be CONSERVATIVE - when in doubt, reject the trade
- Never risk more than the remaining daily loss budget
- Prefer smaller position sizes for unproven wallets
- Higher confidence requires stronger supporting data
- Set urgency based on how time-sensitive the opportunity is

You MUST respond with a valid JSON object containing exactly these fields:
{
    "execute": boolean,      // true to execute, false to reject
    "size": number,          // position size (0 if rejecting)
    "confidence": number,    // 0.0 to 1.0 confidence level
    "urgency": string,       // "high", "normal", or "low"
    "reasoning": string      // brief explanation of your decision
}

Respond ONLY with the JSON object, no additional text."""


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
            return AIDecision.reject("Failed to parse AI response as JSON")

        except Exception as e:
            return AIDecision.reject(f"API error: {e!s}")

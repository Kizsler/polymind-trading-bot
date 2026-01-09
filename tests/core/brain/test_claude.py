"""Tests for Claude API client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymind.core.brain.claude import SYSTEM_PROMPT, ClaudeClient
from polymind.core.brain.context import DecisionContext
from polymind.core.brain.decision import AIDecision, Urgency


class TestClaudeClient:
    """Tests for ClaudeClient class."""

    @pytest.fixture
    def sample_context(self):
        """Create sample decision context for testing."""
        return DecisionContext(
            # Signal data
            signal_wallet="0x1234567890abcdef1234567890abcdef12345678",
            signal_market_id="btc-50k-friday",
            signal_side="YES",
            signal_size=100.0,
            signal_price=0.65,
            # Wallet performance
            wallet_win_rate=0.72,
            wallet_avg_roi=0.15,
            wallet_total_trades=50,
            wallet_recent_performance=0.08,
            # Market conditions
            market_liquidity=50000.0,
            market_spread=0.02,
            # Risk state
            risk_daily_pnl=-50.0,
            risk_open_exposure=1000.0,
            risk_max_daily_loss=500.0,
        )

    def test_client_creates_prompt(self, sample_context):
        """Verify prompt contains all context data."""
        client = ClaudeClient(api_key="test-key")

        prompt = client._build_prompt(sample_context)

        # Verify signal data is in prompt
        assert "0x1234567890abcdef1234567890abcdef12345678" in prompt
        assert "btc-50k-friday" in prompt
        assert "YES" in prompt
        assert "$100.00" in prompt
        assert "0.6500" in prompt

        # Verify wallet metrics are in prompt
        assert "72.0%" in prompt  # win_rate
        assert "15.0%" in prompt  # avg_roi
        assert "50" in prompt  # total_trades
        assert "8.0%" in prompt  # recent_performance

        # Verify market data is in prompt
        assert "$50,000.00" in prompt  # liquidity
        assert "2.00%" in prompt  # spread

        # Verify risk state is in prompt
        assert "$-50.00" in prompt  # daily_pnl (formatted with $ before sign)
        assert "$1,000.00" in prompt  # open_exposure
        assert "$500.00" in prompt  # max_daily_loss
        assert "$450.00" in prompt  # remaining budget (500 + (-50))

    @pytest.mark.asyncio
    async def test_client_evaluate_returns_decision(self, sample_context):
        """Mock API response and verify AIDecision is returned."""
        mock_response_data = {
            "execute": True,
            "size": 75.0,
            "confidence": 0.85,
            "urgency": "high",
            "reasoning": "Strong signal from high-performing wallet",
        }

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(mock_response_data))]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_message)
            mock_anthropic.return_value = mock_client

            client = ClaudeClient(api_key="test-key")
            client._client = mock_client

            decision = await client.evaluate(sample_context)

        assert isinstance(decision, AIDecision)
        assert decision.execute is True
        assert decision.size == 75.0
        assert decision.confidence == 0.85
        assert decision.urgency == Urgency.HIGH
        assert decision.reasoning == "Strong signal from high-performing wallet"

    @pytest.mark.asyncio
    async def test_client_handles_api_error(self, sample_context):
        """Verify rejection is returned on API exception."""
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(
                side_effect=Exception("API rate limit exceeded")
            )
            mock_anthropic.return_value = mock_client

            client = ClaudeClient(api_key="test-key")
            client._client = mock_client

            decision = await client.evaluate(sample_context)

        assert isinstance(decision, AIDecision)
        assert decision.execute is False
        assert decision.size == 0.0
        assert decision.confidence == 0.0
        assert decision.urgency == Urgency.NORMAL
        assert "API error" in decision.reasoning
        assert "API rate limit exceeded" in decision.reasoning

    @pytest.mark.asyncio
    async def test_client_handles_json_decode_error(self, sample_context):
        """Verify rejection is returned on invalid JSON response."""
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Not valid JSON response")]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_message)
            mock_anthropic.return_value = mock_client

            client = ClaudeClient(api_key="test-key")
            client._client = mock_client

            decision = await client.evaluate(sample_context)

        assert isinstance(decision, AIDecision)
        assert decision.execute is False
        assert decision.size == 0.0
        assert decision.confidence == 0.0
        assert "Failed to parse AI response as JSON" in decision.reasoning

    @pytest.mark.asyncio
    async def test_client_calls_api_with_correct_params(self, sample_context):
        """Verify API is called with correct model and parameters."""
        mock_response_data = {
            "execute": False,
            "size": 0,
            "confidence": 0.3,
            "urgency": "low",
            "reasoning": "Test response",
        }

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(mock_response_data))]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_message)
            mock_anthropic.return_value = mock_client

            client = ClaudeClient(
                api_key="test-key",
                model="claude-sonnet-4-20250514",
                max_tokens=256,
            )
            client._client = mock_client

            await client.evaluate(sample_context)

        # Verify API was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs

        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_kwargs["max_tokens"] == 256
        assert call_kwargs["system"] == SYSTEM_PROMPT
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"

    def test_client_default_parameters(self):
        """Verify client uses default model and max_tokens."""
        with patch("anthropic.AsyncAnthropic"):
            client = ClaudeClient(api_key="test-key")

            assert client._model == "claude-sonnet-4-20250514"
            assert client._max_tokens == 512

    def test_client_custom_parameters(self):
        """Verify client accepts custom model and max_tokens."""
        with patch("anthropic.AsyncAnthropic"):
            client = ClaudeClient(
                api_key="test-key",
                model="claude-opus-4-20250514",
                max_tokens=1024,
            )

            assert client._model == "claude-opus-4-20250514"
            assert client._max_tokens == 1024

    def test_system_prompt_contains_key_instructions(self):
        """Verify system prompt has essential trading instructions."""
        # Check for conservative approach
        assert "PROTECT CAPITAL" in SYSTEM_PROMPT
        assert "CONSERVATIVE" in SYSTEM_PROMPT

        # Check for required response format
        assert '"execute"' in SYSTEM_PROMPT
        assert '"size"' in SYSTEM_PROMPT
        assert '"confidence"' in SYSTEM_PROMPT
        assert '"urgency"' in SYSTEM_PROMPT
        assert '"reasoning"' in SYSTEM_PROMPT

        # Check for JSON response requirement
        assert "JSON" in SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_client_evaluate_rejection_decision(self, sample_context):
        """Verify client handles rejection response correctly."""
        mock_response_data = {
            "execute": False,
            "size": 0,
            "confidence": 0.2,
            "urgency": "normal",
            "reasoning": "Wallet has insufficient track record",
        }

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(mock_response_data))]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_message)
            mock_anthropic.return_value = mock_client

            client = ClaudeClient(api_key="test-key")
            client._client = mock_client

            decision = await client.evaluate(sample_context)

        assert decision.execute is False
        assert decision.size == 0
        assert decision.confidence == 0.2
        assert decision.urgency == Urgency.NORMAL
        assert decision.reasoning == "Wallet has insufficient track record"

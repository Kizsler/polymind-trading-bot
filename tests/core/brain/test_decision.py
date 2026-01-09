"""Tests for AI decision response model."""

from polymind.core.brain.decision import AIDecision, Urgency


class TestUrgency:
    """Tests for Urgency enum."""

    def test_urgency_values(self):
        """Verify Urgency enum has correct values."""
        assert Urgency.HIGH.value == "high"
        assert Urgency.NORMAL.value == "normal"
        assert Urgency.LOW.value == "low"

    def test_urgency_from_string_high(self):
        """Parse 'high' string to HIGH urgency."""
        assert Urgency.from_string("high") == Urgency.HIGH

    def test_urgency_from_string_normal(self):
        """Parse 'normal' string to NORMAL urgency."""
        assert Urgency.from_string("normal") == Urgency.NORMAL

    def test_urgency_from_string_low(self):
        """Parse 'low' string to LOW urgency."""
        assert Urgency.from_string("low") == Urgency.LOW

    def test_urgency_from_string_case_insensitive(self):
        """Urgency parsing should be case insensitive."""
        assert Urgency.from_string("HIGH") == Urgency.HIGH
        assert Urgency.from_string("High") == Urgency.HIGH
        assert Urgency.from_string("NORMAL") == Urgency.NORMAL
        assert Urgency.from_string("Low") == Urgency.LOW

    def test_urgency_from_string_unknown_defaults_to_normal(self):
        """Unknown urgency values should default to NORMAL."""
        assert Urgency.from_string("unknown") == Urgency.NORMAL
        assert Urgency.from_string("invalid") == Urgency.NORMAL
        assert Urgency.from_string("") == Urgency.NORMAL
        assert Urgency.from_string("urgent") == Urgency.NORMAL

    def test_urgency_from_string_none_defaults_to_normal(self):
        """None value should default to NORMAL."""
        assert Urgency.from_string(None) == Urgency.NORMAL


class TestAIDecision:
    """Tests for AIDecision dataclass."""

    def test_decision_from_dict(self):
        """Parse AIDecision from dictionary."""
        data = {
            "execute": True,
            "size": 100.0,
            "confidence": 0.85,
            "urgency": "high",
            "reasoning": "Strong signal from high-performing wallet",
        }

        decision = AIDecision.from_dict(data)

        assert decision.execute is True
        assert decision.size == 100.0
        assert decision.confidence == 0.85
        assert decision.urgency == Urgency.HIGH
        assert decision.reasoning == "Strong signal from high-performing wallet"

    def test_decision_from_dict_with_defaults(self):
        """Parse AIDecision with missing fields uses defaults."""
        data = {}

        decision = AIDecision.from_dict(data)

        assert decision.execute is False
        assert decision.size == 0.0
        assert decision.confidence == 0.0
        assert decision.urgency == Urgency.NORMAL
        assert decision.reasoning == ""

    def test_decision_from_dict_partial_data(self):
        """Parse AIDecision with partial data."""
        data = {
            "execute": True,
            "reasoning": "Partial data test",
        }

        decision = AIDecision.from_dict(data)

        assert decision.execute is True
        assert decision.size == 0.0
        assert decision.confidence == 0.0
        assert decision.urgency == Urgency.NORMAL
        assert decision.reasoning == "Partial data test"

    def test_decision_reject(self):
        """Create rejection decision."""
        reasoning = "Wallet has poor historical performance"

        decision = AIDecision.reject(reasoning)

        assert decision.execute is False
        assert decision.size == 0.0
        assert decision.confidence == 0.0
        assert decision.urgency == Urgency.NORMAL
        assert decision.reasoning == reasoning

    def test_decision_approve(self):
        """Create approval decision with default urgency."""
        decision = AIDecision.approve(
            size=150.0,
            confidence=0.92,
            reasoning="Excellent opportunity with high confidence",
        )

        assert decision.execute is True
        assert decision.size == 150.0
        assert decision.confidence == 0.92
        assert decision.urgency == Urgency.NORMAL
        assert decision.reasoning == "Excellent opportunity with high confidence"

    def test_decision_approve_with_urgency(self):
        """Create approval decision with specified urgency."""
        decision = AIDecision.approve(
            size=200.0,
            confidence=0.95,
            reasoning="Time-sensitive opportunity",
            urgency=Urgency.HIGH,
        )

        assert decision.execute is True
        assert decision.size == 200.0
        assert decision.confidence == 0.95
        assert decision.urgency == Urgency.HIGH
        assert decision.reasoning == "Time-sensitive opportunity"

    def test_decision_approve_with_low_urgency(self):
        """Create approval decision with low urgency."""
        decision = AIDecision.approve(
            size=50.0,
            confidence=0.60,
            reasoning="Good opportunity but not urgent",
            urgency=Urgency.LOW,
        )

        assert decision.execute is True
        assert decision.size == 50.0
        assert decision.confidence == 0.60
        assert decision.urgency == Urgency.LOW
        assert decision.reasoning == "Good opportunity but not urgent"

    def test_decision_to_dict(self):
        """Serialize AIDecision to dictionary."""
        decision = AIDecision(
            execute=True,
            size=125.0,
            confidence=0.88,
            urgency=Urgency.HIGH,
            reasoning="Serialization test",
        )

        result = decision.to_dict()

        assert result == {
            "execute": True,
            "size": 125.0,
            "confidence": 0.88,
            "urgency": "high",
            "reasoning": "Serialization test",
        }

    def test_decision_to_dict_rejection(self):
        """Serialize rejection decision to dictionary."""
        decision = AIDecision.reject("Risk too high")

        result = decision.to_dict()

        assert result == {
            "execute": False,
            "size": 0.0,
            "confidence": 0.0,
            "urgency": "normal",
            "reasoning": "Risk too high",
        }

    def test_decision_roundtrip(self):
        """Verify from_dict and to_dict are inverse operations."""
        original_data = {
            "execute": True,
            "size": 175.0,
            "confidence": 0.78,
            "urgency": "low",
            "reasoning": "Roundtrip test case",
        }

        decision = AIDecision.from_dict(original_data)
        result = decision.to_dict()

        assert result == original_data

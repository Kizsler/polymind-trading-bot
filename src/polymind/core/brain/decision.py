"""AI decision response model for trading decisions."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Urgency(Enum):
    """Urgency levels for AI trading decisions."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    @classmethod
    def from_string(cls, value: str) -> "Urgency":
        """Parse urgency from string, defaulting to NORMAL for unknown values.

        Args:
            value: String representation of urgency level

        Returns:
            Corresponding Urgency enum value, defaults to NORMAL
        """
        value_lower = value.lower() if value else ""
        for urgency in cls:
            if urgency.value == value_lower:
                return urgency
        return cls.NORMAL


@dataclass
class AIDecision:
    """Response model for AI trading decisions.

    Contains the AI's decision on whether to execute a trade,
    along with sizing, confidence, urgency, and reasoning.
    """

    execute: bool
    size: float
    confidence: float
    urgency: Urgency
    reasoning: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AIDecision":
        """Parse AIDecision from a dictionary (e.g., from Claude response).

        Args:
            data: Dictionary containing decision fields

        Returns:
            AIDecision instance populated from dictionary
        """
        urgency_str = data.get("urgency", "normal")
        urgency = Urgency.from_string(urgency_str)

        return cls(
            execute=bool(data.get("execute", False)),
            size=float(data.get("size", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            urgency=urgency,
            reasoning=str(data.get("reasoning", "")),
        )

    @classmethod
    def reject(cls, reasoning: str) -> "AIDecision":
        """Create a rejection decision.

        Args:
            reasoning: Explanation for why the trade was rejected

        Returns:
            AIDecision with execute=False and zero size/confidence
        """
        return cls(
            execute=False,
            size=0.0,
            confidence=0.0,
            urgency=Urgency.NORMAL,
            reasoning=reasoning,
        )

    @classmethod
    def approve(
        cls,
        size: float,
        confidence: float,
        reasoning: str,
        urgency: Urgency = Urgency.NORMAL,
    ) -> "AIDecision":
        """Create an approval decision.

        Args:
            size: Position size for the trade
            confidence: Confidence level (0.0 to 1.0)
            reasoning: Explanation for the approval
            urgency: Urgency level for execution (default: NORMAL)

        Returns:
            AIDecision with execute=True and specified parameters
        """
        return cls(
            execute=True,
            size=size,
            confidence=confidence,
            urgency=urgency,
            reasoning=reasoning,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize AIDecision to dictionary.

        Returns:
            Dictionary representation of the decision
        """
        return {
            "execute": self.execute,
            "size": self.size,
            "confidence": self.confidence,
            "urgency": self.urgency.value,
            "reasoning": self.reasoning,
        }

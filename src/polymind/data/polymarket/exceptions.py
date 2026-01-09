"""Polymarket domain-specific exceptions."""


class PolymarketError(Exception):
    """Base exception for Polymarket-related errors."""

    def __init__(self, message: str = "A Polymarket error occurred") -> None:
        """Initialize the exception with a message."""
        self.message = message
        super().__init__(self.message)


class PolymarketAPIError(PolymarketError):
    """Exception raised when a Polymarket API call fails."""

    def __init__(
        self,
        message: str = "Polymarket API request failed",
        status_code: int | None = None,
        response: str | None = None,
    ) -> None:
        """Initialize the exception with API error details."""
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class PolymarketAuthError(PolymarketError):
    """Exception raised when authentication with Polymarket fails."""

    def __init__(
        self,
        message: str = "Polymarket authentication failed",
    ) -> None:
        """Initialize the exception with auth error details."""
        super().__init__(message)

"""Custom exception classes for PolyMind."""


class PolymindError(Exception):
    """Base exception for all PolyMind errors."""

    pass


class TradeError(PolymindError):
    """Error during trade execution."""

    pass


class RiskError(PolymindError):
    """Risk limit or validation error."""

    pass


class ConfigError(PolymindError):
    """Configuration error."""

    pass


class DataError(PolymindError):
    """Data fetching or processing error."""

    pass


class APIError(PolymindError):
    """External API error."""

    pass

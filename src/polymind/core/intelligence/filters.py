"""Market filters for allow/deny lists."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class FilterType(str, Enum):
    """Type of market filter."""

    MARKET_ID = "market_id"
    CATEGORY = "category"
    KEYWORD = "keyword"


class FilterAction(str, Enum):
    """Filter action."""

    ALLOW = "allow"
    DENY = "deny"


@dataclass
class MarketFilter:
    """A single market filter rule.

    Attributes:
        id: Filter ID.
        filter_type: Type of filter.
        value: Value to match.
        action: Whether to allow or deny.
    """

    id: int
    filter_type: FilterType
    value: str
    action: FilterAction


class DatabaseProtocol(Protocol):
    """Protocol for database dependency injection."""

    async def get_all_market_filters(self) -> list[Any]:
        """Get all market filters."""
        ...

    async def add_market_filter(
        self,
        filter_type: str,
        value: str,
        action: str,
    ) -> Any:
        """Add a market filter."""
        ...

    async def remove_market_filter(self, filter_id: int) -> bool:
        """Remove a market filter."""
        ...


@dataclass
class MarketFilterManager:
    """Manages market allow/deny filters.

    Attributes:
        db: Database connection.
    """

    db: DatabaseProtocol

    async def add_filter(
        self,
        filter_type: FilterType,
        value: str,
        action: FilterAction,
    ) -> MarketFilter:
        """Add a new filter.

        Args:
            filter_type: Type of filter.
            value: Value to match.
            action: Allow or deny.

        Returns:
            Created MarketFilter.
        """
        result = await self.db.add_market_filter(
            filter_type=filter_type.value,
            value=value,
            action=action.value,
        )

        logger.info(
            "Added {} filter: {} = {} (id={})",
            action.value,
            filter_type.value,
            value,
            result.id,
        )

        return MarketFilter(
            id=result.id,
            filter_type=filter_type,
            value=value,
            action=action,
        )

    async def remove_filter(self, filter_id: int) -> bool:
        """Remove a filter by ID.

        Args:
            filter_id: Filter ID to remove.

        Returns:
            True if removed, False if not found.
        """
        removed = await self.db.remove_market_filter(filter_id)

        if removed:
            logger.info("Removed filter id={}", filter_id)
        else:
            logger.warning("Filter id={} not found", filter_id)

        return removed

    async def get_filters(self) -> list[MarketFilter]:
        """Get all filters.

        Returns:
            List of all MarketFilter objects.
        """
        rows = await self.db.get_all_market_filters()

        filters = []
        for row in rows:
            filters.append(
                MarketFilter(
                    id=row.id,
                    filter_type=FilterType(row.filter_type),
                    value=row.value,
                    action=FilterAction(row.action),
                )
            )

        return filters

    def is_market_allowed(
        self,
        market_id: str,
        category: str,
        title: str,
        filters: list[MarketFilter],
    ) -> bool:
        """Check if a market is allowed based on filters.

        Priority:
        1. Explicit market_id allow/deny (highest priority)
        2. Category allow/deny
        3. Keyword allow/deny
        4. Default allow

        Args:
            market_id: Market identifier.
            category: Market category.
            title: Market title.
            filters: List of filters to apply.

        Returns:
            True if market is allowed, False if denied.
        """
        if not filters:
            return True  # Default allow

        # Separate filters by type and action
        market_allows = []
        market_denies = []
        category_allows = []
        category_denies = []
        keyword_allows = []
        keyword_denies = []

        for f in filters:
            if f.filter_type == FilterType.MARKET_ID:
                if f.value == market_id:
                    if f.action == FilterAction.ALLOW:
                        market_allows.append(f)
                    else:
                        market_denies.append(f)
            elif f.filter_type == FilterType.CATEGORY:
                if f.value.lower() == category.lower():
                    if f.action == FilterAction.ALLOW:
                        category_allows.append(f)
                    else:
                        category_denies.append(f)
            elif f.filter_type == FilterType.KEYWORD:
                if f.value.lower() in title.lower():
                    if f.action == FilterAction.ALLOW:
                        keyword_allows.append(f)
                    else:
                        keyword_denies.append(f)

        # Priority: market_id > category > keyword
        # Within same priority: explicit allow overrides deny
        # Exception: if both keyword allow and deny match, deny wins

        # Check market_id level
        if market_allows:
            return True
        if market_denies:
            return False

        # Check category level
        if category_allows:
            return True
        if category_denies:
            return False

        # Check keyword level - deny takes precedence here
        if keyword_denies:
            return False
        if keyword_allows:
            return True

        # Default allow
        return True

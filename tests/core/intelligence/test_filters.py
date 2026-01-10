"""Tests for market filters (allow/deny lists)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from polymind.core.intelligence.filters import (
    MarketFilter,
    MarketFilterManager,
    FilterType,
    FilterAction,
)


class MockDbFilter:
    """Mock database filter object."""
    def __init__(self, id: int, filter_type: str, value: str, action: str):
        self.id = id
        self.filter_type = filter_type
        self.value = value
        self.action = action


class TestMarketFilterManager:
    """Tests for MarketFilterManager."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create mock database."""
        db = MagicMock()
        db.add_market_filter = AsyncMock(
            return_value=MockDbFilter(
                id=1,
                filter_type="market_id",
                value="market_abc",
                action="deny",
            )
        )
        db.remove_market_filter = AsyncMock(return_value=True)
        db.get_all_market_filters = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def manager(self, mock_db: MagicMock) -> MarketFilterManager:
        """Create filter manager with mock db."""
        return MarketFilterManager(db=mock_db)

    @pytest.mark.asyncio
    async def test_add_filter(self, manager: MarketFilterManager, mock_db: MagicMock) -> None:
        """Test adding a new filter."""
        filt = await manager.add_filter(
            filter_type=FilterType.MARKET_ID,
            value="market_abc",
            action=FilterAction.DENY,
        )

        assert filt.filter_type == FilterType.MARKET_ID
        assert filt.value == "market_abc"
        assert filt.action == FilterAction.DENY
        mock_db.add_market_filter.assert_called_once_with(
            filter_type="market_id",
            value="market_abc",
            action="deny",
        )

    @pytest.mark.asyncio
    async def test_remove_filter(self, manager: MarketFilterManager, mock_db: MagicMock) -> None:
        """Test removing a filter."""
        mock_db.remove_market_filter = AsyncMock(return_value=True)

        result = await manager.remove_filter(filter_id=1)

        assert result is True
        mock_db.remove_market_filter.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_remove_filter_not_found(self, manager: MarketFilterManager, mock_db: MagicMock) -> None:
        """Test removing a non-existent filter."""
        mock_db.remove_market_filter = AsyncMock(return_value=False)

        result = await manager.remove_filter(filter_id=999)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_filters(self, manager: MarketFilterManager, mock_db: MagicMock) -> None:
        """Test getting all filters."""
        mock_db.get_all_market_filters = AsyncMock(return_value=[
            MockDbFilter(id=1, filter_type="market_id", value="market_1", action="deny"),
            MockDbFilter(id=2, filter_type="category", value="crypto", action="allow"),
        ])

        filters = await manager.get_filters()

        assert len(filters) == 2
        assert filters[0].filter_type == FilterType.MARKET_ID
        assert filters[1].filter_type == FilterType.CATEGORY

    def test_is_market_allowed_no_filters(self, manager: MarketFilterManager) -> None:
        """Test market allowed with no filters."""
        result = manager.is_market_allowed(
            market_id="market_abc",
            category="politics",
            title="Will X happen?",
            filters=[],
        )
        assert result is True  # Default allow

    def test_is_market_allowed_explicit_allow(self, manager: MarketFilterManager) -> None:
        """Test market explicitly allowed."""
        filters = [
            MarketFilter(id=1, filter_type=FilterType.MARKET_ID, value="market_abc", action=FilterAction.ALLOW),
        ]
        result = manager.is_market_allowed(
            market_id="market_abc",
            category="politics",
            title="Will X happen?",
            filters=filters,
        )
        assert result is True

    def test_is_market_denied_by_id(self, manager: MarketFilterManager) -> None:
        """Test market denied by ID."""
        filters = [
            MarketFilter(id=1, filter_type=FilterType.MARKET_ID, value="market_abc", action=FilterAction.DENY),
        ]
        result = manager.is_market_allowed(
            market_id="market_abc",
            category="politics",
            title="Will X happen?",
            filters=filters,
        )
        assert result is False

    def test_is_market_denied_by_category(self, manager: MarketFilterManager) -> None:
        """Test market denied by category."""
        filters = [
            MarketFilter(id=1, filter_type=FilterType.CATEGORY, value="crypto", action=FilterAction.DENY),
        ]
        result = manager.is_market_allowed(
            market_id="market_abc",
            category="crypto",
            title="Will BTC hit 100k?",
            filters=filters,
        )
        assert result is False

    def test_is_market_denied_by_keyword(self, manager: MarketFilterManager) -> None:
        """Test market denied by keyword in title."""
        filters = [
            MarketFilter(id=1, filter_type=FilterType.KEYWORD, value="election", action=FilterAction.DENY),
        ]
        result = manager.is_market_allowed(
            market_id="market_abc",
            category="politics",
            title="Will the election result in X?",
            filters=filters,
        )
        assert result is False

    def test_is_market_keyword_case_insensitive(self, manager: MarketFilterManager) -> None:
        """Test keyword matching is case insensitive."""
        filters = [
            MarketFilter(id=1, filter_type=FilterType.KEYWORD, value="BITCOIN", action=FilterAction.DENY),
        ]
        result = manager.is_market_allowed(
            market_id="market_abc",
            category="crypto",
            title="Will bitcoin reach new highs?",
            filters=filters,
        )
        assert result is False

    def test_allow_overrides_deny(self, manager: MarketFilterManager) -> None:
        """Test that explicit allow overrides category deny."""
        filters = [
            MarketFilter(id=1, filter_type=FilterType.CATEGORY, value="crypto", action=FilterAction.DENY),
            MarketFilter(id=2, filter_type=FilterType.MARKET_ID, value="market_abc", action=FilterAction.ALLOW),
        ]
        result = manager.is_market_allowed(
            market_id="market_abc",
            category="crypto",
            title="Will ETH flip BTC?",
            filters=filters,
        )
        # Specific market allow should override category deny
        assert result is True

    def test_deny_takes_precedence_for_same_specificity(self, manager: MarketFilterManager) -> None:
        """Test that deny wins when filters have same specificity."""
        filters = [
            MarketFilter(id=1, filter_type=FilterType.KEYWORD, value="crypto", action=FilterAction.ALLOW),
            MarketFilter(id=2, filter_type=FilterType.KEYWORD, value="bitcoin", action=FilterAction.DENY),
        ]
        result = manager.is_market_allowed(
            market_id="market_abc",
            category="crypto",
            title="Will bitcoin and crypto rally?",
            filters=filters,
        )
        # Both match, deny should take precedence
        assert result is False

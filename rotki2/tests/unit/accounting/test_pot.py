"""Unit tests for AccountingPot"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from rotkehlchen.constants import ZERO, ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import CostBasisMethod, Location, Price, Timestamp
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH, A_USD
from rotki2.accounting.pot import AccountingPot
from rotki2.accounting.price_historian import PriceHistorian


@pytest.mark.asyncio
class TestAccountingPot:
    """Test AccountingPot functionality"""
    
    async def test_add_in_event(self):
        """Test adding an acquisition event"""
        # Setup mocks
        db_service = MagicMock()
        msg_aggregator = MagicMock()
        price_historian = AsyncMock(spec=PriceHistorian)
        
        # Create pot
        pot = AccountingPot(
            database=db_service,
            msg_aggregator=msg_aggregator,
            price_historian=price_historian,
            profit_currency=A_USD,
            cost_basis_method=CostBasisMethod.FIFO,
        )
        
        # Mock price lookup
        price_historian.query_historical_price.return_value = Price(FVal('1000'))
        
        # Add an acquisition
        taxable, free = await pot.add_in_event(
            event_type=ActionType.TRADE,
            asset=A_ETH,
            amount=FVal('10'),
            timestamp=Timestamp(1000),
        )
        
        assert taxable == FVal('10')
        assert free == ZERO
        
        # Verify price was queried
        price_historian.query_historical_price.assert_called_once_with(
            from_asset=A_ETH,
            to_asset=A_USD,
            timestamp=Timestamp(1000),
        )
    
    async def test_add_out_event(self):
        """Test adding a spend event"""
        # Setup mocks
        db_service = MagicMock()
        msg_aggregator = MagicMock()
        price_historian = AsyncMock(spec=PriceHistorian)
        
        # Create pot
        pot = AccountingPot(
            database=db_service,
            msg_aggregator=msg_aggregator,
            price_historian=price_historian,
            profit_currency=A_USD,
            cost_basis_method=CostBasisMethod.FIFO,
        )
        
        # Mock settings
        pot.settings = {'include_crypto2crypto': True}
        
        # First add some assets to spend
        price_historian.query_historical_price.return_value = Price(FVal('1000'))
        await pot.add_in_event(
            event_type=ActionType.TRADE,
            asset=A_ETH,
            amount=FVal('10'),
            timestamp=Timestamp(1000),
        )
        
        # Now spend some
        price_historian.query_historical_price.return_value = Price(FVal('1500'))
        taxable, free = await pot.add_out_event(
            event_type=ActionType.TRADE,
            asset=A_ETH,
            amount=FVal('5'),
            timestamp=Timestamp(2000),
            taxable=True,
        )
        
        # The amount should be reflected in the return
        assert taxable + free == FVal('5')
    
    async def test_get_rate_in_profit_currency_same_asset(self):
        """Test getting rate when asset is the profit currency"""
        # Setup mocks
        db_service = MagicMock()
        msg_aggregator = MagicMock()
        price_historian = AsyncMock(spec=PriceHistorian)
        
        # Create pot with USD as profit currency
        pot = AccountingPot(
            database=db_service,
            msg_aggregator=msg_aggregator,
            price_historian=price_historian,
            profit_currency=A_USD,
            cost_basis_method=CostBasisMethod.FIFO,
        )
        
        # Get rate for USD in USD - should be 1
        rate = await pot.get_rate_in_profit_currency(
            asset=A_USD,
            timestamp=Timestamp(1000),
        )
        
        assert rate == Price(ONE)
        # Should not query price historian
        price_historian.query_historical_price.assert_not_called()
    
    async def test_get_prices_for_swap(self):
        """Test price calculation for swaps"""
        # Setup mocks
        db_service = MagicMock()
        msg_aggregator = MagicMock()
        price_historian = AsyncMock(spec=PriceHistorian)
        
        # Create pot
        pot = AccountingPot(
            database=db_service,
            msg_aggregator=msg_aggregator,
            price_historian=price_historian,
            profit_currency=A_USD,
            cost_basis_method=CostBasisMethod.FIFO,
        )
        
        # Mock settings
        pot.settings = {'include_fees_in_cost_basis': True}
        
        # Mock price lookups
        price_historian.query_historical_price.side_effect = [
            Price(FVal('1500')),  # ETH price
            Price(FVal('1')),     # USD price (will actually return 1 without query)
        ]
        
        # Calculate prices for ETH -> USD swap
        prices = await pot.get_prices_for_swap(
            timestamp=Timestamp(1000),
            amount_in=FVal('10'),     # 10 USD
            asset_in=A_USD,
            amount_out=FVal('0.01'),  # 0.01 ETH
            asset_out=A_ETH,
            fee_info=None,
        )
        
        assert prices is not None
        out_price, in_price = prices
        
        # Out price should be the ETH price
        assert out_price == Price(FVal('1500'))
        # In price should be 1 for USD
        assert in_price == Price(ONE)
"""Unit tests for OKX data mapper.

These tests demonstrate the improved testability of the new architecture.
No network calls or mocking required!
"""
import pytest
from decimal import Decimal

from rotki2.assets.base import Asset
from rotki2.constants import A_BTC, A_USDT
from rotki2.exchanges.adapters.okx.mapper import OkxDataMapper
from rotki2.history.events.structures.exchange import Trade
from rotki2.history.events.structures.asset import AssetMovement
from rotki2.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)


class TestOkxDataMapper:
    """Test OKX data mapping without any network calls."""
    
    @pytest.fixture
    def mapper(self):
        """Create mapper instance."""
        return OkxDataMapper()
    
    def test_to_balances(self, mapper):
        """Test balance mapping from OKX format to Rotki format."""
        # Sample OKX balance data
        raw_data = [
            {
                'ccy': 'BTC',
                'bal': '1.5',
                'availBal': '1.0',
                'account_type': 'trading'
            },
            {
                'ccy': 'USDT',
                'bal': '1000.50',
                'availBal': '1000.50',
                'account_type': 'funding'
            },
            {
                'ccy': 'UNKNOWN',  # Unknown asset
                'bal': '100',
                'availBal': '100',
                'account_type': 'trading'
            },
        ]
        
        # Map balances
        balances = mapper.to_balances(raw_data)
        
        # Verify results
        assert len(balances) == 2  # Unknown asset should be skipped
        assert balances[A_BTC] == AssetAmount('1.5')
        assert balances[A_USDT] == AssetAmount('1000.50')
    
    def test_to_trades(self, mapper):
        """Test trade mapping from OKX format to Rotki format."""
        # Sample OKX trade data
        raw_data = [
            {
                'instId': 'BTC-USDT',
                'ordId': '123456',
                'side': 'buy',
                'sz': '0.1',
                'px': '50000',
                'fee': '-0.001',  # Negative fee
                'feeCcy': 'USDT',
                'fillTime': '1640995200000'  # 2022-01-01 00:00:00
            },
            {
                'instId': 'BTC-USDT',
                'ordId': '123457',
                'side': 'sell',
                'sz': '0.05',
                'px': '51000',
                'fee': '-0.0005',
                'feeCcy': 'USDT',
                'fillTime': '1640998800000'  # 2022-01-01 01:00:00
            },
        ]
        
        # Map trades
        trades = mapper.to_trades(raw_data, Location.OKX)
        
        # Verify results
        assert len(trades) == 2
        
        # Check first trade (buy)
        trade1 = trades[0]
        assert isinstance(trade1, Trade)
        assert trade1.base_asset == A_BTC
        assert trade1.quote_asset == A_USDT
        assert trade1.trade_type == TradeType.BUY
        assert trade1.amount == AssetAmount('0.1')
        assert trade1.rate == Price('50000')
        assert trade1.fee == Fee('0.001')  # Converted to positive
        assert trade1.fee_currency == A_USDT
        assert trade1.timestamp == Timestamp(1640995200)
        assert trade1.link == '123456'
        
        # Check second trade (sell)
        trade2 = trades[1]
        assert trade2.trade_type == TradeType.SELL
        assert trade2.amount == AssetAmount('0.05')
        assert trade2.rate == Price('51000')
    
    def test_to_asset_movements(self, mapper):
        """Test deposit/withdrawal mapping from OKX format to Rotki format."""
        # Sample OKX deposit data
        deposits = [
            {
                'ccy': 'BTC',
                'amt': '0.5',
                'fee': '0',
                'ts': '1640995200000',
                'depId': 'DEP123',
                'state': '2'  # Success
            },
            {
                'ccy': 'USDT',
                'amt': '1000',
                'fee': '1',
                'ts': '1640998800000',
                'depId': 'DEP124',
                'state': '1'  # Pending - should be skipped
            },
        ]
        
        # Sample OKX withdrawal data
        withdrawals = [
            {
                'ccy': 'BTC',
                'amt': '0.1',
                'fee': '0.0005',
                'ts': '1641002400000',
                'wdId': 'WD123',
                'state': '2'  # Success
            },
        ]
        
        # Map movements
        movements = mapper.to_asset_movements(deposits, withdrawals, Location.OKX)
        
        # Verify results
        assert len(movements) == 2  # 1 deposit + 1 withdrawal (pending skipped)
        
        # Check deposit
        deposit = movements[0]
        assert isinstance(deposit, AssetMovement)
        assert deposit.category == AssetMovementCategory.DEPOSIT
        assert deposit.asset == A_BTC
        assert deposit.amount == AssetAmount('0.5')
        assert deposit.fee == Fee('0')
        assert deposit.timestamp == Timestamp(1640995200)
        assert deposit.link == 'DEP123'
        
        # Check withdrawal
        withdrawal = movements[1]
        assert withdrawal.category == AssetMovementCategory.WITHDRAWAL
        assert withdrawal.asset == A_BTC
        assert withdrawal.amount == AssetAmount('0.1')
        assert withdrawal.fee == Fee('0.0005')
    
    def test_map_asset(self, mapper):
        """Test individual asset mapping."""
        # Test known assets
        assert mapper.map_asset('BTC') == A_BTC
        assert mapper.map_asset('USDT') == A_USDT
        
        # Test unknown asset
        assert mapper.map_asset('UNKNOWNTOKEN') is None
    
    def test_edge_cases(self, mapper):
        """Test edge cases and error handling."""
        # Empty data
        assert mapper.to_balances([]) == {}
        assert mapper.to_trades([], Location.OKX) == []
        assert mapper.to_asset_movements([], [], Location.OKX) == []
        
        # Invalid data formats
        invalid_balance = [{'invalid': 'data'}]
        assert mapper.to_balances(invalid_balance) == {}
        
        invalid_trade = [{'instId': 'INVALID'}]
        assert mapper.to_trades(invalid_trade, Location.OKX) == []
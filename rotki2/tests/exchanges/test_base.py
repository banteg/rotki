"""Tests for exchange base classes"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.types import ApiKey, ApiSecret, Location, Timestamp
from rotki2.exchanges.base import ExchangeInterface, ExchangeWithExtras


class MockExchange(ExchangeInterface):
    """Mock exchange for testing base functionality"""
    
    async def query_balances(self, **kwargs):
        return {
            Asset('BTC'): Balance(amount=FVal('1.5'), usd_value=FVal('75000')),
            Asset('ETH'): Balance(amount=FVal('10'), usd_value=FVal('30000')),
        }
    
    async def query_online_trade_history(self, start_ts: Timestamp, end_ts: Timestamp):
        return []
    
    async def query_online_deposits_withdrawals(self, start_ts: Timestamp, end_ts: Timestamp):
        return []
    
    async def validate_api_key(self) -> tuple[bool, str]:
        return True, ''


class MockExchangeWithExtras(MockExchange, ExchangeWithExtras):
    """Mock exchange with extras for testing"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.account_type = 'standard'
    
    def get_extras(self):
        return {'account_type': self.account_type}
    
    def set_extras(self, extras):
        if 'account_type' in extras:
            self.account_type = extras['account_type']


@pytest.fixture
def mock_db():
    """Mock database"""
    db = MagicMock()
    db.get_exchange_credentials.return_value = {}
    return db


@pytest.fixture
def mock_msg_aggregator():
    """Mock message aggregator"""
    return MagicMock()


@pytest.fixture
def mock_http_client():
    """Mock HTTP client"""
    client = AsyncMock()
    return client


class TestExchangeInterface:
    """Test ExchangeInterface base class"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_db, mock_msg_aggregator, mock_http_client):
        """Test exchange initialization"""
        exchange = MockExchange(
            name='test_exchange',
            location=Location.BINANCE,
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
            http_client=mock_http_client,
        )
        
        assert exchange.name == 'test_exchange'
        assert exchange.location == Location.BINANCE
        assert exchange.api_key == ApiKey('test_key')
        assert exchange.secret == ApiSecret('test_secret')
        assert exchange.http_client == mock_http_client
    
    @pytest.mark.asyncio
    async def test_first_connection(self, mock_db, mock_msg_aggregator):
        """Test first connection validation"""
        exchange = MockExchange(
            name='test_exchange',
            location=Location.BINANCE,
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
        )
        
        assert not exchange.first_connection_made
        
        await exchange.first_connection()
        assert exchange.first_connection_made
        
        # Second call should not validate again
        with patch.object(exchange, 'validate_api_key') as mock_validate:
            await exchange.first_connection()
            mock_validate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_db, mock_msg_aggregator):
        """Test rate limiting functionality"""
        exchange = MockExchange(
            name='test_exchange',
            location=Location.BINANCE,
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
        )
        
        # Set aggressive rate limits for testing
        exchange.rate_limit_calls = 2
        exchange.rate_limit_period = 0.1  # 100ms
        
        # First two calls should be immediate
        start_time = asyncio.get_event_loop().time()
        await exchange._apply_rate_limit()
        await exchange._apply_rate_limit()
        
        # Third call should be delayed
        await exchange._apply_rate_limit()
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Should have waited at least the rate limit period
        assert elapsed >= 0.1
    
    @pytest.mark.asyncio
    async def test_close(self, mock_db, mock_msg_aggregator, mock_http_client):
        """Test closing exchange connections"""
        exchange = MockExchange(
            name='test_exchange',
            location=Location.BINANCE,
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
            http_client=mock_http_client,
        )
        
        await exchange.close()
        mock_http_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_balances(self, mock_db, mock_msg_aggregator):
        """Test balance querying"""
        exchange = MockExchange(
            name='test_exchange',
            location=Location.BINANCE,
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
        )
        
        balances = await exchange.query_balances()
        
        assert len(balances) == 2
        assert Asset('BTC') in balances
        assert balances[Asset('BTC')].amount == FVal('1.5')
        assert balances[Asset('BTC')].usd_value == FVal('75000')


class TestExchangeWithExtras:
    """Test ExchangeWithExtras functionality"""
    
    @pytest.mark.asyncio
    async def test_extras(self, mock_db, mock_msg_aggregator):
        """Test getting and setting extras"""
        exchange = MockExchangeWithExtras(
            name='test_exchange',
            location=Location.KRAKEN,
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
        )
        
        # Test get_extras
        extras = exchange.get_extras()
        assert extras == {'account_type': 'standard'}
        
        # Test set_extras
        exchange.set_extras({'account_type': 'pro'})
        assert exchange.account_type == 'pro'
        
        extras = exchange.get_extras()
        assert extras == {'account_type': 'pro'}
"""Tests for ExchangeManager"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.types import ApiKey, ApiSecret, Location
from rotki2.exchanges.base import ExchangeInterface
from rotki2.exchanges.manager import ExchangeManager


class MockExchange(ExchangeInterface):
    """Mock exchange for testing"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validated = False
    
    async def query_balances(self, **kwargs):
        return {}
    
    async def query_online_trade_history(self, start_ts, end_ts):
        return []
    
    async def query_online_deposits_withdrawals(self, start_ts, end_ts):
        return []
    
    async def validate_api_key(self):
        if self.validated:
            return True, ''
        return False, 'Not validated'
    
    async def first_connection(self):
        self.validated = True
        return await super().first_connection()


@pytest.fixture
def mock_db():
    """Mock database"""
    db = MagicMock()
    return db


@pytest.fixture
def mock_msg_aggregator():
    """Mock message aggregator"""
    return MagicMock()


@pytest.fixture
def exchange_manager(mock_db, mock_msg_aggregator):
    """Create ExchangeManager instance"""
    return ExchangeManager(
        database=mock_db,
        msg_aggregator=mock_msg_aggregator,
    )


class TestExchangeManager:
    """Test ExchangeManager functionality"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, exchange_manager):
        """Test manager initialization"""
        assert exchange_manager.connected_exchanges == {}
        assert exchange_manager.db is not None
        assert exchange_manager.msg_aggregator is not None
    
    @pytest.mark.asyncio
    async def test_setup_exchange_success(self, exchange_manager, mock_db):
        """Test successful exchange setup"""
        # Mock the exchange class
        with patch('rotki2.exchanges.manager.EXCHANGE_MAPPING', {Location.KRAKEN: MockExchange}):
            success, msg = await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('test_key'),
                api_secret=ApiSecret('test_secret'),
                database=mock_db,
            )
            
            assert success is True
            assert msg == ''
            assert Location.KRAKEN in exchange_manager.connected_exchanges
            assert len(exchange_manager.connected_exchanges[Location.KRAKEN]) == 1
            
            exchange = exchange_manager.connected_exchanges[Location.KRAKEN][0]
            assert exchange.name == 'test_kraken'
            assert exchange.validated is True  # first_connection was called
    
    @pytest.mark.asyncio
    async def test_setup_exchange_unsupported(self, exchange_manager, mock_db):
        """Test setup of unsupported exchange"""
        success, msg = await exchange_manager.setup_exchange(
            name='test_unknown',
            location=Location.BLOCKCHAIN_INFO,  # Not in EXCHANGE_MAPPING
            api_key=ApiKey('test_key'),
            api_secret=ApiSecret('test_secret'),
            database=mock_db,
        )
        
        assert success is False
        assert 'not supported' in msg
    
    @pytest.mark.asyncio
    async def test_setup_exchange_duplicate(self, exchange_manager, mock_db):
        """Test setup of duplicate exchange"""
        with patch('rotki2.exchanges.manager.EXCHANGE_MAPPING', {Location.KRAKEN: MockExchange}):
            # Setup first exchange
            await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('test_key'),
                api_secret=ApiSecret('test_secret'),
                database=mock_db,
            )
            
            # Try to setup duplicate
            success, msg = await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('test_key2'),
                api_secret=ApiSecret('test_secret2'),
                database=mock_db,
            )
            
            assert success is False
            assert 'already exists' in msg
    
    @pytest.mark.asyncio
    async def test_setup_exchange_validation_failure(self, exchange_manager, mock_db):
        """Test exchange setup with validation failure"""
        # Create a mock exchange that fails validation
        class FailingExchange(MockExchange):
            async def first_connection(self):
                raise RemoteError('Invalid API key')
        
        with patch('rotki2.exchanges.manager.EXCHANGE_MAPPING', {Location.KRAKEN: FailingExchange}):
            success, msg = await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('bad_key'),
                api_secret=ApiSecret('bad_secret'),
                database=mock_db,
            )
            
            assert success is False
            assert 'Invalid API key' in msg
            assert Location.KRAKEN not in exchange_manager.connected_exchanges
    
    @pytest.mark.asyncio
    async def test_delete_exchange_success(self, exchange_manager, mock_db):
        """Test successful exchange deletion"""
        with patch('rotki2.exchanges.manager.EXCHANGE_MAPPING', {Location.KRAKEN: MockExchange}):
            # Setup exchange first
            await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('test_key'),
                api_secret=ApiSecret('test_secret'),
                database=mock_db,
            )
            
            # Delete it
            success, msg = await exchange_manager.delete_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
            )
            
            assert success is True
            assert msg == ''
            assert Location.KRAKEN not in exchange_manager.connected_exchanges
    
    @pytest.mark.asyncio
    async def test_delete_exchange_not_found(self, exchange_manager):
        """Test deletion of non-existent exchange"""
        success, msg = await exchange_manager.delete_exchange(
            name='non_existent',
            location=Location.KRAKEN,
        )
        
        assert success is False
        assert 'No KRAKEN exchange connected' in msg
    
    @pytest.mark.asyncio
    async def test_edit_exchange_success(self, exchange_manager, mock_db):
        """Test successful exchange edit"""
        with patch('rotki2.exchanges.manager.EXCHANGE_MAPPING', {Location.KRAKEN: MockExchange}):
            # Setup exchange first
            await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('test_key'),
                api_secret=ApiSecret('test_secret'),
                database=mock_db,
            )
            
            # Edit it
            success, msg = await exchange_manager.edit_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                new_name='renamed_kraken',
                api_key=ApiKey('new_key'),
            )
            
            assert success is True
            assert msg == ''
            
            exchange = exchange_manager.connected_exchanges[Location.KRAKEN][0]
            assert exchange.name == 'renamed_kraken'
            assert exchange.api_key == ApiKey('new_key')
    
    @pytest.mark.asyncio
    async def test_get_exchange(self, exchange_manager, mock_db):
        """Test getting specific exchange"""
        with patch('rotki2.exchanges.manager.EXCHANGE_MAPPING', {Location.KRAKEN: MockExchange}):
            # Setup exchange
            await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('test_key'),
                api_secret=ApiSecret('test_secret'),
                database=mock_db,
            )
            
            # Get it
            exchange = exchange_manager.get_exchange('test_kraken', Location.KRAKEN)
            assert exchange is not None
            assert exchange.name == 'test_kraken'
            
            # Try non-existent
            exchange = exchange_manager.get_exchange('non_existent', Location.KRAKEN)
            assert exchange is None
    
    @pytest.mark.asyncio
    async def test_iterate_exchanges(self, exchange_manager, mock_db):
        """Test iterating through all exchanges"""
        with patch('rotki2.exchanges.manager.EXCHANGE_MAPPING', {
            Location.KRAKEN: MockExchange,
            Location.BINANCE: MockExchange,
        }):
            # Setup multiple exchanges
            await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('key1'),
                api_secret=ApiSecret('secret1'),
                database=mock_db,
            )
            
            await exchange_manager.setup_exchange(
                name='test_binance',
                location=Location.BINANCE,
                api_key=ApiKey('key2'),
                api_secret=ApiSecret('secret2'),
                database=mock_db,
            )
            
            exchanges = exchange_manager.iterate_exchanges()
            assert len(exchanges) == 2
            names = [e.name for e in exchanges]
            assert 'test_kraken' in names
            assert 'test_binance' in names
    
    @pytest.mark.asyncio
    async def test_query_all_balances(self, exchange_manager, mock_db):
        """Test querying balances from all exchanges"""
        # Create mock exchanges with different balances
        class KrakenMock(MockExchange):
            async def query_balances(self, **kwargs):
                from rotkehlchen.accounting.structures.balance import Balance
                from rotkehlchen.assets.asset import Asset
                from rotkehlchen.fval import FVal
                return {
                    Asset('BTC'): Balance(amount=FVal('1'), usd_value=FVal('50000')),
                }
        
        class BinanceMock(MockExchange):
            async def query_balances(self, **kwargs):
                from rotkehlchen.accounting.structures.balance import Balance
                from rotkehlchen.assets.asset import Asset
                from rotkehlchen.fval import FVal
                return {
                    Asset('ETH'): Balance(amount=FVal('10'), usd_value=FVal('30000')),
                }
        
        with patch('rotki2.exchanges.manager.EXCHANGE_MAPPING', {
            Location.KRAKEN: KrakenMock,
            Location.BINANCE: BinanceMock,
        }):
            # Setup exchanges
            await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('key1'),
                api_secret=ApiSecret('secret1'),
                database=mock_db,
            )
            
            await exchange_manager.setup_exchange(
                name='test_binance',
                location=Location.BINANCE,
                api_key=ApiKey('key2'),
                api_secret=ApiSecret('secret2'),
                database=mock_db,
            )
            
            # Query all balances
            balances, errors = await exchange_manager.query_all_balances()
            
            assert len(errors) == 0
            assert Location.KRAKEN in balances
            assert Location.BINANCE in balances
            
            from rotkehlchen.assets.asset import Asset
            assert Asset('BTC') in balances[Location.KRAKEN]
            assert Asset('ETH') in balances[Location.BINANCE]
    
    @pytest.mark.asyncio
    async def test_close_all(self, exchange_manager, mock_db):
        """Test closing all exchanges"""
        with patch('rotki2.exchanges.manager.EXCHANGE_MAPPING', {Location.KRAKEN: MockExchange}):
            # Setup exchange
            await exchange_manager.setup_exchange(
                name='test_kraken',
                location=Location.KRAKEN,
                api_key=ApiKey('test_key'),
                api_secret=ApiSecret('test_secret'),
                database=mock_db,
            )
            
            # Mock close method
            exchange = exchange_manager.connected_exchanges[Location.KRAKEN][0]
            exchange.close = AsyncMock()
            
            # Close all
            await exchange_manager.close_all()
            
            exchange.close.assert_called_once()
            assert len(exchange_manager.connected_exchanges) == 0
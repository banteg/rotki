"""Tests for Kraken exchange implementation"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import Trade, TradeType
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.fval import FVal
from rotkehlchen.types import ApiKey, ApiSecret, Location, Timestamp
from rotki2.exchanges.kraken import Kraken


@pytest.fixture
def mock_kraken_response():
    """Mock responses for Kraken API"""
    return {
        'balance': {
            'result': {
                'XXBT': '1.5000000000',
                'XETH': '10.0000000000',
                'ZUSD': '5000.00',
            }
        },
        'trades': {
            'result': {
                'trades': {
                    'TRADE1': {
                        'time': 1609459200.0,
                        'pair': 'XXBTZUSD',
                        'type': 'buy',
                        'vol': '0.1',
                        'price': '30000.0',
                        'fee': '7.5',
                    }
                },
                'count': 1,
            }
        },
        'ledgers': {
            'result': {
                'ledger': {
                    'LEDGER1': {
                        'time': 1609459200.0,
                        'type': 'deposit',
                        'asset': 'XXBT',
                        'amount': '0.5',
                        'fee': '0.0',
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_http_client(mock_kraken_response):
    """Mock HTTP client for Kraken"""
    client = AsyncMock()
    
    # Mock different API responses
    async def mock_post(url, **kwargs):
        response = AsyncMock()
        response.status_code = 200
        
        if 'Balance' in url:
            response.json.return_value = mock_kraken_response['balance']
        elif 'TradesHistory' in url:
            response.json.return_value = mock_kraken_response['trades']
        elif 'Ledgers' in url:
            response.json.return_value = mock_kraken_response['ledgers']
        else:
            response.json.return_value = {'result': {}, 'error': []}
        
        return response
    
    client.post = mock_post
    client.get = AsyncMock()
    return client


class TestKraken:
    """Test Kraken exchange implementation"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_db, mock_msg_aggregator):
        """Test Kraken initialization with account type"""
        kraken = Kraken(
            name='my_kraken',
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
            kraken_account_type=KrakenAccountType.PRO,
        )
        
        assert kraken.name == 'my_kraken'
        assert kraken.location == Location.KRAKEN
        assert kraken.account_type == KrakenAccountType.PRO
        
        # Check rate limits for PRO account
        assert kraken.call_limit == 20
        assert kraken.reduction_every_secs == 1
    
    @pytest.mark.asyncio
    async def test_get_set_extras(self, mock_db, mock_msg_aggregator):
        """Test getting and setting Kraken extras"""
        kraken = Kraken(
            name='my_kraken',
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
            kraken_account_type=KrakenAccountType.STARTER,
        )
        
        # Test get_extras
        extras = kraken.get_extras()
        assert extras == {'account_type': 'starter'}
        
        # Test set_extras
        kraken.set_extras({'account_type': 'intermediate'})
        assert kraken.account_type == KrakenAccountType.INTERMEDIATE
        assert kraken.call_limit == 20
        assert kraken.reduction_every_secs == 60
    
    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, mock_db, mock_msg_aggregator, mock_http_client):
        """Test successful API key validation"""
        kraken = Kraken(
            name='my_kraken',
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
        )
        kraken.http_client = mock_http_client
        
        success, msg = await kraken.validate_api_key()
        assert success is True
        assert msg == ''
    
    @pytest.mark.asyncio
    async def test_validate_api_key_failure(self, mock_db, mock_msg_aggregator):
        """Test failed API key validation"""
        kraken = Kraken(
            name='my_kraken',
            api_key=ApiKey('invalid_key'),
            secret=ApiSecret('invalid_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
        )
        
        # Mock failed response
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'error': ['Invalid API-Key'],
            'result': {}
        }
        mock_client.post.return_value = mock_response
        kraken.http_client = mock_client
        
        success, msg = await kraken.validate_api_key()
        assert success is False
        assert 'Invalid API key' in msg
    
    @pytest.mark.asyncio
    async def test_query_balances(self, mock_db, mock_msg_aggregator, mock_http_client):
        """Test balance querying"""
        kraken = Kraken(
            name='my_kraken',
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
        )
        kraken.http_client = mock_http_client
        
        balances = await kraken.query_balances()
        
        # Check BTC balance (XXBT in Kraken)
        assert len(balances) == 3
        
        # Note: The actual implementation would need proper asset mapping
        # For now, we're using simplified asset names
        btc_balance = next((b for a, b in balances.items() if 'BT' in str(a)), None)
        assert btc_balance is not None
        assert btc_balance.amount == FVal('1.5')
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_db, mock_msg_aggregator):
        """Test Kraken-specific rate limiting"""
        kraken = Kraken(
            name='my_kraken',
            api_key=ApiKey('test_key'),
            secret=ApiSecret('test_secret'),
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
            kraken_account_type=KrakenAccountType.STARTER,
        )
        
        # Set counter near limit
        kraken.call_counter = 14
        
        # Mock sleep to track if rate limiting occurs
        with patch('anyio.sleep') as mock_sleep:
            await kraken._apply_rate_limit()
            
            # Should not sleep yet
            mock_sleep.assert_not_called()
            
            # Now at limit
            assert kraken.call_counter == 15
            
            # Next call should trigger rate limit
            await kraken._apply_rate_limit()
            
            # Should have slept
            mock_sleep.assert_called()
            assert kraken.call_counter == 1  # Reset after wait
    
    @pytest.mark.asyncio
    async def test_signature_generation(self, mock_db, mock_msg_aggregator):
        """Test API signature generation"""
        kraken = Kraken(
            name='my_kraken',
            api_key=ApiKey('test_key'),
            secret=ApiSecret('dGVzdF9zZWNyZXQ='),  # base64 encoded
            database=mock_db,
            msg_aggregator=mock_msg_aggregator,
        )
        
        # Test signature generation
        urlpath = '/0/private/Balance'
        data = {'nonce': 1234567890}
        nonce = 1234567890
        
        signature = kraken._generate_signature(urlpath, data, nonce)
        
        # Signature should be a non-empty string
        assert isinstance(signature, str)
        assert len(signature) > 0
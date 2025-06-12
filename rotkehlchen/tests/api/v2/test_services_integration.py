"""Integration tests for v2 API services"""
import pytest
from unittest.mock import MagicMock, patch
from sqlmodel import Session, create_engine
from collections import defaultdict

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.v2.services.balances import BalancesService
from rotkehlchen.api.v2.services.history import HistoryService
from rotkehlchen.api.v2.services.reports import ReportsService
from rotkehlchen.api.v2.services.blockchain import BlockchainService
from rotkehlchen.api.v2.services.nfts import NFTService
from rotkehlchen.api.v2.services.defi import DeFiService
from rotkehlchen.api.v2.services.names import NamesService
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.db.orm.names import AddressbookEntry, AddressbookType
from rotkehlchen.db.orm.querying import AddressbookFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, ChecksumEvmAddress, OptionalChainAddress, SupportedBlockchain
from rotkehlchen.history.events.structures.base import HistoryEventType


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection"""
    db_conn = MagicMock(spec=DBConnection)
    # Mock the connection contexts
    db_conn.read_ctx.return_value.__enter__ = MagicMock()
    db_conn.read_ctx.return_value.__exit__ = MagicMock(return_value=None)
    db_conn.write_ctx.return_value.__enter__ = MagicMock()
    db_conn.write_ctx.return_value.__exit__ = MagicMock(return_value=None)
    return db_conn


@pytest.fixture
def mock_chains_aggregator():
    """Create a mock chains aggregator"""
    aggregator = MagicMock()
    # Mock accounts
    aggregator.accounts.eth = [
        string_to_evm_address('0x1234567890123456789012345678901234567890'),
        string_to_evm_address('0xabcdefabcdefabcdefabcdefabcdefabcdefabcd'),
    ]
    # Mock chain manager
    eth_manager = MagicMock()
    aggregator.get_chain_manager.return_value = eth_manager
    return aggregator


@pytest.fixture
def mock_exchange_manager():
    """Create a mock exchange manager"""
    manager = MagicMock()
    manager.query_balances.return_value = {
        'binance': {
            'ETH': {'amount': '1.5', 'usd_value': '3000'},
            'BTC': {'amount': '0.1', 'usd_value': '4000'},
        },
    }
    return manager


@pytest.fixture
def mock_notifier():
    """Create a mock notifier"""
    notifier = MagicMock()
    notifier.broadcast = MagicMock()
    return notifier


class TestBalancesServiceIntegration:
    """Integration tests for BalancesService"""

    def test_get_all_balances_with_mocked_sources(
        self,
        mock_chains_aggregator,
        mock_exchange_manager,
        mock_notifier,
    ):
        """Test getting all balances with mocked data sources"""
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")
        
        with Session(engine) as session:
            service = BalancesService(
                session=session,
                chain_manager=mock_chains_aggregator,
                exchange_manager=mock_exchange_manager,
                notifier=mock_notifier,
            )
            
            # Mock the balance sources to return test data
            with patch.object(service.aggregator, 'aggregate_balances') as mock_aggregate:
                # Create mock balance sheet
                from rotkehlchen.api.v2.services.balance_aggregator import LocationBalanceSheet
                balance_sheet = LocationBalanceSheet()
                
                # Add some test balances
                eth_asset = Asset('ETH')
                btc_asset = Asset('BTC')
                
                balance_sheet.add(Location.ETHEREUM, eth_asset, Balance(amount=FVal('2.5'), usd_value=FVal('5000')))
                balance_sheet.add(Location.BINANCE, eth_asset, Balance(amount=FVal('1.5'), usd_value=FVal('3000')))
                balance_sheet.add(Location.BINANCE, btc_asset, Balance(amount=FVal('0.1'), usd_value=FVal('4000')))
                
                mock_aggregate.return_value = balance_sheet
                
                # Get all balances
                result = service.get_all_balances(save_data=False)
                
                # Verify the result structure
                assert 'assets' in result
                assert 'liabilities' in result
                assert 'total_net_value' in result
                
                # Verify balance data
                assert Location.ETHEREUM.value in result['assets']
                assert Location.BINANCE.value in result['assets']
                assert result['assets'][Location.ETHEREUM.value]['ETH']['amount'] == '2.5'
                assert result['assets'][Location.BINANCE.value]['ETH']['amount'] == '1.5'
                assert result['assets'][Location.BINANCE.value]['BTC']['amount'] == '0.1'
                assert result['total_net_value'] == '12000'  # 5000 + 3000 + 4000
                
                # Verify notifications were sent
                assert mock_notifier.broadcast.call_count == 2
                mock_notifier.broadcast.assert_any_call(
                    event_type='balance_query_started',
                    data={'query_type': 'all_balances'},
                )
                mock_notifier.broadcast.assert_any_call(
                    event_type='balance_query_completed',
                    data={'query_type': 'all_balances', 'total_net_value': '12000'},
                )

    def test_add_manual_balance(self):
        """Test adding a manual balance"""
        engine = create_engine("sqlite:///:memory:")
        
        # Create the manually_tracked_balances table
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(engine)
        
        with Session(engine) as session:
            service = BalancesService(session=session)
            
            # Add a manual balance
            eth_asset = Asset('ETH')
            balance = service.add_manual_balance(
                asset=eth_asset,
                amount=FVal('1.5'),
                location=Location.ETHEREUM,
                label='My ETH wallet',
            )
            
            assert balance.amount == FVal('1.5')
            assert balance.asset == eth_asset
            assert balance.location == Location.ETHEREUM
            assert balance.label == 'My ETH wallet'


class TestHistoryServiceIntegration:
    """Integration tests for HistoryService"""

    def test_get_history_events(self, mock_db_connection):
        """Test getting history events"""
        service = HistoryService(db_connection=mock_db_connection)
        
        # Mock the database query
        mock_cursor = MagicMock()
        mock_db_connection.read_ctx.return_value.__enter__.return_value = mock_cursor
        
        with patch.object(service.history_events_db, 'get_history_events') as mock_get:
            # Mock return value
            from rotkehlchen.history.events.structures.base import HistoryEvent
            from rotkehlchen.accounting.structures.balance import Balance
            
            mock_event = HistoryEvent(
                event_identifier='tx_123',
                sequence_index=0,
                timestamp=1609459200,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype='buy',
                asset=Asset('ETH'),
                balance=Balance(amount=FVal('1'), usd_value=FVal('2000')),
            )
            mock_get.return_value = ([mock_event], 1)
            
            # Get events
            events = service.get_history_events(
                from_timestamp=1609459200,
                to_timestamp=1609545600,
                event_types=[HistoryEventType.TRADE],
                limit=10,
                offset=0,
            )
            
            assert len(events) == 1
            assert events[0]['event_identifier'] == 'tx_123'
            assert events[0]['event_type'] == HistoryEventType.TRADE.serialize()
            assert events[0]['asset'] == 'ETH'
            assert events[0]['balance']['amount'] == '1'

    def test_process_history_with_manager(self, mock_db_connection, mock_notifier):
        """Test processing history with manager"""
        mock_history_manager = MagicMock()
        mock_task_manager = MagicMock()
        mock_task_manager.start_task.return_value = 54321
        
        service = HistoryService(
            db_connection=mock_db_connection,
            history_manager=mock_history_manager,
            task_manager=mock_task_manager,
            notifier=mock_notifier,
        )
        
        # Process history
        task_id = service.process_history(
            from_timestamp=1609459200,
            to_timestamp=1609545600,
        )
        
        assert task_id == 54321
        
        # Verify notification was sent
        mock_notifier.broadcast.assert_called_once_with(
            event_type='history_processing_started',
            data={
                'from_timestamp': 1609459200,
                'to_timestamp': 1609545600,
            },
        )
        
        # Verify task was started
        mock_task_manager.start_task.assert_called_once()


class TestBlockchainServiceIntegration:
    """Integration tests for BlockchainService"""

    def test_add_blockchain_accounts(self, mock_db_connection):
        """Test adding blockchain accounts"""
        # Create a mock database service
        db_service = MagicMock(spec=DatabaseService)
        db_service.conn = mock_db_connection
        
        service = BlockchainService(db_service=db_service)
        
        # Mock cursor for database operations
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # Account doesn't exist
        mock_db_connection.write_ctx.return_value.__enter__.return_value = mock_cursor
        
        # Add accounts
        accounts = [
            '0x1234567890123456789012345678901234567890',
            '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
        ]
        labels = ['Account 1', 'Account 2']
        tags = [['defi', 'personal'], ['trading']]
        
        added = service.add_blockchain_accounts(
            blockchain='ETH',
            accounts=accounts,
            labels=labels,
            tags=tags,
        )
        
        assert len(added) == 2
        assert added == accounts
        
        # Verify database operations
        assert mock_cursor.execute.call_count >= 2  # At least checking and inserting


class TestNFTServiceIntegration:
    """Integration tests for NFTService"""

    def test_get_all_nfts(self, mock_db_connection, mock_chains_aggregator):
        """Test getting all NFTs"""
        service = NFTService(
            db_connection=mock_db_connection,
            chains_aggregator=mock_chains_aggregator,
        )
        
        # Mock the NFT module
        mock_nft_module = MagicMock()
        mock_result = MagicMock()
        mock_result.addresses = {
            string_to_evm_address('0x1234567890123456789012345678901234567890'): [
                MagicMock(
                    token_identifier='1',
                    asset=Asset('_nft_0x1234_1'),
                    name='Cool NFT #1',
                    image_url='https://example.com/nft1.png',
                    collection=MagicMock(name='Cool Collection'),
                    price_in_asset=FVal('0.5'),
                    price_asset=Asset('ETH'),
                    manually_input=False,
                    usd_price=FVal('1000'),
                ),
            ],
        }
        mock_result.total_usd_value = FVal('1000')
        mock_nft_module.get_all_info.return_value = mock_result
        
        with patch.object(service, 'nft_module', mock_nft_module):
            with patch.object(service, '_check_premium', return_value=True):
                result = service.get_all_nfts(ignore_cache=False)
                
                assert 'addresses' in result
                assert 'total' in result
                assert 'premium' in result
                
                # Check the NFT data
                nfts = list(result['addresses'].values())[0]
                assert len(nfts) == 1
                assert nfts[0]['name'] == 'Cool NFT #1'
                assert nfts[0]['asset'] == '_nft_0x1234_1'
                assert nfts[0]['price_in_asset'] == '0.5'
                assert nfts[0]['usd_price'] == '1000'


class TestDeFiServiceIntegration:
    """Integration tests for DeFiService"""

    def test_get_defi_metadata(self, mock_db_connection):
        """Test getting DeFi protocol metadata"""
        service = DeFiService(db_connection=mock_db_connection)
        
        protocols = service.get_defi_metadata()
        
        # Should return a list of protocols
        assert isinstance(protocols, list)
        assert len(protocols) > 0
        
        # Check protocol structure
        protocol = protocols[0]
        assert 'identifier' in protocol
        assert 'name' in protocol
        assert 'description' in protocol
        assert 'url' in protocol

    def test_get_module_balances(self, mock_db_connection, mock_chains_aggregator):
        """Test getting module balances"""
        service = DeFiService(
            db_connection=mock_db_connection,
            chains_aggregator=mock_chains_aggregator,
        )
        
        # Mock the module
        mock_module = MagicMock()
        mock_module.get_balances.return_value = {
            string_to_evm_address('0x1234567890123456789012345678901234567890'): {
                'protocol': 'Uniswap V2',
                'positions': [
                    {
                        'pool': 'ETH-USDC',
                        'amount': '100',
                        'value_usd': '5000',
                    },
                ],
            },
        }
        
        with patch.object(service, '_get_module', return_value=mock_module):
            result = service.get_module_balances(
                blockchain='eth',
                module_name='uniswap',
                version=2,
            )
            
            assert 'module' in result
            assert 'balances' in result
            assert result['module'] == 'uniswap'


class TestNamesServiceIntegration:
    """Integration tests for NamesService"""

    def test_reverse_ens_lookup(self, mock_db_connection, mock_chains_aggregator):
        """Test reverse ENS lookup"""
        service = NamesService(
            db_connection=mock_db_connection,
            chains_aggregator=mock_chains_aggregator,
        )
        
        # Mock ENS lookup
        eth_manager = mock_chains_aggregator.get_chain_manager.return_value
        eth_manager.ens_lookup.side_effect = ['vitalik.eth', None]
        
        addresses = [
            string_to_evm_address('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'),
            string_to_evm_address('0x0000000000000000000000000000000000000000'),
        ]
        
        result = service.reverse_ens_lookup(addresses)
        
        assert result[addresses[0]] == 'vitalik.eth'
        assert result[addresses[1]] is None

    def test_addressbook_operations(self, mock_db_connection):
        """Test addressbook CRUD operations"""
        # Mock data handler
        mock_data = MagicMock()
        mock_addressbook_repo = MagicMock()
        mock_data.db.repos.address_book = mock_addressbook_repo
        mock_data.db.repos.unit_of_work.return_value.__enter__ = MagicMock()
        mock_data.db.repos.unit_of_work.return_value.__exit__ = MagicMock()
        
        service = NamesService(
            db_connection=mock_db_connection,
            data_handler=mock_data,
        )
        
        # Test adding entries
        entries = [
            {
                'address': '0x1234567890123456789012345678901234567890',
                'name': 'My Main Wallet',
                'blockchain': 'ETH',
            },
        ]
        
        result = service.add_addressbook_entries(
            book_type=AddressbookType.PRIVATE,
            entries=entries,
        )
        
        assert 'message' in result
        assert 'Added 1 entries' in result['message']
        
        # Verify the repository method was called
        mock_addressbook_repo.add_or_update_entries.assert_called_once()


class TestReportsServiceIntegration:
    """Integration tests for ReportsService"""

    def test_generate_report_with_accountant(self, mock_db_connection, mock_notifier):
        """Test generating report with accountant"""
        db_service = MagicMock(spec=DatabaseService)
        db_service.conn = mock_db_connection
        
        mock_accountant = MagicMock()
        mock_accountant.process_history.return_value = 98765
        
        service = ReportsService(
            db_service=db_service,
            accountant=mock_accountant,
            notifier=mock_notifier,
        )
        
        # Generate report
        report_id = service.generate_report(
            from_timestamp=1609459200,
            to_timestamp=1609545600,
            report_name='Test Report',
        )
        
        assert report_id == 98765
        
        # Verify accountant was called
        mock_accountant.process_history.assert_called_once_with(
            start_ts=1609459200,
            end_ts=1609545600,
        )
        
        # Verify notification was sent
        mock_notifier.broadcast.assert_called_once_with(
            event_type='report_started',
            data={'report_id': 98765},
        )
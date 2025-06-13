"""Tests for async ETH2 repository and service."""
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.repositories.eth2 import Eth2Repository
from rotki2.api.v2.services.async_eth2 import AsyncEth2Service
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDailyStats, ValidatorDetails
from rotkehlchen.constants import ONE
from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Timestamp


@pytest_asyncio.fixture
async def setup_eth2_tables(async_session: AsyncSession):
    """Set up ETH2 tables for testing."""
    # Create eth2_validators table
    await async_session.execute(text("""
        CREATE TABLE IF NOT EXISTS eth2_validators (
            validator_index INTEGER PRIMARY KEY NOT NULL,
            public_key TEXT NOT NULL UNIQUE,
            ownership_proportion TEXT NOT NULL,
            withdrawal_address TEXT,
            activation_timestamp INTEGER
        )
    """))
    
    # Create eth2_daily_staking_details table
    await async_session.execute(text("""
        CREATE TABLE IF NOT EXISTS eth2_daily_staking_details (
            validator_index INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            pnl TEXT NOT NULL,
            PRIMARY KEY (validator_index, timestamp),
            FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index)
        )
    """))
    
    await async_session.commit()


@pytest_asyncio.fixture
async def eth2_repository(
    async_session: AsyncSession,
    setup_eth2_tables,
) -> Eth2Repository:
    """Create an async ETH2 repository instance."""
    return Eth2Repository(async_session)


@pytest_asyncio.fixture
async def eth2_service(
    eth2_repository: Eth2Repository,
) -> AsyncEth2Service:
    """Create an async ETH2 service instance."""
    return AsyncEth2Service(eth2_repository)


@pytest.fixture
def sample_validator() -> ValidatorDetails:
    """Create a sample validator for testing."""
    return ValidatorDetails(
        validator_index=12345,
        public_key=Eth2PubKey('0x' + 'a' * 96),
        ownership_proportion=ONE,
        withdrawal_address=ChecksumEvmAddress('0x' + 'b' * 40),
        activation_timestamp=Timestamp(1606824023),
        validator_type='own',  # Add the required validator_type field
    )


@pytest.fixture
def sample_daily_stats() -> ValidatorDailyStats:
    """Create sample daily stats for testing."""
    return ValidatorDailyStats(
        validator_index=12345,
        timestamp=Timestamp(1640000000),
        pnl=FVal('0.05'),
    )


@pytest.mark.asyncio
async def test_add_validator(async_session: AsyncSession, setup_eth2_tables):
    """Test adding a validator using raw SQL."""
    # Insert validator
    await async_session.execute(text("""
        INSERT INTO eth2_validators (
            validator_index, public_key, ownership_proportion,
            withdrawal_address, activation_timestamp
        ) VALUES (
            :index, :pubkey, :ownership, :withdrawal, :activation
        )
    """), {
        'index': 12345,
        'pubkey': '0x' + 'a' * 96,
        'ownership': '1',
        'withdrawal': '0x' + 'b' * 40,
        'activation': 1606824023,
    })
    await async_session.commit()
    
    # Verify validator was created
    result = await async_session.execute(
        text("SELECT * FROM eth2_validators WHERE validator_index = :index"),
        {'index': 12345}
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == 12345  # validator_index
    assert row[1] == '0x' + 'a' * 96  # public_key
    assert row[2] == '1'  # ownership_proportion


@pytest.mark.asyncio
async def test_add_validator_daily_stats(async_session: AsyncSession, setup_eth2_tables):
    """Test adding validator daily stats."""
    # First add a validator
    await async_session.execute(text("""
        INSERT INTO eth2_validators (validator_index, public_key, ownership_proportion)
        VALUES (:index, :pubkey, :ownership)
    """), {'index': 12345, 'pubkey': '0xabc', 'ownership': '1'})
    
    # Add daily stats
    await async_session.execute(text("""
        INSERT INTO eth2_daily_staking_details (validator_index, timestamp, pnl)
        VALUES (:index, :ts, :pnl)
    """), {'index': 12345, 'ts': 1640000000, 'pnl': '0.05'})
    
    await async_session.commit()
    
    # Verify stats were created
    result = await async_session.execute(
        text("SELECT * FROM eth2_daily_staking_details WHERE validator_index = :index"),
        {'index': 12345}
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == 12345  # validator_index
    assert row[1] == 1640000000  # timestamp
    assert row[2] == '0.05'  # pnl


@pytest.mark.asyncio
async def test_get_validators(
    eth2_repository: Eth2Repository,
    sample_validator: ValidatorDetails,
):
    """Test getting validators through repository."""
    # Add validator
    await eth2_repository.add_or_update_validators([sample_validator])
    
    # Get validators
    validators = await eth2_repository.get_validators()
    assert len(validators) == 1
    assert validators[0].validator_index == sample_validator.validator_index
    assert validators[0].public_key == sample_validator.public_key
    assert validators[0].ownership_proportion == sample_validator.ownership_proportion


@pytest.mark.asyncio
async def test_validator_exists(
    eth2_repository: Eth2Repository,
    sample_validator: ValidatorDetails,
):
    """Test checking if validator exists."""
    # Initially should not exist
    assert not await eth2_repository.validator_exists(pubkey=sample_validator.public_key, index=None)
    assert not await eth2_repository.validator_exists(pubkey=None, index=sample_validator.validator_index)
    
    # Add validator
    await eth2_repository.add_or_update_validators([sample_validator])
    
    # Now should exist
    assert await eth2_repository.validator_exists(pubkey=sample_validator.public_key, index=None)
    assert await eth2_repository.validator_exists(pubkey=None, index=sample_validator.validator_index)


@pytest.mark.asyncio
async def test_edit_validator_ownership(
    eth2_repository: Eth2Repository,
    sample_validator: ValidatorDetails,
):
    """Test editing validator ownership proportion."""
    # Add validator
    await eth2_repository.add_or_update_validators([sample_validator])
    
    # Edit ownership
    new_ownership = FVal('0.5')
    await eth2_repository.edit_validator_ownership(
        validator_index=sample_validator.validator_index,
        ownership_proportion=new_ownership,
    )
    
    # Verify update
    validators = await eth2_repository.get_validators()
    assert len(validators) == 1
    assert validators[0].ownership_proportion == new_ownership


@pytest.mark.asyncio
async def test_delete_validators(
    eth2_repository: Eth2Repository,
    sample_validator: ValidatorDetails,
    sample_daily_stats: ValidatorDailyStats,
):
    """Test deleting validators."""
    # Add validator and stats
    await eth2_repository.add_or_update_validators([sample_validator])
    await eth2_repository.add_validator_daily_stats([sample_daily_stats])
    
    # Delete validator
    await eth2_repository.delete_validators([sample_validator.validator_index])
    
    # Verify deletion
    validators = await eth2_repository.get_validators()
    assert len(validators) == 0
    
    # Verify stats also deleted
    stats = await eth2_repository.get_validator_daily_stats(
        validator_indices=[sample_validator.validator_index]
    )
    assert len(stats) == 0


@pytest.mark.asyncio
async def test_get_validator_daily_stats(
    eth2_repository: Eth2Repository,
    sample_validator: ValidatorDetails,
):
    """Test getting validator daily stats."""
    # Add validator
    await eth2_repository.add_or_update_validators([sample_validator])
    
    # Add multiple daily stats
    stats_to_add = [
        ValidatorDailyStats(
            validator_index=sample_validator.validator_index,
            timestamp=Timestamp(1640000000 + i * 86400),
            pnl=FVal(f'0.0{i+1}'),
        )
        for i in range(5)
    ]
    await eth2_repository.add_validator_daily_stats(stats_to_add)
    
    # Get all stats
    stats = await eth2_repository.get_validator_daily_stats(
        validator_indices=[sample_validator.validator_index]
    )
    assert len(stats) == 5
    
    # Test with filter
    filter_query = Eth2DailyStatsFilterQuery.make(
        validator_indices=[sample_validator.validator_index],
        limit=3,
    )
    stats, count, pnl_sum = await eth2_repository.get_validator_daily_stats_and_limit_info(filter_query)
    assert len(stats) == 3
    assert count == 5
    assert pnl_sum == FVal('0.15')  # 0.01 + 0.02 + 0.03 + 0.04 + 0.05


@pytest.mark.asyncio
async def test_get_performance_stats(
    eth2_repository: Eth2Repository,
    sample_validator: ValidatorDetails,
):
    """Test getting performance stats."""
    # Add validator
    await eth2_repository.add_or_update_validators([sample_validator])
    
    # Add daily stats
    stats_to_add = [
        ValidatorDailyStats(
            validator_index=sample_validator.validator_index,
            timestamp=Timestamp(1640000000 + i * 86400),
            pnl=FVal('0.01'),
        )
        for i in range(10)
    ]
    await eth2_repository.add_validator_daily_stats(stats_to_add)
    
    # Get performance
    performance = await eth2_repository.get_performance_stats(
        validator_indices=[sample_validator.validator_index]
    )
    assert sample_validator.validator_index in performance
    assert performance[sample_validator.validator_index] == FVal('0.1')  # 0.01 * 10


@pytest.mark.asyncio
async def test_service_add_validator(
    eth2_service: AsyncEth2Service,
    sample_validator: ValidatorDetails,
):
    """Test adding validator through service."""
    result = await eth2_service.add_validator(
        validator_index=sample_validator.validator_index,
        public_key=sample_validator.public_key,
        ownership_proportion=sample_validator.ownership_proportion,
        withdrawal_address=sample_validator.withdrawal_address,
        activation_timestamp=sample_validator.activation_timestamp,
    )
    
    assert 'message' in result
    assert 'Successfully added' in result['message']


@pytest.mark.asyncio
async def test_service_duplicate_validator_fails(
    eth2_service: AsyncEth2Service,
    sample_validator: ValidatorDetails,
):
    """Test that adding duplicate validator fails."""
    # Add validator
    await eth2_service.add_validator(
        validator_index=sample_validator.validator_index,
        public_key=sample_validator.public_key,
    )
    
    # Try to add again - should fail
    with pytest.raises(InputError):
        await eth2_service.add_validator(
            validator_index=sample_validator.validator_index,
            public_key=sample_validator.public_key,
        )


@pytest.mark.asyncio
async def test_service_get_validators(
    eth2_service: AsyncEth2Service,
    sample_validator: ValidatorDetails,
):
    """Test getting validators through service."""
    # Add validator
    await eth2_service.add_validator(
        validator_index=sample_validator.validator_index,
        public_key=sample_validator.public_key,
    )
    
    # Get validators
    result = await eth2_service.get_validators()
    
    assert 'entries' in result
    assert len(result['entries']) == 1
    assert result['entries_found'] == 1
    assert result['entries_total'] == 1
    
    validator_data = result['entries'][0]
    assert validator_data['validator_index'] == sample_validator.validator_index
    assert validator_data['public_key'] == sample_validator.public_key
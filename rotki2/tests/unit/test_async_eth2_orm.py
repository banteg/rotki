"""Tests for async ETH2 repository using ORM."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.repositories.eth2 import Eth2Repository
from rotki2.api.v2.services.async_eth2 import AsyncEth2Service
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDailyStats, ValidatorDetails
from rotkehlchen.constants import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Timestamp


@pytest_asyncio.fixture
async def eth2_repository(async_session: AsyncSession) -> Eth2Repository:
    """Create an async ETH2 repository instance."""
    return Eth2Repository(async_session)


@pytest_asyncio.fixture
async def eth2_service(eth2_repository: Eth2Repository) -> AsyncEth2Service:
    """Create an async ETH2 service instance."""
    return AsyncEth2Service(eth2_repository)


@pytest.mark.asyncio
async def test_validator_crud_operations_with_orm(
    eth2_repository: Eth2Repository,
):
    """Test CRUD operations using ORM."""
    # Create validator
    validator = ValidatorDetails(
        validator_index=12345,
        public_key=Eth2PubKey('0x' + 'a' * 96),
        ownership_proportion=ONE,
        withdrawal_address=ChecksumEvmAddress('0x' + '1' * 40),
        activation_timestamp=Timestamp(1606824023),
        validator_type=0,
    )
    
    # Test validator doesn't exist
    assert not await eth2_repository.validator_exists(pubkey=validator.public_key, index=None)
    assert not await eth2_repository.validator_exists(pubkey=None, index=validator.validator_index)
    
    # Add validator
    await eth2_repository.add_or_update_validators([validator])
    
    # Test validator exists
    assert await eth2_repository.validator_exists(pubkey=validator.public_key, index=None)
    assert await eth2_repository.validator_exists(pubkey=None, index=validator.validator_index)
    
    # Get validators
    validators = await eth2_repository.get_validators()
    assert len(validators) == 1
    assert validators[0].validator_index == validator.validator_index
    assert validators[0].public_key == validator.public_key
    assert validators[0].ownership_proportion == validator.ownership_proportion
    
    # Edit ownership
    new_ownership = FVal('0.5')
    await eth2_repository.edit_validator_ownership(
        validator_index=validator.validator_index,
        ownership_proportion=new_ownership,
    )
    
    # Verify edit
    validators = await eth2_repository.get_validators()
    assert validators[0].ownership_proportion == new_ownership
    
    # Test index to ownership mapping
    ownership_map = await eth2_repository.get_index_to_ownership()
    assert validator.validator_index in ownership_map
    assert ownership_map[validator.validator_index] == new_ownership
    
    # Delete validator
    await eth2_repository.delete_validators([validator.validator_index])
    
    # Verify deletion
    validators = await eth2_repository.get_validators()
    assert len(validators) == 0
    assert not await eth2_repository.validator_exists(pubkey=validator.public_key, index=None)


@pytest.mark.asyncio
async def test_daily_stats_operations_with_orm(
    eth2_repository: Eth2Repository,
):
    """Test daily stats operations using ORM."""
    # First add a validator
    validator = ValidatorDetails(
        validator_index=54321,
        public_key=Eth2PubKey('0x' + 'b' * 96),
        ownership_proportion=ONE,
        validator_type=0,
    )
    await eth2_repository.add_or_update_validators([validator])
    
    # Add daily stats
    stats = [
        ValidatorDailyStats(
            validator_index=validator.validator_index,
            timestamp=Timestamp(1640000000 + i * 86400),
            pnl=FVal(f'0.0{i+1}'),
        )
        for i in range(5)
    ]
    await eth2_repository.add_validator_daily_stats(stats)
    
    # Get stats
    retrieved_stats = await eth2_repository.get_validator_daily_stats(
        validator_indices=[validator.validator_index]
    )
    assert len(retrieved_stats) == 5
    
    # Add duplicate stats (should be skipped)
    await eth2_repository.add_validator_daily_stats([stats[0]])
    retrieved_stats = await eth2_repository.get_validator_daily_stats(
        validator_indices=[validator.validator_index]
    )
    assert len(retrieved_stats) == 5  # Still 5, not 6
    
    # Test count
    count = await eth2_repository.count_daily_stats()
    assert count == 5
    
    # Test performance stats
    performance = await eth2_repository.get_performance_stats(
        validator_indices=[validator.validator_index]
    )
    assert validator.validator_index in performance
    assert performance[validator.validator_index] == FVal('0.15')  # Sum of 0.01 to 0.05


@pytest.mark.asyncio
async def test_count_operations_with_orm(
    eth2_repository: Eth2Repository,
):
    """Test count operations using ORM."""
    # Initially empty
    assert await eth2_repository.count_validators() == 0
    assert await eth2_repository.count_daily_stats() == 0
    
    # Add validators
    validators = [
        ValidatorDetails(
            validator_index=i,
            public_key=Eth2PubKey(f'0x{str(i).zfill(96)}'),
            ownership_proportion=ONE,
            validator_type=0,
        )
        for i in range(10, 15)
    ]
    await eth2_repository.add_or_update_validators(validators)
    
    # Test count
    assert await eth2_repository.count_validators() == 5
    
    # Add stats for one validator
    stats = [
        ValidatorDailyStats(
            validator_index=10,
            timestamp=Timestamp(1640000000 + i * 86400),
            pnl=FVal('0.01'),
        )
        for i in range(3)
    ]
    await eth2_repository.add_validator_daily_stats(stats)
    
    assert await eth2_repository.count_daily_stats() == 3
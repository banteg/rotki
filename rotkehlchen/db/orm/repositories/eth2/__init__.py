"""ETH2/Beacon chain repositories"""

from .staking_repository import ETH2StakingRepository
from .validator_repository import ETH2ValidatorRepository

__all__ = ['ETH2StakingRepository', 'ETH2ValidatorRepository']

"""Chain configuration registry."""
from typing import TYPE_CHECKING

from rotkehlchen.types import ChainID, SupportedBlockchain

if TYPE_CHECKING:
    from .base import ChainConfig

# Global registry for chain configurations
_CHAIN_CONFIGS: dict[ChainID, 'ChainConfig'] = {}
_BLOCKCHAIN_CONFIGS: dict[SupportedBlockchain, 'ChainConfig'] = {}


def register_chain_config(config: 'ChainConfig') -> None:
    """Register a chain configuration."""
    _CHAIN_CONFIGS[config.chain_id] = config
    _BLOCKCHAIN_CONFIGS[config.blockchain] = config


def get_chain_config(chain_id: ChainID | None = None, blockchain: SupportedBlockchain | None = None) -> 'ChainConfig':
    """Get a chain configuration by chain ID or blockchain type."""
    if chain_id is not None:
        config = _CHAIN_CONFIGS.get(chain_id)
        if config is None:
            raise ValueError(f'No configuration found for chain ID {chain_id}')
        return config
    
    if blockchain is not None:
        config = _BLOCKCHAIN_CONFIGS.get(blockchain)
        if config is None:
            raise ValueError(f'No configuration found for blockchain {blockchain}')
        return config
    
    raise ValueError('Must provide either chain_id or blockchain')


def get_all_chain_configs() -> list['ChainConfig']:
    """Get all registered chain configurations."""
    return list(_CHAIN_CONFIGS.values())
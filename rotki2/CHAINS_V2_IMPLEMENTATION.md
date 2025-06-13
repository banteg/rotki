# Chains V2 Architecture Implementation

This document describes the implementation of the new chain configuration architecture for rotki2, as outlined in CHAINS_V2.md.

## Overview

The new architecture moves from a per-chain package structure to a generic, configuration-driven approach for all EVM-compatible chains. This significantly reduces code duplication and makes adding new chains trivial.

## Key Components

### 1. Protocol Handlers (`rotki2/protocols/`)

Centralized protocol logic that works across all chains:

```python
rotki2/protocols/
├── base.py              # ProtocolHandler base class
├── uniswap/
│   ├── v3.py           # Generic Uniswap V3 handler
│   └── constants.py    # Chain-specific addresses
└── aave/
    ├── v3.py           # Generic Aave V3 handler
    └── constants.py    # Chain-specific addresses
```

### 2. Chain Configuration (`rotki2/chain/evm/configs/`)

Simple configuration files for each chain:

```python
rotki2/chain/evm/configs/
├── base.py         # ChainConfig dataclass
├── registry.py     # Configuration registry
├── ethereum.py     # Ethereum configuration
├── optimism.py     # Optimism configuration
└── arbitrum.py     # Arbitrum configuration
```

### 3. Generic EVM Manager (`rotki2/chain/evm/manager.py`)

A single manager class that handles all EVM chains based on configuration.

## Usage Example

```python
# Get chain configuration
config = get_chain_config(chain_id=ChainID.ETHEREUM)

# Create chain manager
manager = EvmChainManager(
    config=config,
    database=db,
    msg_aggregator=msg_aggregator,
)

# Connect and use
await manager.connect()
balances = await manager.get_protocol_balances(address)
```

## Adding a New Chain

1. Create a configuration file in `rotki2/chain/evm/configs/`:

```python
from rotki2.protocols import aave, uniswap
from .base import ChainConfig
from .registry import register_chain_config

NEW_CHAIN_CONFIG = ChainConfig(
    name='New Chain',
    chain_id=ChainID.NEW_CHAIN,
    blockchain=SupportedBlockchain.NEW_CHAIN,
    inquirer_class=NewChainInquirer,
    native_token=A_NEW_TOKEN,
    supported_protocols=[aave.AaveV3, uniswap.UniswapV3],
    # ... chain-specific constants
)

register_chain_config(NEW_CHAIN_CONFIG)
```

2. Add protocol addresses to the protocol constants files.

3. That's it! The chain is now supported.

## Benefits

- **Reduced Boilerplate**: ~90% less code per chain
- **Centralized Logic**: Protocol updates happen in one place
- **Easy Scaling**: Adding chains is now configuration, not code
- **Better Maintainability**: Clear separation of concerns
- **Type Safety**: Strong typing throughout

## Migration Status

- [x] Base architecture implemented
- [x] Uniswap V3 migrated
- [x] Aave V3 migrated
- [x] Example chains configured (Ethereum, Optimism, Arbitrum)
- [ ] Migrate remaining protocols
- [ ] Update services to use new managers
- [ ] Remove old chain packages
"""Example usage of the new chain configuration architecture."""
import asyncio
from typing import Any

from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotki2.chain.evm.configs.registry import get_chain_config
from rotki2.chain.evm.manager import EvmChainManager


async def example_usage() -> None:
    """Demonstrate how to use the new architecture."""
    # Import chain configurations (this would normally happen at startup)
    import rotki2.chain.evm.configs.arbitrum  # noqa: F401
    import rotki2.chain.evm.configs.ethereum  # noqa: F401
    import rotki2.chain.evm.configs.optimism  # noqa: F401
    
    # Mock dependencies (in real usage these would be proper instances)
    class MockDB:
        """Mock database."""
        pass
    
    class MockMessagesAggregator:
        """Mock message aggregator."""
        def add_message(self, msg: str, message_type: str) -> None:
            print(f"[{message_type}] {msg}")
        
        def add_error(self, msg: str) -> None:
            print(f"[error] {msg}")
    
    db = MockDB()
    msg_aggregator = MockMessagesAggregator()
    
    # Example 1: Get Ethereum configuration and create manager
    eth_config = get_chain_config(chain_id=ChainID.ETHEREUM)
    eth_manager = EvmChainManager(
        config=eth_config,
        database=db,  # type: ignore
        msg_aggregator=msg_aggregator,  # type: ignore
    )
    print(f"Created manager: {eth_manager}")
    print(f"Supported protocols: {[p.get_protocol_name() for p in eth_manager.protocol_handlers]}")
    
    # Example 2: Get Optimism configuration by blockchain type
    opt_config = get_chain_config(blockchain=ChainID.OPTIMISM.to_blockchain())
    opt_manager = EvmChainManager(
        config=opt_config,
        database=db,  # type: ignore
        msg_aggregator=msg_aggregator,  # type: ignore
    )
    print(f"\nCreated manager: {opt_manager}")
    
    # Example 3: Access protocol-specific decoding rules
    for handler in eth_manager.protocol_handlers:
        rules = handler.get_decoding_rules()
        print(f"\n{handler.get_protocol_name()} decoding rules:")
        print(f"  Events: {list(rules.get('events', {}).values())[:2]}...")  # Show first 2
        print(f"  Transactions: {list(rules.get('transactions', {}).keys())}")
    
    # Example 4: Chain-specific addresses are automatically configured
    uniswap_handler = next(
        (h for h in eth_manager.protocol_handlers if h.get_protocol_name() == 'Uniswap V3'),
        None,
    )
    if uniswap_handler:
        print(f"\nUniswap V3 on Ethereum:")
        print(f"  Router: {uniswap_handler.router_address}")
        print(f"  NFT Manager: {uniswap_handler.nft_manager_address}")
    
    # Example 5: Adding a new chain is now just configuration
    print("\nTo add a new chain, simply create a new config file in configs/")
    print("No need to duplicate protocol logic!")


def show_migration_benefits() -> None:
    """Show the benefits of the new architecture."""
    print("\n=== Migration Benefits ===\n")
    
    print("BEFORE (Old Architecture):")
    print("- Each chain has its own package with duplicated files")
    print("- Protocol logic is scattered across chain packages")
    print("- Adding a new chain requires creating ~10 files")
    print("- Updating protocol logic requires changes in N chain packages")
    print("")
    
    print("AFTER (New Architecture):")
    print("- Single configuration file per chain")
    print("- Protocol logic centralized in rotki2/protocols/")
    print("- Adding a new chain = 1 config file")
    print("- Protocol updates happen in one place")
    print("- Automatic registration and discovery")


if __name__ == '__main__':
    print("=== New Chain Configuration Architecture Demo ===\n")
    
    # Run the async example
    asyncio.run(example_usage())
    
    # Show migration benefits
    show_migration_benefits()
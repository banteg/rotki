"""Service for aggregating data across multiple blockchain chains."""
import asyncio
import logging
from collections import defaultdict
from typing import Any

import anyio

from rotki2.common.types import ChecksumEvmAddress
from rotki2.services.chains.ethereum import EthereumService
from rotki2.services.chains.optimism import OptimismService
from rotki2.services.chains.polygon import PolygonService

logger = logging.getLogger(__name__)


# Chain IDs for supported chains
SUPPORTED_CHAIN_IDS = {
    1: "ethereum",
    10: "optimism", 
    137: "polygon",
    # More chains to be added
}


class ChainsAggregatorService:
    """
    Service that aggregates operations across multiple blockchain chains.
    
    This replaces the old ChainsAggregator with a clean async implementation
    that leverages individual chain services.
    """
    
    def __init__(
        self,
        ethereum_service: EthereumService | None = None,
        optimism_service: OptimismService | None = None,
        polygon_service: PolygonService | None = None,
        # Add more chain services as they are implemented
    ) -> None:
        """
        Initialize the aggregator with available chain services.
        
        Args:
            ethereum_service: Ethereum blockchain service
            optimism_service: Optimism L2 service
            polygon_service: Polygon PoS service
        """
        self.chain_services = {}
        
        if ethereum_service:
            self.chain_services[1] = ethereum_service
            self.ethereum_service = ethereum_service
        
        if optimism_service:
            self.chain_services[10] = optimism_service
            self.optimism_service = optimism_service
        
        if polygon_service:
            self.chain_services[137] = polygon_service
            self.polygon_service = polygon_service
        
        logger.info(f"Initialized ChainsAggregatorService with {len(self.chain_services)} chains")
    
    async def query_balances(
        self,
        addresses: dict[int, list[ChecksumEvmAddress]] | None = None,
    ) -> dict[int, dict[ChecksumEvmAddress, dict[str, str]]]:
        """
        Query balances across all chains concurrently.
        
        Args:
            addresses: Optional dict mapping chain_id to list of addresses.
                      If None, queries all tracked addresses.
                      
        Returns:
            Nested dict: chain_id -> address -> {"native": balance, "tokens": {...}}
        """
        if not addresses:
            # In production, would fetch tracked addresses from DB
            addresses = {}
        
        results = {}
        
        # Create tasks for concurrent balance queries
        async with anyio.create_task_group() as tg:
            for chain_id, service in self.chain_services.items():
                if chain_id not in addresses or not addresses[chain_id]:
                    continue
                
                async def query_chain_balances(
                    chain_id: int,
                    service: Any,
                    addrs: list[ChecksumEvmAddress],
                ) -> None:
                    try:
                        chain_results = await service.get_balances_for_addresses(addrs)
                        results[chain_id] = {
                            addr: {"native": balance}
                            for addr, balance in chain_results.items()
                        }
                    except Exception as e:
                        logger.error(f"Failed to query balances for chain {chain_id}: {e}")
                        results[chain_id] = {addr: {"native": "0"} for addr in addrs}
                
                tg.start_soon(
                    query_chain_balances,
                    chain_id,
                    service,
                    addresses[chain_id],
                )
        
        return results
    
    async def get_all_balances(
        self,
        address: ChecksumEvmAddress,
    ) -> dict[str, dict[str, str]]:
        """
        Get all balances for a single address across all chains.
        
        Args:
            address: Address to query
            
        Returns:
            Dict mapping chain name to balances
        """
        addresses = {
            chain_id: [address]
            for chain_id in self.chain_services.keys()
        }
        
        raw_results = await self.query_balances(addresses)
        
        # Transform to chain name mapping
        results = {}
        for chain_id, balances in raw_results.items():
            chain_name = SUPPORTED_CHAIN_IDS.get(chain_id, f"chain_{chain_id}")
            if address in balances:
                results[chain_name] = balances[address]
        
        return results
    
    async def get_transaction_history(
        self,
        address: ChecksumEvmAddress,
        chain_id: int | None = None,
        from_block: int | None = None,
        to_block: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get transaction history for an address.
        
        Args:
            address: Address to query
            chain_id: Optional specific chain (queries all if None)
            from_block: Starting block
            to_block: Ending block
            limit: Max transactions per chain
            
        Returns:
            List of transactions with chain information
        """
        transactions = []
        
        # Determine which chains to query
        chains_to_query = (
            [chain_id] if chain_id and chain_id in self.chain_services
            else list(self.chain_services.keys())
        )
        
        # Query each chain
        async with anyio.create_task_group() as tg:
            for cid in chains_to_query:
                service = self.chain_services[cid]
                
                async def get_chain_txs(chain_id: int, svc: Any) -> None:
                    try:
                        # This assumes services have a method to get transactions
                        # In practice, this would use the repository
                        chain_name = SUPPORTED_CHAIN_IDS.get(chain_id, f"chain_{chain_id}")
                        
                        # Placeholder - real implementation would query the repository
                        logger.info(
                            f"Getting transactions for {address} on {chain_name}"
                        )
                        
                        # Add chain info to each transaction
                        # txs = await svc.get_transactions_for_address(...)
                        # for tx in txs:
                        #     tx["chain_id"] = chain_id
                        #     tx["chain_name"] = chain_name
                        #     transactions.append(tx)
                        
                    except Exception as e:
                        logger.error(f"Failed to get txs for chain {chain_id}: {e}")
                
                tg.start_soon(get_chain_txs, cid, service)
        
        # Sort by timestamp/block number
        transactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        return transactions[:limit]
    
    async def add_blockchain_accounts(
        self,
        accounts: dict[int, list[ChecksumEvmAddress]],
    ) -> dict[str, Any]:
        """
        Add blockchain accounts to track across chains.
        
        Args:
            accounts: Dict mapping chain_id to list of addresses
            
        Returns:
            Result with added accounts and any errors
        """
        results = {
            "added": defaultdict(list),
            "errors": defaultdict(list),
        }
        
        for chain_id, addresses in accounts.items():
            if chain_id not in self.chain_services:
                for addr in addresses:
                    results["errors"][chain_id].append({
                        "address": addr,
                        "error": f"Chain {chain_id} not supported",
                    })
                continue
            
            chain_name = SUPPORTED_CHAIN_IDS.get(chain_id, f"chain_{chain_id}")
            
            for address in addresses:
                try:
                    # In production, would save to database
                    # For now, just validate the address format
                    if not address.startswith("0x") or len(address) != 42:
                        raise ValueError("Invalid address format")
                    
                    results["added"][chain_name].append(address)
                    
                except Exception as e:
                    results["errors"][chain_name].append({
                        "address": address,
                        "error": str(e),
                    })
        
        return dict(results)
    
    async def remove_blockchain_accounts(
        self,
        accounts: dict[int, list[ChecksumEvmAddress]],
    ) -> dict[str, Any]:
        """
        Remove blockchain accounts from tracking.
        
        Args:
            accounts: Dict mapping chain_id to list of addresses
            
        Returns:
            Result with removed accounts and any errors
        """
        results = {
            "removed": defaultdict(list),
            "errors": defaultdict(list),
        }
        
        for chain_id, addresses in accounts.items():
            chain_name = SUPPORTED_CHAIN_IDS.get(chain_id, f"chain_{chain_id}")
            
            for address in addresses:
                try:
                    # In production, would remove from database
                    results["removed"][chain_name].append(address)
                    
                except Exception as e:
                    results["errors"][chain_name].append({
                        "address": address,
                        "error": str(e),
                    })
        
        return dict(results)
    
    async def decode_transactions(
        self,
        tx_hashes: dict[int, list[str]],
    ) -> dict[int, list[dict[str, Any]]]:
        """
        Decode transactions across multiple chains.
        
        Args:
            tx_hashes: Dict mapping chain_id to list of tx hashes
            
        Returns:
            Dict mapping chain_id to decoded transactions
        """
        results = {}
        
        async with anyio.create_task_group() as tg:
            for chain_id, hashes in tx_hashes.items():
                if chain_id not in self.chain_services:
                    continue
                
                service = self.chain_services[chain_id]
                if not hasattr(service, "decode_transaction"):
                    continue
                
                async def decode_chain_txs(cid: int, svc: Any, txs: list[str]) -> None:
                    chain_results = []
                    for tx_hash in txs:
                        try:
                            decoded = await svc.decode_transaction(tx_hash)
                            chain_results.append(decoded)
                        except Exception as e:
                            logger.error(f"Failed to decode {tx_hash} on chain {cid}: {e}")
                            chain_results.append({
                                "tx_hash": tx_hash,
                                "decoded": False,
                                "error": str(e),
                            })
                    
                    results[cid] = chain_results
                
                tg.start_soon(decode_chain_txs, chain_id, service, hashes)
        
        return results
    
    def get_supported_chains(self) -> dict[int, str]:
        """
        Get list of supported chains.
        
        Returns:
            Dict mapping chain_id to chain name
        """
        return {
            chain_id: SUPPORTED_CHAIN_IDS.get(chain_id, f"chain_{chain_id}")
            for chain_id in self.chain_services.keys()
        }
    
    async def get_ens_names(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, str | None]:
        """
        Get ENS names for addresses (Ethereum-specific).
        
        Args:
            addresses: List of addresses to lookup
            
        Returns:
            Mapping of addresses to ENS names
        """
        if not self.ethereum_service:
            return {addr: None for addr in addresses}
        
        return await self.ethereum_service.ens_reverse_lookup(addresses)
    
    async def get_eth2_deposits(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, list[dict[str, Any]]]:
        """
        Get ETH2 deposits for addresses (Ethereum-specific).
        
        Args:
            addresses: List of addresses to check
            
        Returns:
            Mapping of addresses to their ETH2 deposits
        """
        if not self.ethereum_service:
            return {}
        
        results = {}
        
        async with anyio.create_task_group() as tg:
            for address in addresses:
                async def get_deposits(addr: ChecksumEvmAddress) -> None:
                    try:
                        deposits = await self.ethereum_service.get_eth2_deposits(addr)
                        results[addr] = deposits
                    except Exception as e:
                        logger.error(f"Failed to get ETH2 deposits for {addr}: {e}")
                        results[addr] = []
                
                tg.start_soon(get_deposits, address)
        
        return results
    
    async def close(self) -> None:
        """Close all chain services and cleanup resources."""
        # In production, would close node connections, cleanup resources
        logger.info("Closing ChainsAggregatorService")
    
    def __repr__(self) -> str:
        """String representation."""
        chains = ", ".join(
            SUPPORTED_CHAIN_IDS.get(cid, f"chain_{cid}")
            for cid in self.chain_services.keys()
        )
        return f"<ChainsAggregatorService(chains=[{chains}])>"
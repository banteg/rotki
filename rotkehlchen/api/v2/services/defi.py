"""DeFi service for managing DeFi protocol operations"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.defi.protocols import DEFI_PROTOCOLS
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.ethereum.interfaces.modules import EthereumModule
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.premium.premium import Premium


class DeFiService:
    """Service for DeFi protocol operations"""

    def __init__(
        self,
        db_connection: DBConnection,
        chains_aggregator: 'ChainsAggregator | None' = None,
        premium: 'Premium | None' = None,
    ):
        self.db_connection = db_connection
        self.chains_aggregator = chains_aggregator
        self.premium = premium

    def get_defi_metadata(self) -> list[dict[str, str]]:
        """Get metadata for all supported DeFi protocols"""
        protocols = []
        for identifier, protocol in DEFI_PROTOCOLS.items():
            protocols.append({
                'identifier': identifier,
                'name': protocol.name,
                'description': protocol.description,
                'url': protocol.url,
                'version': protocol.version,
                'icon': f'defi/{identifier}.svg',  # Assuming icon path pattern
            })
        
        return sorted(protocols, key=lambda x: x['name'])

    def get_module_balances(
        self,
        blockchain: str,
        module_name: str,
        addresses: list[ChecksumEvmAddress] | None = None,
        version: int | None = None,
    ) -> dict[str, Any]:
        """Get balances for a specific DeFi module"""
        # Validate blockchain
        try:
            blockchain_enum = SupportedBlockchain(blockchain.upper())
        except ValueError as e:
            raise InputError(f'Unsupported blockchain: {blockchain}') from e

        if blockchain_enum != SupportedBlockchain.ETHEREUM:
            raise InputError(f'DeFi modules are only supported on Ethereum, not {blockchain}')

        # Get the module
        module = self._get_module(module_name)
        if module is None:
            raise InputError(f'Module {module_name} not found')

        # If no addresses provided, use all tracked addresses
        if addresses is None:
            addresses = self._get_tracked_addresses()

        try:
            # Call the module's get_balances method
            if version is not None and hasattr(module, f'get_balances_v{version}'):
                # Version-specific method
                method = getattr(module, f'get_balances_v{version}')
                balances = method(addresses)
            elif hasattr(module, 'get_balances'):
                # Generic get_balances
                if version is not None:
                    # Some modules accept version as parameter
                    balances = module.get_balances(addresses, version=version)
                else:
                    balances = module.get_balances(addresses)
            else:
                raise InputError(f'Module {module_name} does not support balance queries')

            return self._serialize_module_balances(balances, module_name)

        except RemoteError as e:
            raise InputError(f'Failed to query {module_name} balances: {str(e)}') from e

    def get_liquity_balances(self, addresses: list[ChecksumEvmAddress] | None = None) -> dict[str, Any]:
        """Get Liquity protocol balances (troves)"""
        module = self._get_module('liquity')
        if module is None:
            raise InputError('Liquity module not found')

        if addresses is None:
            addresses = self._get_tracked_addresses()

        try:
            balances = module.get_balances(addresses)
            return {
                'troves': balances.get('troves', {}),
                'total_collateral_eth': str(balances.get('total_collateral_eth', '0')),
                'total_debt_lusd': str(balances.get('total_debt_lusd', '0')),
            }
        except Exception as e:
            raise InputError(f'Failed to query Liquity balances: {str(e)}') from e

    def get_liquity_staking(self, addresses: list[ChecksumEvmAddress] | None = None) -> dict[str, Any]:
        """Get Liquity staking positions"""
        module = self._get_module('liquity')
        if module is None:
            raise InputError('Liquity module not found')

        if addresses is None:
            addresses = self._get_tracked_addresses()

        try:
            staking = module.get_staking(addresses)
            return self._serialize_liquity_staking(staking)
        except Exception as e:
            raise InputError(f'Failed to query Liquity staking: {str(e)}') from e

    def get_liquity_pool(self, addresses: list[ChecksumEvmAddress] | None = None) -> dict[str, Any]:
        """Get Liquity stability pool positions"""
        module = self._get_module('liquity')
        if module is None:
            raise InputError('Liquity module not found')

        if addresses is None:
            addresses = self._get_tracked_addresses()

        try:
            pool = module.get_stability_pool_positions(addresses)
            return self._serialize_liquity_pool(pool)
        except Exception as e:
            raise InputError(f'Failed to query Liquity pool: {str(e)}') from e

    def get_liquity_stats(self) -> dict[str, Any]:
        """Get Liquity protocol statistics"""
        module = self._get_module('liquity')
        if module is None:
            raise InputError('Liquity module not found')

        try:
            stats = module.get_stats()
            return {
                'total_collateral_ratio': str(stats.get('total_collateral_ratio', '0')),
                'recovery_mode': stats.get('recovery_mode', False),
                'last_fee_operation_time': stats.get('last_fee_operation_time', 0),
                'borrowing_fee_floor': str(stats.get('borrowing_fee_floor', '0')),
                'max_borrowing_fee': str(stats.get('max_borrowing_fee', '0')),
                'redemption_fee_floor': str(stats.get('redemption_fee_floor', '0')),
                'total_stakes_snapshot': str(stats.get('total_stakes_snapshot', '0')),
            }
        except Exception as e:
            raise InputError(f'Failed to query Liquity stats: {str(e)}') from e

    def get_module_stats(self, module_name: str) -> dict[str, Any]:
        """Get statistics for a specific module"""
        module = self._get_module(module_name)
        if module is None:
            raise InputError(f'Module {module_name} not found')

        if not hasattr(module, 'get_stats'):
            raise InputError(f'Module {module_name} does not support statistics')

        try:
            stats = module.get_stats()
            return stats
        except Exception as e:
            raise InputError(f'Failed to query {module_name} stats: {str(e)}') from e

    def _get_module(self, module_name: str) -> 'EthereumModule | None':
        """Get an Ethereum module by name"""
        if self.chains_aggregator is None:
            return None

        eth_manager: 'EthereumManager' = self.chains_aggregator.get_chain_manager('ETH')
        if eth_manager is None:
            return None

        return eth_manager.node_inquirer.get_module(module_name)

    def _get_tracked_addresses(self) -> list[ChecksumEvmAddress]:
        """Get all tracked Ethereum addresses"""
        if self.chains_aggregator is None:
            return []

        eth_accounts = self.chains_aggregator.accounts.eth
        return list(eth_accounts) if eth_accounts else []

    def _serialize_module_balances(self, balances: Any, module_name: str) -> dict[str, Any]:
        """Serialize module balances to API format"""
        # Handle different balance formats from different modules
        if isinstance(balances, dict):
            # Most modules return dict with addresses as keys
            serialized = {}
            for key, value in balances.items():
                if hasattr(value, 'serialize'):
                    serialized[key] = value.serialize()
                elif isinstance(value, dict):
                    serialized[key] = value
                else:
                    # Convert to dict representation
                    serialized[key] = str(value)
            
            return {
                'module': module_name,
                'balances': serialized,
            }
        
        # Some modules might return lists or other formats
        return {
            'module': module_name,
            'balances': balances,
        }

    def _serialize_liquity_staking(self, staking: dict[str, Any]) -> dict[str, Any]:
        """Serialize Liquity staking data"""
        return {
            'staking': {
                addr: {
                    'staked_lqty': str(data.get('staked_lqty', '0')),
                    'staked_usd_value': str(data.get('staked_usd_value', '0')),
                    'pending_eth': str(data.get('pending_eth', '0')),
                    'pending_lusd': str(data.get('pending_lusd', '0')),
                }
                for addr, data in staking.items()
            },
        }

    def _serialize_liquity_pool(self, pool: dict[str, Any]) -> dict[str, Any]:
        """Serialize Liquity stability pool data"""
        return {
            'stability_pool': {
                addr: {
                    'deposited_lusd': str(data.get('deposited_lusd', '0')),
                    'deposited_usd_value': str(data.get('deposited_usd_value', '0')),
                    'pending_eth': str(data.get('pending_eth', '0')),
                    'pending_lqty': str(data.get('pending_lqty', '0')),
                }
                for addr, data in pool.items()
            },
        }
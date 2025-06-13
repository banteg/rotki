"""Async EVM proxies inquirer for handling proxy contracts"""
import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.contracts import EvmContract

    from rotki2.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = logging.getLogger(__name__)


class EvmProxiesInquirer:
    """Handles queries for EVM proxy contracts like DSProxy"""

    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            dsproxy_registry: 'EvmContract',
    ) -> None:
        self.node_inquirer = node_inquirer
        self.dsproxy_registry = dsproxy_registry

    async def get_account_proxy(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:
        """Query DSProxy registry to get proxy address for given address

        Returns None if no proxy exists for the address
        """
        result = await self.dsproxy_registry.call(
            node_inquirer=self.node_inquirer,
            method_name='proxies',
            arguments=[address],
        )

        if result == ZERO_ADDRESS:
            return None

        return hex_or_bytes_to_address(result)

    async def get_proxy_owner(self, proxy_address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:
        """Get the owner of a DSProxy contract

        Returns None if the proxy doesn't exist or has no owner
        """
        # DSProxy contracts have an owner() method
        code = await self.node_inquirer.get_code(proxy_address)
        if code == '0x':
            return None  # Not a contract

        # Try to call owner() method on the proxy
        try:
            # DSProxy owner method selector: 0x8da5cb5b
            result = await self.node_inquirer._query(
                method=self.node_inquirer._call_contract,
                call_order=self.node_inquirer.default_call_order(),
                contract_address=proxy_address,
                abi=[{
                    'constant': True,
                    'inputs': [],
                    'name': 'owner',
                    'outputs': [{'name': '', 'type': 'address'}],
                    'type': 'function',
                }],
                method_name='owner',
            )
            return hex_or_bytes_to_address(result)
        except Exception:
            # If owner() method doesn't exist or fails, return None
            return None

    async def get_multiple_proxies(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, ChecksumEvmAddress]:
        """Get proxy addresses for multiple accounts efficiently using multicall

        Returns a dictionary mapping original addresses to their proxy addresses
        Only includes entries where a proxy exists (non-zero address)
        """
        if not addresses:
            return {}

        calls = [
            (
                self.dsproxy_registry.address,
                self.dsproxy_registry.encode(method_name='proxies', arguments=[address]),
            )
            for address in addresses
        ]

        try:
            results = await self.node_inquirer.multicall(calls=calls)
        except Exception as e:
            log.error(f'Failed to query multiple proxies: {e}')
            return {}

        proxies = {}
        for idx, result in enumerate(results):
            if len(result) >= 32:  # Ensure we have enough data
                proxy_address = hex_or_bytes_to_address(result[-20:])  # Last 20 bytes
                if proxy_address != ZERO_ADDRESS:
                    proxies[addresses[idx]] = proxy_address

        return proxies
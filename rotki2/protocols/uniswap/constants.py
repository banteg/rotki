"""Uniswap protocol constants for all chains."""
from rotkehlchen.types import ChainID, ChecksumEvmAddress

# Uniswap V3 Router addresses per chain
UNISWAP_V3_ROUTERS: dict[ChainID, ChecksumEvmAddress] = {
    ChainID.ETHEREUM: ChecksumEvmAddress('0xE592427A0AEce92De3Edee1F18E0157C05861564'),
    ChainID.ARBITRUM_ONE: ChecksumEvmAddress('0xE592427A0AEce92De3Edee1F18E0157C05861564'),
    ChainID.OPTIMISM: ChecksumEvmAddress('0xE592427A0AEce92De3Edee1F18E0157C05861564'),
    ChainID.POLYGON_POS: ChecksumEvmAddress('0xE592427A0AEce92De3Edee1F18E0157C05861564'),
    ChainID.BASE: ChecksumEvmAddress('0x2626664c2603336E57B271c5C0b26F421741e481'),
    ChainID.BINANCE_SC: ChecksumEvmAddress('0xB971eF87ede563556b2ED4b1C0b0019111Dd85d2'),
}

# Uniswap V3 NFT Position Manager addresses per chain
UNISWAP_V3_NFT_MANAGERS: dict[ChainID, ChecksumEvmAddress] = {
    ChainID.ETHEREUM: ChecksumEvmAddress('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
    ChainID.ARBITRUM_ONE: ChecksumEvmAddress('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
    ChainID.OPTIMISM: ChecksumEvmAddress('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
    ChainID.POLYGON_POS: ChecksumEvmAddress('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
    ChainID.BASE: ChecksumEvmAddress('0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1'),
    ChainID.BINANCE_SC: ChecksumEvmAddress('0x7b8A01B39D58278b5DE7e48c8449c9f4F5170613'),
}

# Uniswap V3 Universal Router addresses per chain
UNISWAP_UNIVERSAL_ROUTERS: dict[ChainID, ChecksumEvmAddress] = {
    ChainID.ETHEREUM: ChecksumEvmAddress('0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD'),
    ChainID.ARBITRUM_ONE: ChecksumEvmAddress('0x5E325eDA8064b456f4781070C0738d849c824258'),
    ChainID.OPTIMISM: ChecksumEvmAddress('0xCb1355ff08Ab38bBCE60111F1bb2B784bE25D7e8'),
    ChainID.POLYGON_POS: ChecksumEvmAddress('0xec7BE89e9d109e7e3Fec59c222CF297125FEFda2'),
    ChainID.BASE: ChecksumEvmAddress('0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD'),
    ChainID.BINANCE_SC: ChecksumEvmAddress('0x4Dae2f939ACf50408e13d58534Ff8c2776d45265'),
}

# Event signatures
SWAP_SIGNATURE = b'\xc4 \xdf\xba\xda\xf8\xdc\xf6\xeb \xb5\xfa\xbfF%\x99\x11\xdc\x11~\x04\xcc\xfdN\xf5\xda\\Hl}\xef'  # noqa: E501
INCREASE_LIQUIDITY_SIGNATURE = b'0\xad\xd4\xd1\xdb\xa5n\xb6\x17v\xa5\xd1s}\x9e\xfb>\x8e\x87:\xdd\x9f\xddq6\xa5\x85\x06\x14Z\xd1='  # noqa: E501
COLLECT_LIQUIDITY_SIGNATURE = b'@\xd3\xec3\x06\x9b\xadL+\xcc\xd6\xec\x95\x94f\xefFF\xc8vy}\x8aQ&o\x91\x84\x96\x12`?'  # noqa: E501

# Fee tiers in basis points
UNISWAP_V3_FEE_TIERS = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
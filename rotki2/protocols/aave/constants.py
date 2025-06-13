"""Aave protocol constants for all chains."""
from rotkehlchen.types import ChainID, ChecksumEvmAddress

# Aave V3 Pool addresses per chain
AAVE_V3_POOLS: dict[ChainID, list[ChecksumEvmAddress]] = {
    ChainID.ETHEREUM: [
        ChecksumEvmAddress('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),  # Main pool
        ChecksumEvmAddress('0x7937D4799803FbBe595ed57278Bc4cA21f3bFfCB'),  # Lido pool
        ChecksumEvmAddress('0x0B925eD163218f6662a35e0f0371Ac234f9E9371'),  # EtherFi pool
    ],
    ChainID.ARBITRUM_ONE: [
        ChecksumEvmAddress('0x794a61358D6845594F94dc1DB02A252b5b4814aD'),
    ],
    ChainID.OPTIMISM: [
        ChecksumEvmAddress('0x794a61358D6845594F94dc1DB02A252b5b4814aD'),
    ],
    ChainID.POLYGON_POS: [
        ChecksumEvmAddress('0x794a61358D6845594F94dc1DB02A252b5b4814aD'),
    ],
    ChainID.BASE: [
        ChecksumEvmAddress('0xA238Dd80C259a72e81d7e4664a9801593F98d1c5'),
    ],
    ChainID.GNOSIS: [
        ChecksumEvmAddress('0xb50201558B00496A145fE76f7424749556E326D8'),
    ],
    ChainID.AVALANCHE: [
        ChecksumEvmAddress('0x794a61358D6845594F94dc1DB02A252b5b4814aD'),
    ],
    ChainID.BINANCE_SC: [
        ChecksumEvmAddress('0x6807dc923806fE8Fd134338EABCA509979a7e0cB'),
    ],
    ChainID.SCROLL: [
        ChecksumEvmAddress('0x11fCfe756c05AD438e312a7fd934381537D3cFfe'),
    ],
}

# Aave V3 Native Gateway addresses per chain (for ETH deposits/withdrawals)
AAVE_V3_NATIVE_GATEWAYS: dict[ChainID, ChecksumEvmAddress] = {
    ChainID.ETHEREUM: ChecksumEvmAddress('0x893411580e590D62dDBca8a703d61Cc4A8c7b2b9'),
    ChainID.ARBITRUM_ONE: ChecksumEvmAddress('0xecD4bd3121F9FD604ffaC631bF6d41ec12f1fafb'),
    ChainID.OPTIMISM: ChecksumEvmAddress('0x76D3030728e52DEB8848d5613aBaDE88441cbc59'),
    ChainID.POLYGON_POS: ChecksumEvmAddress('0xA6FA05ac5D2eC71A9fB6033A8525080304AA7F45'),
    ChainID.BASE: ChecksumEvmAddress('0x18CD499E3d7ed42FEbA981ac9236A278E4Cdc2ee'),
    ChainID.GNOSIS: ChecksumEvmAddress('0xfE76366A986B72c3f2923e05E6ba07b7de5401e4'),
    ChainID.AVALANCHE: ChecksumEvmAddress('0xD7f71A58f763e42fCA79D3BEEDb5DB0b7e11BbBa'),
    ChainID.BINANCE_SC: ChecksumEvmAddress('0x3C922F84A0c58779C300B2B5DF39a385e7bC5788'),
    ChainID.SCROLL: ChecksumEvmAddress('0xFF75A4B698E3Ec95E608ac0f22A03B8368E05F5D'),
}

# Aave V3 Incentives Controller addresses per chain
AAVE_V3_INCENTIVES_CONTROLLERS: dict[ChainID, ChecksumEvmAddress] = {
    ChainID.ETHEREUM: ChecksumEvmAddress('0x8164Cc65827dcFe994AB23944CBC90e0aa80bFcb'),
    ChainID.ARBITRUM_ONE: ChecksumEvmAddress('0x929EC64c34a17401F460460D4B9390518E5B473e'),
    ChainID.OPTIMISM: ChecksumEvmAddress('0x929EC64c34a17401F460460D4B9390518E5B473e'),
    ChainID.POLYGON_POS: ChecksumEvmAddress('0x929EC64c34a17401F460460D4B9390518E5B473e'),
    ChainID.BASE: ChecksumEvmAddress('0xf9cc4F0D883F1a1eb2c253bdb46c254Ca51E1F44'),
    ChainID.GNOSIS: ChecksumEvmAddress('0xaEf0D72AC36b02Cdc8F5f96aab8F901De090F9Dc'),
    ChainID.AVALANCHE: ChecksumEvmAddress('0x929EC64c34a17401F460460D4B9390518E5B473e'),
    ChainID.BINANCE_SC: ChecksumEvmAddress('0xC206C2764A9dBF27d599613b8F9A63ACd1160ab4'),
    ChainID.SCROLL: ChecksumEvmAddress('0x8Dc3e20Eceb6F36deD116a60CCD345beAc23C9b8'),
}

# Event signatures
DEPOSIT_SIGNATURE = b'J\xa2S\xd4\xd7L\xb5P\xaa\xfae\x81\xeaq\x95\xe0\x08z\xec\xa9]\xb2\x99P\xcan\x80F\xb7\xc9q\xb0'  # noqa: E501
BORROW_SIGNATURE = b'\xb3\xd0\x84\xa8\\\x95\xda=\xc3\xec\xb5\t\xfaQt[\xf5\xd9\x85\x0e\xad@x\x16\xdfM!\xc0\x9d\x82\x1a\xb7'  # noqa: E501
REPAY_SIGNATURE = b'\xa54\xb2Q\x17\xb0\x1c\xf2\xbf\x98\x95`bO\xf0\xda\xaa?\xdd\xb7wdA\xbaw\xe3\xa4\\>\x05\xf1B'  # noqa: E501
BURN_SIGNATURE = b'L\x99\xc2d\x15\xf2gNP\xec\xb6\x91)\xae\xf8\xb2M\xc6I\xd9\x10\x0c-7\xfa\xa8.\xde\xae\xea\xcd\xca'  # noqa: E501
REWARDS_CLAIMED_SIGNATURE = b'1\x19\xb3\xf9h\x02M\xfa9n$\xbf\x8fU%\x07k\x94H\x87[\xd8>\x96\xd5\xe4\x11\xf9D\xf0\xec\xb8'  # noqa: E501
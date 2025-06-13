"""Types for L2 chains with L1 fees"""
from typing import Union

from rotkehlchen.types import SupportedBlockchain

# Type for supported L2 chains with L1 fees
SupportedL2WithL1FeesType = Union[
    SupportedBlockchain.OPTIMISM,
    SupportedBlockchain.BASE,
    SupportedBlockchain.ARBITRUM_ONE,
    SupportedBlockchain.SCROLL,
]
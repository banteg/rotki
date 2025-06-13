"""Airdrops service for managing airdrop information"""
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class AirdropsService:
    """Service for managing airdrop metadata"""
    
    def __init__(self) -> None:
        # Simulated airdrop data
        self._airdrops = [
            {
                'protocol': 'uniswap',
                'name': 'Uniswap',
                'token': 'UNI',
                'icon': 'uniswap.png',
                'cutoff_date': 1600041600,  # Sept 1, 2020
                'claim_start': 1600387200,  # Sept 18, 2020
                'claim_end': None,  # No end date
                'amount_per_user': '400',
                'requirements': 'Used Uniswap V1 or V2 before Sept 1, 2020',
            },
            {
                'protocol': '1inch',
                'name': '1inch',
                'token': '1INCH',
                'icon': '1inch.png',
                'cutoff_date': 1608595200,  # Dec 24, 2020
                'claim_start': 1608768000,  # Dec 24, 2020
                'claim_end': None,
                'amount_per_user': 'Variable',
                'requirements': 'Early users and liquidity providers',
            },
            {
                'protocol': 'gitcoin',
                'name': 'Gitcoin',
                'token': 'GTC',
                'icon': 'gitcoin.png',
                'cutoff_date': 1622505600,  # May 25, 2021
                'claim_start': 1622505600,  # May 27, 2021
                'claim_end': None,
                'amount_per_user': 'Variable',
                'requirements': 'Contributors and funders on Gitcoin',
            },
            {
                'protocol': 'ens',
                'name': 'Ethereum Name Service',
                'token': 'ENS',
                'icon': 'ens.png',
                'cutoff_date': 1635724800,  # Oct 31, 2021
                'claim_start': 1636416000,  # Nov 8, 2021
                'claim_end': 1651881600,  # May 4, 2022
                'amount_per_user': 'Variable',
                'requirements': 'ENS domain holders',
            },
        ]
    
    def get_all_airdrop_metadata(self) -> list[dict[str, Any]]:
        """Get metadata for all supported airdrops"""
        return self._airdrops
    
    def get_airdrop_by_protocol(self, protocol: str) -> dict[str, Any] | None:
        """Get airdrop metadata by protocol name"""
        for airdrop in self._airdrops:
            if airdrop['protocol'] == protocol.lower():
                return airdrop
        return None
    
    def check_airdrop_eligibility(self, protocol: str, address: str) -> dict[str, Any]:
        """Check if an address is eligible for an airdrop"""
        # Would actually check eligibility
        airdrop = self.get_airdrop_by_protocol(protocol)
        
        if not airdrop:
            return {
                'eligible': False,
                'reason': 'Unknown airdrop protocol',
            }
        
        # Simulated eligibility check
        return {
            'eligible': True,
            'protocol': protocol,
            'amount': airdrop['amount_per_user'],
            'token': airdrop['token'],
            'claim_deadline': airdrop.get('claim_end'),
        }
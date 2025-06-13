"""Locations service for managing location data"""

from sqlmodel import Session, select

from rotki2.api.v2.repositories.blockchain_account import BlockchainAccountRepository
from rotki2.db.models.user.accounts import BlockchainAccount, UserCredentials
from rotkehlchen.types import Location


class LocationsService:
    """Service for managing locations"""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        if session:
            self.blockchain_repo = BlockchainAccountRepository(session)

    def get_all_locations(self) -> list[str]:
        """Get all supported locations"""
        return [loc.value for loc in Location]

    def get_associated_locations(self) -> dict[str, list[str]]:
        """Get locations with associated data"""
        if not self.session:
            # Return empty if no session
            return {
                'blockchains': [],
                'exchanges': [],
                'other': [],
            }

        # Get blockchains with accounts
        blockchain_query = select(BlockchainAccount.blockchain).distinct()
        blockchains = list(self.session.exec(blockchain_query).all())

        # Get exchanges with credentials
        exchange_query = select(UserCredentials.location).distinct()
        exchanges = list(self.session.exec(exchange_query).all())

        # Combine and categorize
        associated = {
            'blockchains': blockchains,
            'exchanges': exchanges,
            'other': [],  # Other locations like banks, etc.
        }

        return associated

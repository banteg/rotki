"""ENS repository for v2 API.

Handles all ENS-related database operations.
"""

from sqlmodel import Session, select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.user.ens import ENSMapping
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import ChecksumEvmAddress, EnsMapping, Timestamp
from rotkehlchen.utils.misc import ts_now


class ENSRepository(BaseRepository[ENSMapping]):
    """Repository for ENS mappings."""

    def __init__(self, session: Session):
        super().__init__(session, ENSMapping)

    def add_ens_mapping(
        self,
        address: ChecksumEvmAddress,
        name: str | None,
        now: Timestamp | None = None,
    ) -> ENSMapping:
        """Add or update an ENS mapping for an address.
        
        If the name is None then it sets it as an empty name to the DB, signifying we checked it
        If the mapping already exists, but name is updated then we update the name + time
        """
        if now is None:
            now = ts_now()

        # Check if mapping exists
        existing = self.session.get(ENSMapping, address)

        if existing:
            # Update existing mapping
            existing.ens_name = name
            existing.last_update = now
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            # Create new mapping
            mapping = ENSMapping(
                address=address,
                ens_name=name,
                last_update=now,
                last_avatar_update=0,
            )
            return self.create(mapping)

    def get_reverse_ens(
        self,
        addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, EnsMapping | Timestamp]:
        """Returns a mapping of addresses to ens mappings if found in the DB.
        
        - If the address has a name mapping in the DB it is returned as part of the dict
        - If the address maps to None in the DB then address maps to last update in return dict
        - If address is not found in the DB it's not in the result
        """
        if not addresses:
            return {}

        statement = select(ENSMapping).where(ENSMapping.address.in_(addresses))
        results = self.session.exec(statement)

        output = {}
        for mapping in results:
            address = ChecksumEvmAddress(mapping.address)
            if mapping.ens_name is None:
                output[address] = Timestamp(mapping.last_update)
            else:
                output[address] = EnsMapping(
                    address=address,
                    name=mapping.ens_name,
                    last_update=Timestamp(mapping.last_update),
                )

        return output

    def get_address_for_name(self, name: str) -> ChecksumEvmAddress | None:
        """Returns the address for the given name if cached."""
        statement = select(ENSMapping).where(ENSMapping.ens_name == name)
        result = self.session.exec(statement).first()

        if result is None:
            return None

        return ChecksumEvmAddress(result.address)

    def update_values(
        self,
        ens_lookup_results: dict[ChecksumEvmAddress, str | None],
        mappings_to_send: dict[ChecksumEvmAddress, str],
    ) -> dict[ChecksumEvmAddress, str]:
        """Update the ENS mapping values in the DB and return updates mappings to return via api."""
        now = ts_now()

        for address, name in ens_lookup_results.items():
            # If name conflicts with existing mapping for another address, remove the old one
            if name is not None:
                existing_with_name = self.session.exec(
                    select(ENSMapping).where(ENSMapping.ens_name == name),
                ).first()

                if existing_with_name and existing_with_name.address != address:
                    self.session.delete(existing_with_name)
                    self.session.commit()

            # Add or update the mapping
            self.add_ens_mapping(address=address, name=name, now=now)

            if name is not None:
                mappings_to_send[address] = name

        return mappings_to_send

    def get_last_avatar_update(self, ens_name: str) -> Timestamp:
        """
        Returns the timestamp when the avatar for the given ens name was updated last time.
        
        May raise:
        - InputError if given `ens_name` is not in `ens_mappings` table
        """
        statement = select(ENSMapping).where(ENSMapping.ens_name == ens_name)
        result = self.session.exec(statement).first()

        if result is None:
            raise InputError(f'ens name {ens_name} is not being tracked')

        return Timestamp(result.last_avatar_update)

    def find_by(self, **kwargs) -> list[ENSMapping]:
        """Find ENS mappings by criteria."""
        statement = select(ENSMapping)

        for key, value in kwargs.items():
            if hasattr(ENSMapping, key):
                statement = statement.where(getattr(ENSMapping, key) == value)

        results = self.session.exec(statement)
        return list(results.all())

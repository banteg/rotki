"""Repository for Bitcoin xpub management"""


from sqlalchemy import select

from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.db.orm.user_db_models import Xpub, XpubMapping
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.types import BTCAddress, SupportedBlockchain


class XpubRepository(BaseRepository[Xpub]):
    """Repository for managing Bitcoin xpubs and their derived addresses"""

    def __init__(self, session):
        super().__init__(session, Xpub)

    def add_xpub(self, xpub_data: XpubData) -> Xpub:
        """Add a new xpub"""
        xpub = Xpub(
            xpub=xpub_data.xpub,
            derivation_path=xpub_data.derivation_path,
            label=xpub_data.label,
            blockchain=xpub_data.blockchain.value,
        )
        return self.add(xpub)

    def get_xpub(
        self,
        xpub: HDKey,
        derivation_path: str,
        blockchain: SupportedBlockchain,
    ) -> Xpub | None:
        """Get a specific xpub"""
        return self.get(
            xpub=xpub,
            derivation_path=derivation_path,
            blockchain=blockchain.value,
        )

    def get_xpubs_by_blockchain(
        self,
        blockchain: SupportedBlockchain,
    ) -> list[Xpub]:
        """Get all xpubs for a blockchain"""
        return self.get_all(blockchain=blockchain.value)

    def delete_xpub(self, xpub_data: XpubData) -> bool:
        """Delete an xpub and all its mappings"""
        return self.delete_by(
            xpub=xpub_data.xpub,
            derivation_path=xpub_data.derivation_path,
            blockchain=xpub_data.blockchain.value,
        ) > 0

    def update_xpub_label(
        self,
        xpub_data: XpubData,
        new_label: str | None,
    ) -> bool:
        """Update the label of an xpub"""
        xpub = self.get_xpub(
            xpub_data.xpub,
            xpub_data.derivation_path,
            xpub_data.blockchain,
        )
        if xpub:
            xpub.label = new_label
            self.update(xpub)
            return True
        return False

    # XpubMapping operations

    def add_xpub_mapping(
        self,
        address: BTCAddress,
        xpub: HDKey,
        derivation_path: str,
        account_index: int,
        derived_index: int,
        blockchain: SupportedBlockchain,
    ) -> XpubMapping:
        """Add a mapping between an address and xpub"""
        mapping = XpubMapping(
            address=address,
            xpub=xpub,
            derivation_path=derivation_path,
            account_index=account_index,
            derived_index=derived_index,
            blockchain=blockchain.value,
        )
        self.session.add(mapping)
        self.session.flush()
        return mapping

    def get_addresses_for_xpub(
        self,
        xpub_data: XpubData,
    ) -> list[XpubMapping]:
        """Get all addresses derived from an xpub"""
        stmt = select(XpubMapping).filter_by(
            xpub=xpub_data.xpub,
            derivation_path=xpub_data.derivation_path,
            blockchain=xpub_data.blockchain.value,
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_xpub_for_address(
        self,
        address: BTCAddress,
        blockchain: SupportedBlockchain,
    ) -> XpubMapping | None:
        """Get xpub mapping for an address"""
        stmt = select(XpubMapping).filter_by(
            address=address,
            blockchain=blockchain.value,
        ).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_last_consecutive_indices(
        self,
        xpub_data: XpubData,
    ) -> tuple[int, int]:
        """Get last consecutive account and derived indices"""
        stmt = select(XpubMapping).filter_by(
            xpub=xpub_data.xpub,
            derivation_path=xpub_data.derivation_path,
            blockchain=xpub_data.blockchain.value,
        ).order_by(
            XpubMapping.account_index,
            XpubMapping.derived_index,
        )

        mappings = self.session.execute(stmt).scalars().all()

        if not mappings:
            return -1, -1

        # Find last consecutive indices
        last_account = -1
        last_derived = -1

        for mapping in mappings:
            if mapping.account_index == last_account + 1:
                last_account = mapping.account_index
                last_derived = mapping.derived_index
            elif mapping.account_index == last_account and mapping.derived_index == last_derived + 1:
                last_derived = mapping.derived_index
            else:
                break

        return last_account, last_derived

    def ensure_xpub_mappings_exist(
        self,
        mappings: list[tuple[BTCAddress, XpubData, int, int]],
    ) -> None:
        """Ensure multiple xpub mappings exist"""
        for address, xpub_data, account_idx, derived_idx in mappings:
            # Check if mapping already exists
            existing = self.get_xpub_for_address(address, xpub_data.blockchain)
            if not existing:
                self.add_xpub_mapping(
                    address=address,
                    xpub=xpub_data.xpub,
                    derivation_path=xpub_data.derivation_path,
                    account_index=account_idx,
                    derived_index=derived_idx,
                    blockchain=xpub_data.blockchain,
                )

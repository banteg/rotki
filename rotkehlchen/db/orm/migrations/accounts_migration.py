"""Migration for blockchain accounts and related data"""

from typing import Any

from sqlalchemy.orm import Session

from rotkehlchen.db.orm.migrations.migrator import BaseMigrationStep
from rotkehlchen.db.orm.models import (
    BlockchainAccount,
    Tag,
    Xpub,
    XpubMapping,
)
from rotkehlchen.db.orm.repositories import (
    BlockchainAccountRepository,
    EvmAccountDetailsRepository,
    TagRepository,
    XpubRepository,
)


class TagsMigration(BaseMigrationStep):
    """Migrate tags table"""

    @property
    def name(self) -> str:
        return 'tags'

    @property
    def description(self) -> str:
        return 'Migrate account tags'

    def migrate(self, old_conn: Any, new_session: Session) -> None:
        """Migrate tags data"""
        tag_repo = TagRepository(new_session)

        # Query old tags
        cursor = old_conn.cursor()
        cursor.execute(
            'SELECT name, description, background_color, foreground_color FROM tags',
        )

        for row in cursor:
            name, description, bg_color, fg_color = row
            tag_repo.add_tag(
                name=name,
                description=description,
                background_color=bg_color,
                foreground_color=fg_color,
            )

        new_session.commit()

    def verify(self, old_conn: Any, new_session: Session) -> bool:
        """Verify tags migration"""
        cursor = old_conn.cursor()
        old_count = cursor.execute('SELECT COUNT(*) FROM tags').fetchone()[0]

        new_count = new_session.query(Tag).count()

        return old_count == new_count


class BlockchainAccountsMigration(BaseMigrationStep):
    """Migrate blockchain accounts"""

    @property
    def name(self) -> str:
        return 'blockchain_accounts'

    @property
    def description(self) -> str:
        return 'Migrate blockchain accounts and addresses'

    def migrate(self, old_conn: Any, new_session: Session) -> None:
        """Migrate blockchain accounts"""
        account_repo = BlockchainAccountRepository(new_session)
        evm_details_repo = EvmAccountDetailsRepository(new_session)

        # Query old accounts
        cursor = old_conn.cursor()
        cursor.execute(
            'SELECT blockchain, account, label FROM blockchain_accounts',
        )

        for row in cursor:
            blockchain, account, label = row
            account_repo.add_account(
                blockchain=blockchain,
                address=account,
                label=label,
            )

        # Migrate EVM account details if exists
        try:
            cursor.execute(
                'SELECT account, tokens_list, time FROM evm_accounts_details',
            )

            for row in cursor:
                account, tokens_list, time = row
                evm_details_repo.set_tokens_list(
                    address=account,
                    tokens=tokens_list.split(',') if tokens_list else [],
                    timestamp=time,
                )
        except Exception:
            # Table might not exist in older versions
            pass

        new_session.commit()

    def verify(self, old_conn: Any, new_session: Session) -> bool:
        """Verify accounts migration"""
        cursor = old_conn.cursor()
        old_count = cursor.execute('SELECT COUNT(*) FROM blockchain_accounts').fetchone()[0]

        new_count = new_session.query(BlockchainAccount).count()

        return old_count == new_count


class XpubsMigration(BaseMigrationStep):
    """Migrate xpubs and mappings"""

    @property
    def name(self) -> str:
        return 'xpubs'

    @property
    def description(self) -> str:
        return 'Migrate extended public keys and mappings'

    def migrate(self, old_conn: Any, new_session: Session) -> None:
        """Migrate xpubs data"""
        xpub_repo = XpubRepository(new_session)

        # Query old xpubs
        cursor = old_conn.cursor()
        cursor.execute(
            'SELECT xpub, derivation_path, label, blockchain FROM xpubs',
        )

        for row in cursor:
            xpub, derivation_path, label, blockchain = row
            xpub_repo.add_xpub(
                xpub=xpub,
                derivation_path=derivation_path,
                label=label,
                blockchain=blockchain,
            )

            # Migrate xpub mappings
            mapping_cursor = old_conn.cursor()
            mapping_cursor.execute(
                'SELECT address, blockchain, derivation_path '
                'FROM xpub_mappings WHERE xpub = ?',
                (xpub,),
            )

            for mapping_row in mapping_cursor:
                address, blockchain, deriv_path = mapping_row
                xpub_repo.add_address_mapping(
                    xpub=xpub,
                    address=address,
                    blockchain=blockchain,
                    derivation_path=deriv_path,
                )

        new_session.commit()

    def verify(self, old_conn: Any, new_session: Session) -> bool:
        """Verify xpubs migration"""
        cursor = old_conn.cursor()
        old_xpub_count = cursor.execute('SELECT COUNT(*) FROM xpubs').fetchone()[0]
        old_mapping_count = cursor.execute('SELECT COUNT(*) FROM xpub_mappings').fetchone()[0]

        new_xpub_count = new_session.query(Xpub).count()
        new_mapping_count = new_session.query(XpubMapping).count()

        return (old_xpub_count == new_xpub_count and
                old_mapping_count == new_mapping_count)

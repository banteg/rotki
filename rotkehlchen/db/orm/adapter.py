"""Adapter layer for transitioning from DBHandler to ORM repositories"""

from pathlib import Path
from typing import Any

from rotkehlchen.db.orm.database import RotkehlchenDatabase
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = RotkehlchenLogsAdapter(__name__)


class DBHandlerAdapter:
    """
    Adapter that provides DBHandler-compatible interface using ORM repositories.

    This allows gradual migration by replacing DBHandler usage with this adapter
    without changing all the calling code at once.
    """

    def __init__(self, db: RotkehlchenDatabase):
        """
        Initialize adapter with ORM database.

        Args:
            db: ORM database instance
        """
        self.db = db
        self.repos = db.repos
        self.user_version = db.get_version()

    # Settings methods

    def get_setting(self, name: str) -> Any:
        """Get a setting value"""
        return self.repos.settings.get_setting(name)

    def set_setting(self, name: str, value: Any) -> None:
        """Set a setting value"""
        self.repos.settings.set_setting(name, value)
        self.db.session_manager.user_session.commit()

    def get_settings(self) -> dict[str, Any]:
        """Get all settings"""
        return self.repos.settings.get_all_settings()

    # Account methods

    def add_blockchain_accounts(
        self,
        blockchain: str,
        accounts: list[str],
    ) -> None:
        """Add blockchain accounts"""
        for account in accounts:
            self.repos.accounts.add_account(
                blockchain=blockchain,
                address=account,
            )
        self.db.session_manager.user_session.commit()

    def remove_blockchain_accounts(
        self,
        blockchain: str,
        accounts: list[str],
    ) -> None:
        """Remove blockchain accounts"""
        for account in accounts:
            self.repos.accounts.delete_account(blockchain, account)
        self.db.session_manager.user_session.commit()

    def get_blockchain_accounts(self) -> dict[str, list[str]]:
        """Get all blockchain accounts grouped by blockchain"""
        accounts = self.repos.accounts.get_all_accounts()
        result = {}

        for account in accounts:
            blockchain = account.blockchain
            if blockchain not in result:
                result[blockchain] = []
            result[blockchain].append(account.account)

        return result

    # Tag methods

    def add_tag(
        self,
        name: str,
        description: str,
        background_color: str,
        foreground_color: str,
    ) -> None:
        """Add a tag"""
        self.repos.tags.add_tag(
            name=name,
            description=description,
            background_color=background_color,
            foreground_color=foreground_color,
        )
        self.db.session_manager.user_session.commit()

    def edit_tag(
        self,
        name: str,
        description: str | None = None,
        background_color: str | None = None,
        foreground_color: str | None = None,
    ) -> None:
        """Edit a tag"""
        self.repos.tags.update_tag(
            name=name,
            description=description,
            background_color=background_color,
            foreground_color=foreground_color,
        )
        self.db.session_manager.user_session.commit()

    def delete_tag(self, name: str) -> None:
        """Delete a tag"""
        self.repos.tags.delete_tag(name)
        self.db.session_manager.user_session.commit()

    def get_tags(self) -> list[dict[str, Any]]:
        """Get all tags"""
        tags = self.repos.tags.get_all_tags()
        return [
            {
                'name': tag.name,
                'description': tag.description,
                'background_color': tag.background_color,
                'foreground_color': tag.foreground_color,
            }
            for tag in tags
        ]

    # Balance methods

    def add_manual_balance(
        self,
        asset: str,
        label: str,
        amount: str,
        location: str,
        tags: list[str] | None = None,
    ) -> int:
        """Add manual balance"""
        balance = self.repos.manual_balances.add_balance(
            asset=asset,
            label=label,
            amount=amount,
            location=location,
            tags=tags or [],
        )
        self.db.session_manager.user_session.commit()
        return balance.identifier

    def edit_manual_balance(
        self,
        identifier: int,
        asset: str | None = None,
        label: str | None = None,
        amount: str | None = None,
        location: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Edit manual balance"""
        self.repos.manual_balances.update_balance(
            identifier=identifier,
            asset=asset,
            label=label,
            amount=amount,
            location=location,
            tags=tags,
        )
        self.db.session_manager.user_session.commit()

    def delete_manual_balance(self, identifier: int) -> None:
        """Delete manual balance"""
        self.repos.manual_balances.delete_balance(identifier)
        self.db.session_manager.user_session.commit()

    def get_manual_balances(self) -> list[dict[str, Any]]:
        """Get all manual balances"""
        balances = self.repos.manual_balances.get_all_balances()
        return [
            {
                'identifier': b.identifier,
                'asset': b.asset,
                'label': b.label,
                'amount': b.amount,
                'location': b.location,
                'tags': self.repos.manual_balances.get_balance_tags(b.identifier),
            }
            for b in balances
        ]

    # Transaction/History methods

    def get_history_events(
        self,
        from_timestamp: int | None = None,
        to_timestamp: int | None = None,
        location: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[dict], int]:
        """Get history events"""
        events = self.repos.history_events.get_events(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            locations=[location] if location else None,
            limit=limit,
            offset=offset,
        )

        count = self.repos.history_events.get_events_count()

        # Convert to dict format
        event_dicts = []
        for event in events:
            event_dict = {
                'identifier': event.identifier,
                'entry_type': event.entry_type,
                'event_identifier': event.event_identifier,
                'sequence_index': event.sequence_index,
                'timestamp': event.timestamp,
                'location': event.location,
                'location_label': event.location_label,
                'asset': event.asset,
                'amount': event.amount,
                'notes': event.notes,
                'type': event.type,
                'subtype': event.subtype,
                'extra_data': event.extra_data,
            }
            event_dicts.append(event_dict)

        return event_dicts, count

    # Utility methods

    def disconnect(self) -> None:
        """Close database connections"""
        self.db.close()

    def backup_database(self, backup_path: Path | None = None) -> Path:
        """Create database backup"""
        return self.db.backup(backup_path)

    def get_version(self) -> int:
        """Get database version"""
        return self.db.get_version()

    def set_version(self, version: int) -> None:
        """Set database version"""
        self.db.set_version(version)

    # Property compatibility

    @property
    def conn(self):
        """Get connection (for compatibility)"""
        return self.db.session_manager.user_session.connection()


def create_dbhandler_adapter(
    user_data_dir: Path,
    password: str,
    **kwargs,
) -> DBHandlerAdapter:
    """
    Create a DBHandler-compatible adapter using ORM.

    Args:
        user_data_dir: User data directory
        password: Database password
        **kwargs: Additional arguments (ignored)

    Returns:
        DBHandler-compatible adapter
    """
    # Create ORM database
    orm_db = RotkehlchenDatabase(
        user_data_dir=user_data_dir,
        password=password,
    )

    # Wrap in adapter
    return DBHandlerAdapter(orm_db)

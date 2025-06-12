"""Database service for handling database operations"""
from typing import Any

from sqlmodel import Session, select

from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.db.models.user.accounts import BlockchainAccount, UserCredentials
from rotkehlchen.db.models.user.notes import UserNote
from rotkehlchen.db.models.user.models import Settings, Tag


class DatabaseService:
    """Service for database operations using SQLModel"""

    def __init__(self, connection: DBConnection):
        self.connection = connection

    def get_settings(self) -> Settings | None:
        """Get user settings"""
        with Session(self.connection) as session:
            statement = select(Settings)
            return session.exec(statement).first()

    def update_settings(self, settings: dict[str, Any]) -> Settings:
        """Update user settings"""
        with Session(self.connection) as session:
            db_settings = session.exec(select(Settings)).first()
            if not db_settings:
                db_settings = Settings()
                session.add(db_settings)

            for key, value in settings.items():
                if hasattr(db_settings, key):
                    setattr(db_settings, key, value)

            session.commit()
            session.refresh(db_settings)
            return db_settings

    def get_user_credentials(self, location: str | None = None) -> list[UserCredentials]:
        """Get user credentials for exchanges"""
        with Session(self.connection) as session:
            statement = select(UserCredentials)
            if location:
                statement = statement.where(UserCredentials.location == location)
            return list(session.exec(statement))

    def add_user_credential(
        self,
        name: str,
        location: str,
        api_key: str | None = None,
        api_secret: str | None = None,
        passphrase: str | None = None,
    ) -> UserCredentials:
        """Add new user credential"""
        with Session(self.connection) as session:
            credential = UserCredentials(
                name=name,
                location=location,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
            )
            session.add(credential)
            session.commit()
            session.refresh(credential)
            return credential

    def get_blockchain_accounts(self, blockchain: str | None = None) -> list[BlockchainAccount]:
        """Get blockchain accounts"""
        with Session(self.connection) as session:
            statement = select(BlockchainAccount)
            if blockchain:
                statement = statement.where(BlockchainAccount.blockchain == blockchain)
            return list(session.exec(statement))

    def add_blockchain_account(self, blockchain: str, account: str) -> BlockchainAccount:
        """Add new blockchain account"""
        with Session(self.connection) as session:
            account_obj = BlockchainAccount(blockchain=blockchain, account=account)
            session.add(account_obj)
            session.commit()
            session.refresh(account_obj)
            return account_obj

    def get_tags(self) -> list[Tag]:
        """Get all tags"""
        with Session(self.connection) as session:
            return list(session.exec(select(Tag)))

    def add_tag(self, name: str, description: str | None = None) -> Tag:
        """Add new tag"""
        with Session(self.connection) as session:
            tag = Tag(name=name, description=description)
            session.add(tag)
            session.commit()
            session.refresh(tag)
            return tag

    def get_user_notes(self, limit: int | None = None) -> list[UserNote]:
        """Get user notes"""
        with Session(self.connection) as session:
            statement = select(UserNote)
            if limit:
                statement = statement.limit(limit)
            return list(session.exec(statement))

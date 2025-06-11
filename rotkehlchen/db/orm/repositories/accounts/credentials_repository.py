"""Repository for external service credentials management"""


from sqlalchemy import select

from rotkehlchen.db.orm.models import (
    UserCredentialMapping,
    UserCredentials,
)
from rotkehlchen.db.orm.user_db_models import ExternalServiceCredentials
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.types import ExchangeApiCredentials, Location


class CredentialsRepository(BaseRepository[UserCredentials]):
    """Repository for managing user and external service credentials"""

    def __init__(self, session):
        super().__init__(session, UserCredentials)

    # User credentials (exchange) operations

    def add_exchange_credentials(
        self,
        name: str,
        location: Location,
        api_key: str,
        api_secret: str,
        passphrase: str | None = None,
    ) -> UserCredentials:
        """Add exchange credentials"""
        credentials = UserCredentials(
            name=name,
            location=location.serialize_for_db(),
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )
        return self.add(credentials)

    def get_exchange_credentials(
        self,
        name: str | None = None,
        location: Location | None = None,
    ) -> list[UserCredentials]:
        """Get exchange credentials"""
        filters = {}
        if name is not None:
            filters['name'] = name
        if location is not None:
            filters['location'] = location.serialize_for_db()

        return self.get_all(**filters)

    def get_credentials_by_exchange(
        self,
        location: Location,
    ) -> list[ExchangeApiCredentials]:
        """Get all credentials for a specific exchange"""
        credentials = self.get_exchange_credentials(location=location)
        result = []

        for cred in credentials:
            # Get mappings for additional settings
            mappings = self.get_credential_mappings(cred.name, location)

            result.append(ExchangeApiCredentials(
                name=cred.name,
                api_key=cred.api_key,
                api_secret=cred.api_secret,
                passphrase=cred.passphrase,
                additional_settings=mappings,
            ))

        return result

    def delete_exchange_credentials(
        self,
        name: str,
        location: Location,
    ) -> bool:
        """Delete exchange credentials"""
        return self.delete_by(
            name=name,
            location=location.serialize_for_db(),
        ) > 0

    def update_exchange_credentials(
        self,
        name: str,
        location: Location,
        api_key: str | None = None,
        api_secret: str | None = None,
        passphrase: str | None = None,
    ) -> bool:
        """Update exchange credentials"""
        cred = self.get(name=name, location=location.serialize_for_db())
        if not cred:
            return False

        if api_key is not None:
            cred.api_key = api_key
        if api_secret is not None:
            cred.api_secret = api_secret
        if passphrase is not None:
            cred.passphrase = passphrase

        self.update(cred)
        return True

    # Credential mapping operations

    def add_credential_mapping(
        self,
        credential_name: str,
        credential_location: Location,
        setting_name: str,
        setting_value: str,
    ) -> UserCredentialMapping:
        """Add a credential mapping"""
        mapping = UserCredentialMapping(
            credential_name=credential_name,
            credential_location=credential_location.serialize_for_db(),
            setting_name=setting_name,
            setting_value=setting_value,
        )
        self.session.add(mapping)
        self.session.flush()
        return mapping

    def get_credential_mappings(
        self,
        credential_name: str,
        credential_location: Location,
    ) -> dict[str, str]:
        """Get all mappings for a credential"""
        stmt = select(UserCredentialMapping).filter_by(
            credential_name=credential_name,
            credential_location=credential_location.serialize_for_db(),
        )
        mappings = self.session.execute(stmt).scalars().all()
        return {m.setting_name: m.setting_value for m in mappings}

    def delete_credential_mappings(
        self,
        credential_name: str,
        credential_location: Location,
    ) -> int:
        """Delete all mappings for a credential"""
        from sqlalchemy import delete

        stmt = delete(UserCredentialMapping).filter_by(
            credential_name=credential_name,
            credential_location=credential_location.serialize_for_db(),
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    # External service credentials operations

    def add_external_service(
        self,
        name: str,
        api_key: str,
        api_secret: str | None = None,
    ) -> ExternalServiceCredentials:
        """Add external service credentials"""
        service = ExternalServiceCredentials(
            name=name,
            api_key=api_key,
            api_secret=api_secret,
        )
        self.session.add(service)
        self.session.flush()
        return service

    def get_external_service(
        self,
        name: str,
    ) -> ExternalServiceCredentials | None:
        """Get external service credentials"""
        stmt = select(ExternalServiceCredentials).filter_by(name=name)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_all_external_services(self) -> list[ExternalServiceCredentials]:
        """Get all external service credentials"""
        stmt = select(ExternalServiceCredentials)
        return list(self.session.execute(stmt).scalars().all())

    def delete_external_service(self, name: str) -> bool:
        """Delete external service credentials"""
        service = self.get_external_service(name)
        if service:
            self.session.delete(service)
            self.session.flush()
            return True
        return False

    def get_exchange_locations(self) -> list[Location]:
        """Get all locations that have credentials"""
        stmt = select(UserCredentials.location).distinct()
        locations = self.session.execute(stmt).scalars().all()

        result = []
        for loc_char in locations:
            location = Location.deserialize_from_db(loc_char)
            if location in SUPPORTED_EXCHANGES:
                result.append(location)

        return result

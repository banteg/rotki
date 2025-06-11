"""Repository for premium subscription management"""


from sqlalchemy import select

from rotkehlchen.db.orm.models import AdblockRule, PremiumCredential, PremiumSync
from rotkehlchen.db.orm.repositories.base import BaseRepository
from rotkehlchen.types import Timestamp


class PremiumRepository(BaseRepository[PremiumCredential]):
    """Repository for managing premium subscriptions"""

    def __init__(self, session):
        super().__init__(session, PremiumCredential)

    def set_credentials(
        self,
        api_key: str,
        api_secret: str,
    ) -> PremiumCredential:
        """Set or update premium credentials"""
        # Delete any existing credentials
        self.session.query(PremiumCredential).delete()

        credential = PremiumCredential(
            api_key=api_key,
            api_secret=api_secret,
        )
        return self.add(credential)

    def get_credentials(self) -> PremiumCredential | None:
        """Get premium credentials"""
        stmt = select(PremiumCredential).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def delete_credentials(self) -> bool:
        """Delete premium credentials"""
        count = self.session.query(PremiumCredential).delete()
        self.session.flush()
        return count > 0

    def has_premium(self) -> bool:
        """Check if premium credentials exist"""
        return self.get_credentials() is not None

    # Premium sync operations

    def add_sync_record(
        self,
        data_type: str,
        data_hash: str,
        last_upload_ts: Timestamp,
    ) -> PremiumSync:
        """Add or update a premium sync record"""
        sync = self.session.query(PremiumSync).filter_by(
            data_type=data_type,
        ).first()

        if sync:
            sync.data_hash = data_hash
            sync.last_upload_ts = int(last_upload_ts)
        else:
            sync = PremiumSync(
                data_type=data_type,
                data_hash=data_hash,
                last_upload_ts=int(last_upload_ts),
            )
            self.session.add(sync)

        self.session.flush()
        return sync

    def get_sync_record(self, data_type: str) -> PremiumSync | None:
        """Get sync record for a data type"""
        return self.session.query(PremiumSync).filter_by(
            data_type=data_type,
        ).first()

    def get_all_sync_records(self) -> list[PremiumSync]:
        """Get all sync records"""
        return list(self.session.query(PremiumSync).all())

    def delete_sync_record(self, data_type: str) -> bool:
        """Delete a sync record"""
        count = self.session.query(PremiumSync).filter_by(
            data_type=data_type,
        ).delete()
        self.session.flush()
        return count > 0

    def delete_all_sync_records(self) -> int:
        """Delete all sync records"""
        count = self.session.query(PremiumSync).delete()
        self.session.flush()
        return count

    def get_last_sync_timestamp(self, data_type: str) -> Timestamp | None:
        """Get last sync timestamp for a data type"""
        sync = self.get_sync_record(data_type)
        return Timestamp(sync.last_upload_ts) if sync else None

    def needs_sync(
        self,
        data_type: str,
        current_hash: str,
    ) -> bool:
        """Check if data needs to be synced"""
        sync = self.get_sync_record(data_type)
        return not sync or sync.data_hash != current_hash

    # Adblock rules operations

    def add_adblock_rule(
        self,
        domain: str,
        rule_type: str = 'block',
    ) -> AdblockRule:
        """Add an adblock rule"""
        rule = AdblockRule(
            domain=domain,
            rule_type=rule_type,
        )
        self.session.add(rule)
        self.session.flush()
        return rule

    def get_adblock_rules(
        self,
        rule_type: str | None = None,
    ) -> list[AdblockRule]:
        """Get adblock rules"""
        query = self.session.query(AdblockRule)

        if rule_type:
            query = query.filter_by(rule_type=rule_type)

        return list(query.all())

    def delete_adblock_rule(self, domain: str) -> bool:
        """Delete an adblock rule"""
        count = self.session.query(AdblockRule).filter_by(
            domain=domain,
        ).delete()
        self.session.flush()
        return count > 0

    def is_domain_blocked(self, domain: str) -> bool:
        """Check if a domain is blocked"""
        rule = self.session.query(AdblockRule).filter_by(
            domain=domain,
            rule_type='block',
        ).first()
        return rule is not None

    def clear_all_adblock_rules(self) -> int:
        """Delete all adblock rules"""
        count = self.session.query(AdblockRule).delete()
        self.session.flush()
        return count

    def bulk_add_adblock_rules(
        self,
        domains: list[str],
        rule_type: str = 'block',
    ) -> list[AdblockRule]:
        """Bulk add adblock rules"""
        rules = []

        for domain in domains:
            rule = AdblockRule(
                domain=domain,
                rule_type=rule_type,
            )
            self.session.add(rule)
            rules.append(rule)

        self.session.flush()
        return rules

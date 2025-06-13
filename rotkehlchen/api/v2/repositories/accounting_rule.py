"""Repository for managing accounting rules."""
from typing import TYPE_CHECKING

from sqlmodel import select

from rotkehlchen.api.v2.repositories.base import BaseRepository
from rotkehlchen.db.models.user.accounting import AccountingRule, LinkedRuleProperty

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


class AccountingRuleRepository(BaseRepository[AccountingRule]):
    """Repository for managing accounting rules."""

    model = AccountingRule

    def get_rules_for_event_type(
        self,
        event_type: str,
        event_subtype: str | None = None,
    ) -> list[AccountingRule]:
        """Get all accounting rules that match the given event type and subtype."""
        query = select(self.model).where(self.model.event_type == event_type)

        if event_subtype is not None:
            query = query.where(self.model.event_subtype == event_subtype)

        result = self.session.exec(query)
        return list(result.all())

    def get_rules_for_counterparty(
        self,
        counterparty: str,
        event_type: str | None = None,
    ) -> list[AccountingRule]:
        """Get all accounting rules for a specific counterparty."""
        query = select(self.model).where(self.model.counterparty == counterparty)

        if event_type is not None:
            query = query.where(self.model.event_type == event_type)

        result = self.session.exec(query)
        return list(result.all())

    def get_rule_with_links(self, rule_id: int) -> AccountingRule | None:
        """Get a rule with its linked properties."""
        rule = self.get(rule_id)
        if rule:
            # Load linked properties
            links_query = select(LinkedRuleProperty).where(
                LinkedRuleProperty.accounting_rule == rule_id,
            )
            links = list(self.session.exec(links_query).all())
            # We can attach these to the rule object if needed
            # For now, return the rule as is
        return rule

    def create_with_links(
        self,
        rule_data: dict,
        linked_properties: list[dict] | None = None,
    ) -> AccountingRule:
        """Create a new accounting rule with optional linked properties."""
        # Create the main rule
        rule = self.create(rule_data)

        # Create linked properties if provided
        if linked_properties:
            for link_data in linked_properties:
                link_data['accounting_rule'] = rule.identifier
                link = LinkedRuleProperty(**link_data)
                self.session.add(link)
            self.session.commit()

        return rule

    def get_rules_by_address(self, address: 'ChecksumEvmAddress') -> list[AccountingRule]:
        """Get all accounting rules associated with a specific address."""
        # This requires a join with the linked_rules_properties table
        query = (
            select(self.model)
            .join(LinkedRuleProperty, LinkedRuleProperty.accounting_rule == self.model.identifier)
            .where(LinkedRuleProperty.value == address)
            .where(LinkedRuleProperty.setting_type == 'address')
        )

        result = self.session.exec(query)
        return list(result.all())

    def get_conflicting_rules(
        self,
        event_type: str,
        event_subtype: str | None = None,
        counterparty: str | None = None,
    ) -> list[AccountingRule]:
        """Find rules that might conflict with the given parameters."""
        query = select(self.model).where(self.model.event_type == event_type)

        if event_subtype is not None:
            query = query.where(self.model.event_subtype == event_subtype)

        if counterparty is not None:
            query = query.where(self.model.counterparty == counterparty)

        result = self.session.exec(query)
        return list(result.all())

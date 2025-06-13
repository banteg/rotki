"""Async AccountingRule repository for v2 API.

Handles all accounting rules-related async database operations.
"""
from typing import TYPE_CHECKING

from sqlalchemy import delete as sa_delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from rotkehlchen.api.v2.repositories.async_base import AsyncBaseRepository
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
    NO_ACCOUNTING_COUNTERPARTY,
)
from rotkehlchen.db.models.user.accounting import AccountingRule, LinkedRuleProperty
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotkehlchen.db.filtering import AccountingRulesFilterQuery


class AsyncAccountingRuleRepository(AsyncBaseRepository[AccountingRule]):
    """Async repository for accounting rules."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AccountingRule)
    
    async def add_accounting_rule(
        self,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        counterparty: str | None,
        rule: BaseEventSettings,
        links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
        force_update: bool = False,
    ) -> int:
        """
        Add a single accounting rule to the database. It returns the identifier
        of the created rule.
        May raise:
        - InputError: If the combination of type, subtype and counterparty already exists
        and we are not force updating.
        """
        counterparty_value = counterparty if counterparty is not None else NO_ACCOUNTING_COUNTERPARTY
        
        if force_update:
            # Check if rule exists and update it
            statement = select(AccountingRule).where(
                AccountingRule.type == event_type.serialize(),
                AccountingRule.subtype == event_subtype.serialize(),
                AccountingRule.counterparty == counterparty_value,
            )
            result = await self.session.execute(statement)
            existing_rule = result.scalar_one_or_none()
            
            if existing_rule:
                # Update existing rule
                serialized = rule.serialize_for_db()
                existing_rule.taxable = serialized[0]
                existing_rule.count_entire_amount_spend = serialized[1]
                existing_rule.count_cost_basis_pnl = serialized[2]
                existing_rule.accounting_treatment = serialized[3]
                self.session.add(existing_rule)
                await self.session.commit()
                rule_id = existing_rule.identifier
            else:
                # Create new rule
                rule_id = await self._create_new_rule(
                    event_type, event_subtype, counterparty_value, rule
                )
        else:
            try:
                rule_id = await self._create_new_rule(
                    event_type, event_subtype, counterparty_value, rule
                )
            except IntegrityError as e:
                raise InputError(
                    f'Rule for ({event_type.serialize()}, {event_subtype.serialize()}, {counterparty}) already exists'
                ) from e
        
        # Add linked settings
        await self._update_linked_settings(rule_id, links)
        
        return rule_id
    
    async def _create_new_rule(
        self,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        counterparty_value: str,
        rule: BaseEventSettings,
    ) -> int:
        """Create a new accounting rule."""
        serialized = rule.serialize_for_db()
        new_rule = AccountingRule(
            type=event_type.serialize(),
            subtype=event_subtype.serialize(),
            counterparty=counterparty_value,
            taxable=serialized[0],
            count_entire_amount_spend=serialized[1],
            count_cost_basis_pnl=serialized[2],
            accounting_treatment=serialized[3],
        )
        self.session.add(new_rule)
        await self.session.commit()
        await self.session.refresh(new_rule)
        return new_rule.identifier
    
    async def remove_accounting_rule(
        self, rule_id: int
    ) -> tuple[HistoryEventType, HistoryEventSubType, str | None]:
        """
        Delete an accounting rule using its identifier. Returns the type identifier for the rule.
        May raise:
        - InputError if the rule doesn't exist
        """
        # Get the rule first
        rule = await self.get(rule_id)
        if not rule:
            raise InputError(f'Rule with id {rule_id} does not exist')
        
        event_type = HistoryEventType.deserialize(rule.type)
        event_subtype = HistoryEventSubType.deserialize(rule.subtype)
        counterparty = None if rule.counterparty == NO_ACCOUNTING_COUNTERPARTY else rule.counterparty
        
        # Delete linked properties
        await self.session.execute(
            sa_delete(LinkedRuleProperty).where(LinkedRuleProperty.accounting_rule == rule_id)
        )
        
        # Delete the rule
        self.session.delete(rule)
        await self.session.commit()
        
        return event_type, event_subtype, counterparty
    
    async def update_accounting_rule(
        self,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        counterparty: str | None,
        rule: BaseEventSettings,
        links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
        identifier: int,
    ) -> None:
        """
        Edit accounting rule properties (type, subtype, counterparty) for the rule with the
        provided identifier
        May raise:
        - InputError: if no event gets updated
        """
        # Get existing rule
        existing_rule = await self.get(identifier)
        if not existing_rule:
            raise InputError(
                f'Tried to update accounting rule for ({event_type.serialize()}, {event_subtype.serialize()}, {counterparty}) '
                f'but it was not found'
            )
        
        # Update rule properties
        counterparty_value = counterparty if counterparty is not None else NO_ACCOUNTING_COUNTERPARTY
        serialized = rule.serialize_for_db()
        
        existing_rule.type = event_type.serialize()
        existing_rule.subtype = event_subtype.serialize()
        existing_rule.counterparty = counterparty_value
        existing_rule.taxable = serialized[0]
        existing_rule.count_entire_amount_spend = serialized[1]
        existing_rule.count_cost_basis_pnl = serialized[2]
        existing_rule.accounting_treatment = serialized[3]
        
        try:
            self.session.add(existing_rule)
            await self.session.commit()
        except IntegrityError as e:
            raise InputError(
                f'Accounting rule for ({event_type.serialize()}, {event_subtype.serialize()}, {counterparty}) '
                'already exists in the database'
            ) from e
        
        # Update linked settings
        await self._update_linked_settings(identifier, links)
    
    async def _update_linked_settings(
        self,
        rule_id: int,
        links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> None:
        """Update linked settings for a rule."""
        # Delete existing links
        await self.session.execute(
            sa_delete(LinkedRuleProperty).where(LinkedRuleProperty.accounting_rule == rule_id)
        )
        
        # Add new links
        for property_name, setting_name in links.items():
            linked_property = LinkedRuleProperty(
                accounting_rule=rule_id,
                property_name=property_name,
                setting_name=setting_name,
            )
            self.session.add(linked_property)
        
        await self.session.commit()
    
    async def get_rules_for_event(
        self,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType | None = None,
        counterparty: str | None = None,
    ) -> list[AccountingRule]:
        """Get accounting rules matching the given criteria."""
        statement = select(AccountingRule).where(
            AccountingRule.type == event_type.serialize()
        )
        
        if event_subtype is not None:
            statement = statement.where(AccountingRule.subtype == event_subtype.serialize())
        
        if counterparty is not None:
            counterparty_value = counterparty if counterparty else NO_ACCOUNTING_COUNTERPARTY
            statement = statement.where(AccountingRule.counterparty == counterparty_value)
        
        result = await self.session.execute(statement)
        return [row[0] for row in result.all()]
    
    async def get_rule_with_links(self, rule_id: int) -> tuple[AccountingRule, list[LinkedRuleProperty]] | None:
        """Get a rule with its linked properties."""
        rule = await self.get(rule_id)
        if not rule:
            return None
        
        # Get linked properties
        statement = select(LinkedRuleProperty).where(
            LinkedRuleProperty.accounting_rule == rule_id
        )
        result = await self.session.execute(statement)
        links = [row[0] for row in result.all()]
        
        return rule, links
    
    async def get_all_rules_with_filter(
        self,
        filter_query: 'AccountingRulesFilterQuery | None' = None,
    ) -> tuple[list[AccountingRule], int]:
        """Get all accounting rules with optional filtering."""
        if filter_query:
            # Build filter query
            base_query, bindings = filter_query.prepare(with_pagination=False)
            count_query = f'SELECT COUNT(*) FROM accounting_rules {base_query}'
            result = await self.session.execute(count_query, bindings)
            total_found = result.scalar()
            
            # Get actual rules
            query, bindings = filter_query.prepare()
            query = f'SELECT * FROM accounting_rules {query}'
            result = await self.session.execute(query, bindings)
            
            rules = []
            for row in result:
                rule = AccountingRule(
                    identifier=row[0],
                    type=row[1],
                    subtype=row[2],
                    counterparty=row[3],
                    taxable=row[4],
                    count_entire_amount_spend=row[5],
                    count_cost_basis_pnl=row[6],
                    accounting_treatment=row[7],
                )
                rules.append(rule)
            
            return rules, total_found
        else:
            # Get all rules
            statement = select(AccountingRule)
            result = await self.session.execute(statement)
            rules = [row[0] for row in result.all()]
            return rules, len(rules)
    
    async def find_by(self, **kwargs) -> list[AccountingRule]:
        """Find accounting rules by criteria."""
        statement = select(AccountingRule)
        
        for key, value in kwargs.items():
            if hasattr(AccountingRule, key):
                statement = statement.where(getattr(AccountingRule, key) == value)
        
        results = await self.session.execute(statement)
        return [row[0] for row in results.all()]
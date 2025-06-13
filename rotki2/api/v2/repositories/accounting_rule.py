"""AccountingRule repository for v2 API.

Handles all accounting rules-related async database operations.
"""
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete as sa_delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, text

from rotki2.api.v2.repositories.async_base import AsyncBaseRepository
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
    NO_ACCOUNTING_COUNTERPARTY,
)
from rotki2.db.models.user.accounting import AccountingRule, LinkedRuleProperty
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotkehlchen.db.filtering import AccountingRulesFilterQuery


class AccountingRuleRepository(AsyncBaseRepository[AccountingRule]):
    """Repository for accounting rules."""
    
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
        return result.scalars().all()
    
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
        links = result.scalars().all()
        
        return rule, links
    
    async def get_all_rules_with_filter(
        self,
        filter_query: 'AccountingRulesFilterQuery | None' = None,
    ) -> tuple[list[AccountingRule], int]:
        """Get all accounting rules with optional filtering."""
        if filter_query:
            # Note: Dynamic filter queries require raw SQL
            # Build filter query
            base_query, bindings = filter_query.prepare(with_pagination=False)
            count_query = f'SELECT COUNT(*) FROM accounting_rules {base_query}'
            result = await self.session.execute(text(count_query), bindings)
            total_found = result.scalar()
            
            # Get actual rules
            query, bindings = filter_query.prepare()
            query = f'SELECT * FROM accounting_rules {query}'
            result = await self.session.execute(text(query), bindings)
            
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
            # Get all rules using ORM
            statement = select(AccountingRule)
            result = await self.session.execute(statement)
            rules = result.scalars().all()
            return rules, len(rules)
    
    async def find_by(self, **kwargs) -> list[AccountingRule]:
        """Find accounting rules by criteria."""
        statement = select(AccountingRule)
        
        for key, value in kwargs.items():
            if hasattr(AccountingRule, key):
                statement = statement.where(getattr(AccountingRule, key) == value)
        
        results = await self.session.execute(statement)
        return results.scalars().all()
    
    async def get_accounting_rules_and_properties(self) -> dict[str, Any]:
        """Get all accounting rules and their linked properties in export format.
        
        Returns:
            Dict with accounting rules and linked rule properties
        """
        # Get all rules
        rules_statement = select(AccountingRule)
        rules_result = await self.session.execute(rules_statement)
        rules = rules_result.scalars().all()
        
        # Get all linked properties
        links_statement = select(LinkedRuleProperty)
        links_result = await self.session.execute(links_statement)
        links = links_result.scalars().all()
        
        # Convert to export format
        accounting_rules = []
        for rule in rules:
            accounting_rules.append({
                'identifier': rule.identifier,
                'type': rule.type,
                'subtype': rule.subtype,
                'counterparty': rule.counterparty,
                'taxable': rule.taxable,
                'count_entire_amount_spend': rule.count_entire_amount_spend,
                'count_cost_basis_pnl': rule.count_cost_basis_pnl,
                'accounting_treatment': rule.accounting_treatment,
            })
        
        linked_properties = []
        for link in links:
            linked_properties.append({
                'identifier': link.identifier,
                'accounting_rule': link.accounting_rule,
                'property_name': link.property_name,
                'setting_name': link.setting_name,
            })
        
        return {
            'accounting_rules': accounting_rules,
            'linked_rule_properties': linked_properties,
        }
    
    async def query_missing_accounting_rules(
        self,
        event_types: list[HistoryEventType] | None = None,
        event_subtypes: list[HistoryEventSubType] | None = None,
        counterparties: list[str] | None = None,
    ) -> list[tuple[HistoryEventType, HistoryEventSubType, str | None]]:
        """Query which event combinations are missing accounting rules.
        
        This determines which events won't be processed in accounting because
        they lack rules.
        
        Args:
            event_types: Optional list of event types to check
            event_subtypes: Optional list of event subtypes to check
            counterparties: Optional list of counterparties to check
            
        Returns:
            List of (type, subtype, counterparty) tuples that need rules
        """
        # Build filter conditions
        conditions = []
        params = {}
        
        if event_types:
            type_strings = [t.serialize() for t in event_types]
            conditions.append("he.type IN :types")
            params['types'] = tuple(type_strings)
        
        if event_subtypes:
            subtype_strings = [s.serialize() for s in event_subtypes]
            conditions.append("he.subtype IN :subtypes")
            params['subtypes'] = tuple(subtype_strings)
        
        if counterparties:
            # Handle EVM events with counterparties
            conditions.append("(eei.counterparty IN :counterparties OR eei.counterparty IS NULL)")
            params['counterparties'] = tuple(counterparties)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        # Query for unique type/subtype/counterparty combinations in history events
        query = text(f"""
            SELECT DISTINCT 
                he.type,
                he.subtype,
                COALESCE(eei.counterparty, :no_counterparty) as counterparty
            FROM history_events he
            LEFT JOIN evm_events_info eei ON he.identifier = eei.identifier
            {where_clause}
        """)
        params['no_counterparty'] = NO_ACCOUNTING_COUNTERPARTY
        
        result = await self.session.execute(query, params)
        event_combinations = result.fetchall()
        
        # Get existing rules
        rules_query = text("""
            SELECT DISTINCT type, subtype, counterparty
            FROM accounting_rules
        """)
        rules_result = await self.session.execute(rules_query)
        existing_rules = {(row[0], row[1], row[2]) for row in rules_result.fetchall()}
        
        # Find missing rules
        missing_rules = []
        events_to_consume = await self._events_to_consume()
        
        for type_str, subtype_str, counterparty_str in event_combinations:
            # Check if this combination has a rule
            if (type_str, subtype_str, counterparty_str) not in existing_rules:
                # Check if it's an event that should be consumed by special treatment
                event_type = HistoryEventType.deserialize(type_str)
                event_subtype = HistoryEventSubType.deserialize(subtype_str)
                counterparty = None if counterparty_str == NO_ACCOUNTING_COUNTERPARTY else counterparty_str
                
                if (event_type, event_subtype) not in events_to_consume:
                    missing_rules.append((event_type, event_subtype, counterparty))
        
        return missing_rules
    
    async def _events_to_consume(self) -> set[tuple[HistoryEventType, HistoryEventSubType]]:
        """Get event type/subtype combinations that are consumed by special treatments.
        
        Returns:
            Set of (type, subtype) tuples that don't need explicit rules
        """
        # These events are handled by special accounting treatments
        events = set()
        
        # Check for swap accounting treatment
        swap_query = text("""
            SELECT 1 FROM accounting_rules
            WHERE accounting_treatment = 'swap'
            LIMIT 1
        """)
        swap_result = await self.session.execute(swap_query)
        if swap_result.scalar():
            # Swap events are consumed by swap treatment
            events.add((HistoryEventType.TRADE, HistoryEventSubType.SPEND))
            events.add((HistoryEventType.TRADE, HistoryEventSubType.RECEIVE))
        
        # Check for gas accounting treatment
        gas_query = text("""
            SELECT 1 FROM accounting_rules
            WHERE type = :type AND subtype = :subtype
            AND accounting_treatment IS NOT NULL
            LIMIT 1
        """)
        gas_params = {
            'type': HistoryEventType.SPEND.serialize(),
            'subtype': HistoryEventSubType.FEE.serialize(),
        }
        gas_result = await self.session.execute(gas_query, gas_params)
        if gas_result.scalar():
            # Gas fees might be consumed by special treatment
            events.add((HistoryEventType.SPEND, HistoryEventSubType.FEE))
        
        return events
    
    async def add_linked_setting(
        self,
        rule_id: int,
        property_name: LINKABLE_ACCOUNTING_PROPERTIES,
        setting_name: LINKABLE_ACCOUNTING_SETTINGS_NAME,
    ) -> None:
        """Add a single linked setting to a rule.
        
        Args:
            rule_id: The accounting rule identifier
            property_name: The property to link
            setting_name: The setting name to link to
        """
        # Check if rule exists
        rule = await self.get(rule_id)
        if not rule:
            raise InputError(f'Rule with id {rule_id} does not exist')
        
        # Add linked property
        linked_property = LinkedRuleProperty(
            accounting_rule=rule_id,
            property_name=property_name,
            setting_name=setting_name,
        )
        self.session.add(linked_property)
        
        try:
            await self.session.commit()
        except IntegrityError as e:
            raise InputError(
                f'Linked property {property_name} already exists for rule {rule_id}'
            ) from e
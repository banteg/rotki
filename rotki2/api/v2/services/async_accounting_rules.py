"""Async AccountingRules service for accounting rule operations"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.types import EventAccountingRuleStatus
from rotki2.api.v2.repositories.async_accounting_rule import AsyncAccountingRuleRepository
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
)
from rotkehlchen.db.filtering import AccountingRulesFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant


class AsyncAccountingRulesService:
    """Async service for accounting rules operations"""
    
    def __init__(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
        accountant: 'Accountant | None' = None,
    ):
        self.accounting_rule_repository = accounting_rule_repository
        self.accountant = accountant
    
    async def add_accounting_rule(
        self,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        counterparty: str | None,
        rule: BaseEventSettings,
        links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
        force_update: bool = False,
    ) -> dict[str, Any]:
        """Add a new accounting rule."""
        try:
            rule_id = await self.accounting_rule_repository.add_accounting_rule(
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
                rule=rule,
                links=links,
                force_update=force_update,
            )
            
            return {
                'identifier': rule_id,
                'message': f'Successfully added accounting rule for ({event_type.serialize()}, {event_subtype.serialize()}, {counterparty})',
            }
        except InputError as e:
            raise InputError(str(e)) from e
    
    async def remove_accounting_rule(self, rule_id: int) -> dict[str, Any]:
        """Remove an accounting rule by ID."""
        try:
            event_type, event_subtype, counterparty = await self.accounting_rule_repository.remove_accounting_rule(rule_id)
            
            return {
                'message': f'Successfully removed accounting rule for ({event_type.serialize()}, {event_subtype.serialize()}, {counterparty})',
            }
        except InputError as e:
            raise InputError(str(e)) from e
    
    async def update_accounting_rule(
        self,
        rule_id: int,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        counterparty: str | None,
        rule: BaseEventSettings,
        links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> dict[str, Any]:
        """Update an existing accounting rule."""
        try:
            await self.accounting_rule_repository.update_accounting_rule(
                event_type=event_type,
                event_subtype=event_subtype,
                counterparty=counterparty,
                rule=rule,
                links=links,
                identifier=rule_id,
            )
            
            return {
                'message': f'Successfully updated accounting rule {rule_id}',
            }
        except InputError as e:
            raise InputError(str(e)) from e
    
    async def get_accounting_rules(
        self,
        filter_query: AccountingRulesFilterQuery | None = None,
    ) -> dict[str, Any]:
        """Get accounting rules with optional filtering."""
        rules, total_found = await self.accounting_rule_repository.get_all_rules_with_filter(
            filter_query=filter_query,
        )
        
        # Serialize rules
        serialized_rules = []
        for rule in rules:
            rule_with_links = await self.accounting_rule_repository.get_rule_with_links(rule.identifier)
            if rule_with_links:
                rule_obj, links = rule_with_links
                
                # Convert links to dict
                links_dict = {
                    link.property_name: link.setting_name
                    for link in links
                }
                
                serialized_rules.append({
                    'identifier': rule_obj.identifier,
                    'event_type': rule_obj.type,
                    'event_subtype': rule_obj.subtype,
                    'counterparty': None if rule_obj.counterparty == 'NO_ACCOUNTING_COUNTERPARTY' else rule_obj.counterparty,
                    'taxable': rule_obj.taxable,
                    'count_entire_amount_spend': rule_obj.count_entire_amount_spend,
                    'count_cost_basis_pnl': rule_obj.count_cost_basis_pnl,
                    'accounting_treatment': rule_obj.accounting_treatment,
                    'links': links_dict,
                })
        
        return {
            'entries': serialized_rules,
            'entries_found': total_found,
            'entries_total': await self.accounting_rule_repository.count(),
        }
    
    async def get_accounting_rule(self, rule_id: int) -> dict[str, Any]:
        """Get a specific accounting rule by ID."""
        rule_with_links = await self.accounting_rule_repository.get_rule_with_links(rule_id)
        if not rule_with_links:
            raise InputError(f'Accounting rule with id {rule_id} not found')
        
        rule, links = rule_with_links
        
        # Convert links to dict
        links_dict = {
            link.property_name: link.setting_name
            for link in links
        }
        
        return {
            'identifier': rule.identifier,
            'event_type': rule.type,
            'event_subtype': rule.subtype,
            'counterparty': None if rule.counterparty == 'NO_ACCOUNTING_COUNTERPARTY' else rule.counterparty,
            'taxable': rule.taxable,
            'count_entire_amount_spend': rule.count_entire_amount_spend,
            'count_cost_basis_pnl': rule.count_cost_basis_pnl,
            'accounting_treatment': rule.accounting_treatment,
            'links': links_dict,
        }
    
    async def get_accounting_rules_for_event(
        self,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType | None = None,
        counterparty: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get accounting rules for a specific event type."""
        rules = await self.accounting_rule_repository.get_rules_for_event(
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
        )
        
        serialized_rules = []
        for rule in rules:
            rule_with_links = await self.accounting_rule_repository.get_rule_with_links(rule.identifier)
            if rule_with_links:
                rule_obj, links = rule_with_links
                
                # Convert links to dict
                links_dict = {
                    link.property_name: link.setting_name
                    for link in links
                }
                
                serialized_rules.append({
                    'identifier': rule_obj.identifier,
                    'event_type': rule_obj.type,
                    'event_subtype': rule_obj.subtype,
                    'counterparty': None if rule_obj.counterparty == 'NO_ACCOUNTING_COUNTERPARTY' else rule_obj.counterparty,
                    'taxable': rule_obj.taxable,
                    'count_entire_amount_spend': rule_obj.count_entire_amount_spend,
                    'count_cost_basis_pnl': rule_obj.count_cost_basis_pnl,
                    'accounting_treatment': rule_obj.accounting_treatment,
                    'links': links_dict,
                })
        
        return serialized_rules
    
    async def export_accounting_rules(self) -> dict[str, list[dict[str, Any]]]:
        """Export all accounting rules."""
        rules, _ = await self.accounting_rule_repository.get_all_rules_with_filter()
        
        exported_rules = []
        for rule in rules:
            rule_with_links = await self.accounting_rule_repository.get_rule_with_links(rule.identifier)
            if rule_with_links:
                rule_obj, links = rule_with_links
                
                # Convert links to dict
                links_dict = {
                    link.property_name: link.setting_name
                    for link in links
                }
                
                exported_rules.append({
                    'event_type': rule_obj.type,
                    'event_subtype': rule_obj.subtype,
                    'counterparty': None if rule_obj.counterparty == 'NO_ACCOUNTING_COUNTERPARTY' else rule_obj.counterparty,
                    'taxable': rule_obj.taxable,
                    'count_entire_amount_spend': rule_obj.count_entire_amount_spend,
                    'count_cost_basis_pnl': rule_obj.count_cost_basis_pnl,
                    'accounting_treatment': rule_obj.accounting_treatment,
                    'links': links_dict,
                })
        
        return {'rules': exported_rules}
    
    async def import_accounting_rules(
        self,
        rules: list[dict[str, Any]],
        force_update: bool = False,
    ) -> dict[str, Any]:
        """Import accounting rules."""
        imported_count = 0
        errors = []
        
        for rule_data in rules:
            try:
                # Parse event types
                event_type = HistoryEventType.deserialize(rule_data['event_type'])
                event_subtype = HistoryEventSubType.deserialize(rule_data['event_subtype'])
                counterparty = rule_data.get('counterparty')
                
                # Create rule object
                if rule_data.get('accounting_treatment'):
                    treatment = TxAccountingTreatment.deserialize(rule_data['accounting_treatment'])
                else:
                    treatment = None
                
                rule = BaseEventSettings(
                    taxable=rule_data['taxable'],
                    count_entire_amount_spend=rule_data['count_entire_amount_spend'],
                    count_cost_basis_pnl=rule_data['count_cost_basis_pnl'],
                    accounting_treatment=treatment,
                )
                
                # Import the rule
                await self.accounting_rule_repository.add_accounting_rule(
                    event_type=event_type,
                    event_subtype=event_subtype,
                    counterparty=counterparty,
                    rule=rule,
                    links=rule_data.get('links', {}),
                    force_update=force_update,
                )
                imported_count += 1
                
            except (InputError, DeserializationError) as e:
                errors.append({
                    'rule': str(rule_data),
                    'error': str(e),
                })
        
        return {
            'imported': imported_count,
            'errors': errors,
        }
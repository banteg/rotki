"""Async Accounting service for managing accounting rules and report generation"""
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.repositories.accounting_rule import AccountingRuleRepository
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
)
from rotkehlchen.db.filtering import AccountingRulesFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotki2.api.v2.repositories.history_events import HistoryEventsRepository


class AsyncAccountingRulesService:
    """Async service for handling accounting rules"""

    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session
        self.accounting_rule_repo = AccountingRuleRepository(session)

    async def add_accounting_rule(
        self,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        counterparty: str | None,
        rule: BaseEventSettings,
        links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
        force_update: bool = False,
    ) -> int:
        """Add a new accounting rule
        
        Returns the rule identifier
        """
        return await self.accounting_rule_repo.add_accounting_rule(
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
            rule=rule,
            links=links,
            force_update=force_update,
        )

    async def remove_accounting_rule(
        self,
        rule_id: int,
    ) -> tuple[HistoryEventType, HistoryEventSubType, str | None]:
        """Remove an accounting rule
        
        Returns the type information for the removed rule
        """
        return await self.accounting_rule_repo.remove_accounting_rule(rule_id)

    async def update_accounting_rule(
        self,
        identifier: int,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        counterparty: str | None,
        rule: BaseEventSettings,
        links: dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME],
    ) -> None:
        """Update an existing accounting rule"""
        await self.accounting_rule_repo.update_accounting_rule(
            event_type=event_type,
            event_subtype=event_subtype,
            counterparty=counterparty,
            rule=rule,
            links=links,
            identifier=identifier,
        )

    async def get_all_rules(
        self,
        filter_query: AccountingRulesFilterQuery | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get all accounting rules with optional filtering
        
        Returns (rules, total_count)
        """
        rules, total = await self.accounting_rule_repo.get_all_rules_with_filter(
            filter_query=filter_query
        )
        
        # Serialize rules
        serialized_rules = []
        for rule in rules:
            # Get linked properties for this rule
            _, links = await self.accounting_rule_repo.get_rule_with_links(rule.identifier)
            
            linked_properties = {}
            for link in links:
                linked_properties[link.property_name] = link.setting_name
            
            serialized_rules.append({
                'identifier': rule.identifier,
                'event_type': rule.type,
                'event_subtype': rule.subtype,
                'counterparty': rule.counterparty,
                'taxable': rule.taxable,
                'count_entire_amount_spend': rule.count_entire_amount_spend,
                'count_cost_basis_pnl': rule.count_cost_basis_pnl,
                'accounting_treatment': rule.accounting_treatment,
                'links': linked_properties,
            })
        
        return serialized_rules, total

    async def query_missing_accounting_rules(
        self,
        event_types: list[HistoryEventType] | None = None,
        event_subtypes: list[HistoryEventSubType] | None = None,
        counterparties: list[str] | None = None,
    ) -> list[tuple[HistoryEventType, HistoryEventSubType, str | None]]:
        """Query which event combinations are missing accounting rules"""
        return await self.accounting_rule_repo.query_missing_accounting_rules(
            event_types=event_types,
            event_subtypes=event_subtypes,
            counterparties=counterparties,
        )

    async def export_accounting_rules(self) -> dict[str, Any]:
        """Export all accounting rules and linked properties"""
        return await self.accounting_rule_repo.get_accounting_rules_and_properties()

    async def import_accounting_rules(
        self,
        data: dict[str, Any],
    ) -> dict[str, int]:
        """Import accounting rules from exported data
        
        Returns dict with counts of imported/failed rules
        """
        imported = 0
        failed = 0
        
        # Import accounting rules
        for rule_data in data.get('accounting_rules', []):
            try:
                # Create BaseEventSettings
                rule = BaseEventSettings(
                    taxable=rule_data['taxable'],
                    count_entire_amount_spend=rule_data['count_entire_amount_spend'],
                    count_cost_basis_pnl=rule_data['count_cost_basis_pnl'],
                    accounting_treatment=rule_data.get('accounting_treatment'),
                )
                
                # Get type/subtype
                event_type = HistoryEventType.deserialize(rule_data['type'])
                event_subtype = HistoryEventSubType.deserialize(rule_data['subtype'])
                counterparty = rule_data['counterparty']
                
                # Import the rule
                await self.accounting_rule_repo.add_accounting_rule(
                    event_type=event_type,
                    event_subtype=event_subtype,
                    counterparty=counterparty,
                    rule=rule,
                    links={},  # Links will be imported separately
                    force_update=True,
                )
                imported += 1
            except Exception as e:
                print(f"Failed to import rule: {e}")
                failed += 1
        
        # Import linked properties
        for link_data in data.get('linked_rule_properties', []):
            try:
                if link_data['accounting_rule']:
                    await self.accounting_rule_repo.add_linked_setting(
                        rule_id=link_data['accounting_rule'],
                        property_name=link_data['property_name'],
                        setting_name=link_data['setting_name'],
                    )
            except Exception:
                # Linked property might reference a rule that wasn't imported
                pass
        
        return {
            'imported': imported,
            'failed': failed,
            'total': len(data.get('accounting_rules', [])),
        }


class AsyncAccountingService:
    """Async service for accounting operations and report generation"""
    
    def __init__(
        self,
        session: AsyncSession,
        history_repo: 'HistoryEventsRepository | None' = None,
    ):
        self.session = session
        self.history_repo = history_repo
        self.rules_service = AsyncAccountingRulesService(session)
    
    async def process_accounting_report(
        self,
        from_timestamp: int,
        to_timestamp: int,
        settings: dict[str, Any] | None = None,
    ) -> int:
        """Process accounting report for the given time range
        
        This is a placeholder for the full accounting logic.
        In a complete implementation, this would:
        1. Fetch all history events in the time range
        2. Apply accounting rules to each event
        3. Calculate PnL using the configured cost basis method
        4. Generate and store the report
        
        Returns report ID
        """
        # Generate a mock report ID
        import time
        report_id = int(time.time())
        
        # In production, this would:
        # 1. Create a new report entry in the database
        # 2. Start async processing of events
        # 3. Apply accounting rules
        # 4. Calculate taxes based on jurisdiction
        # 5. Store results
        
        return report_id
    
    async def get_report(self, report_id: int) -> dict[str, Any] | None:
        """Get a generated accounting report by ID"""
        # In production, this would fetch from the reports table
        return {
            'report_id': report_id,
            'status': 'completed',
            'from_timestamp': 0,
            'to_timestamp': 0,
            'entries': [],
            'totals': {
                'taxable_profit': '0',
                'taxable_loss': '0',
                'free_profit': '0',
                'free_loss': '0',
            },
        }
    
    async def get_all_reports(self) -> list[dict[str, Any]]:
        """Get all generated reports"""
        # In production, this would query the reports table
        return []
    
    async def delete_report(self, report_id: int) -> bool:
        """Delete a report"""
        # In production, this would delete from the reports table
        return True
    
    async def get_accounting_settings(self) -> dict[str, Any]:
        """Get current accounting settings"""
        # In production, this would fetch from settings
        return {
            'include_crypto2crypto': True,
            'include_gas_costs': True,
            'cost_basis_method': 'fifo',
            'account_for_assets_movements': True,
            'calculate_past_cost_basis': True,
            'tax_free_period': None,
        }
    
    async def update_accounting_settings(
        self,
        settings: dict[str, Any],
    ) -> None:
        """Update accounting settings"""
        # In production, this would update the settings table
        pass
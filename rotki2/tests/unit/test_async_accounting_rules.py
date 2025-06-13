"""Tests for async accounting rules repository and service."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

from rotki2.api.v2.repositories.async_accounting_rule import AsyncAccountingRuleRepository
from rotki2.api.v2.services.async_accounting_rules import AsyncAccountingRulesService
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
    NO_ACCOUNTING_COUNTERPARTY,
)
from rotkehlchen.db.filtering import AccountingRulesFilterQuery
from rotki2.db.models.user.accounting import AccountingRule, LinkedRuleProperty
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType


@pytest.fixture
async def accounting_rule_repository(async_session: AsyncSession) -> AsyncAccountingRuleRepository:
    """Create an async accounting rule repository instance."""
    return AsyncAccountingRuleRepository(async_session)


@pytest.fixture
async def accounting_rules_service(
    accounting_rule_repository: AsyncAccountingRuleRepository,
) -> AsyncAccountingRulesService:
    """Create an async accounting rules service instance."""
    return AsyncAccountingRulesService(
        accounting_rule_repository=accounting_rule_repository,
        accountant=None,
    )


@pytest.fixture
async def sample_rule() -> BaseEventSettings:
    """Create a sample rule for testing."""
    return BaseEventSettings(
        taxable=True,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=True,
        accounting_treatment=TxAccountingTreatment.SWAP,
    )


@pytest.fixture
async def sample_links() -> dict[LINKABLE_ACCOUNTING_PROPERTIES, LINKABLE_ACCOUNTING_SETTINGS_NAME]:
    """Create sample links for testing."""
    return {
        'taxable': 'include_crypto2crypto',
        'count_cost_basis_pnl': 'include_gas_costs',
    }


class TestAsyncAccountingRuleRepository:
    """Test async accounting rule repository functionality."""

    async def test_add_accounting_rule(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
        sample_rule: BaseEventSettings,
        sample_links: dict,
    ):
        """Test adding a new accounting rule."""
        # Add rule
        rule_id = await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links=sample_links,
        )
        
        assert rule_id > 0
        
        # Verify rule was created
        rule = await accounting_rule_repository.get(rule_id)
        assert rule is not None
        assert rule.type == HistoryEventType.TRADE.serialize()
        assert rule.subtype == HistoryEventSubType.SPEND.serialize()
        assert rule.counterparty == 'uniswap'
        assert rule.taxable is True
        assert rule.count_entire_amount_spend is False
        assert rule.count_cost_basis_pnl is True
        assert rule.accounting_treatment == TxAccountingTreatment.SWAP.serialize_for_db()
        
        # Verify links were created
        rule_with_links = await accounting_rule_repository.get_rule_with_links(rule_id)
        assert rule_with_links is not None
        rule_obj, links = rule_with_links
        assert len(links) == 2
        
        link_dict = {link.property_name: link.setting_name for link in links}
        assert link_dict['taxable'] == 'include_crypto2crypto'
        assert link_dict['count_cost_basis_pnl'] == 'include_gas_costs'

    async def test_add_duplicate_rule_fails(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
        sample_rule: BaseEventSettings,
    ):
        """Test that adding a duplicate rule fails."""
        # Add initial rule
        await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links={},
        )
        
        # Attempt to add duplicate
        with pytest.raises(InputError, match='already exists'):
            await accounting_rule_repository.add_accounting_rule(
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                counterparty='uniswap',
                rule=sample_rule,
                links={},
            )

    async def test_add_rule_with_force_update(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
        sample_rule: BaseEventSettings,
    ):
        """Test adding a rule with force update."""
        # Add initial rule
        rule_id = await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links={},
        )
        
        # Update with force
        updated_rule = BaseEventSettings(
            taxable=False,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=False,
            accounting_treatment=None,
        )
        
        new_rule_id = await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=updated_rule,
            links={'taxable': 'include_gas_costs'},
            force_update=True,
        )
        
        # Should be same rule ID
        assert new_rule_id == rule_id
        
        # Verify update
        rule = await accounting_rule_repository.get(rule_id)
        assert rule is not None
        assert rule.taxable is False
        assert rule.count_entire_amount_spend is True
        assert rule.count_cost_basis_pnl is False
        assert rule.accounting_treatment is None

    async def test_remove_accounting_rule(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
        sample_rule: BaseEventSettings,
        sample_links: dict,
    ):
        """Test removing an accounting rule."""
        # Add rule
        rule_id = await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links=sample_links,
        )
        
        # Remove rule
        event_type, event_subtype, counterparty = await accounting_rule_repository.remove_accounting_rule(rule_id)
        
        assert event_type == HistoryEventType.TRADE
        assert event_subtype == HistoryEventSubType.SPEND
        assert counterparty == 'uniswap'
        
        # Verify rule is gone
        rule = await accounting_rule_repository.get(rule_id)
        assert rule is None
        
        # Verify links are gone
        session = accounting_rule_repository.session
        result = await session.execute(
            select(LinkedRuleProperty).where(LinkedRuleProperty.accounting_rule == rule_id)
        )
        links = result.all()
        assert len(links) == 0

    async def test_remove_nonexistent_rule_fails(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
    ):
        """Test that removing a nonexistent rule fails."""
        with pytest.raises(InputError, match='does not exist'):
            await accounting_rule_repository.remove_accounting_rule(999)

    async def test_update_accounting_rule(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
        sample_rule: BaseEventSettings,
    ):
        """Test updating an accounting rule."""
        # Add initial rule
        rule_id = await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links={'taxable': 'include_crypto2crypto'},
        )
        
        # Update rule
        updated_rule = BaseEventSettings(
            taxable=False,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=False,
            accounting_treatment=TxAccountingTreatment.SWAP,
        )
        
        await accounting_rule_repository.update_accounting_rule(
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.RECEIVE,
            counterparty='compound',
            rule=updated_rule,
            links={'count_entire_amount_spend': 'include_gas_costs'},
            identifier=rule_id,
        )
        
        # Verify update
        rule = await accounting_rule_repository.get(rule_id)
        assert rule is not None
        assert rule.type == HistoryEventType.DEPOSIT.serialize()
        assert rule.subtype == HistoryEventSubType.RECEIVE.serialize()
        assert rule.counterparty == 'compound'
        assert rule.taxable is False
        assert rule.count_entire_amount_spend is True
        
        # Verify links updated
        rule_with_links = await accounting_rule_repository.get_rule_with_links(rule_id)
        assert rule_with_links is not None
        _, links = rule_with_links
        assert len(links) == 1
        assert links[0].property_name == 'count_entire_amount_spend'
        assert links[0].setting_name == 'include_gas_costs'

    async def test_get_rules_for_event(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
        sample_rule: BaseEventSettings,
    ):
        """Test getting rules for specific event criteria."""
        # Add multiple rules
        await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links={},
        )
        
        await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='sushiswap',
            rule=sample_rule,
            links={},
        )
        
        await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            counterparty='uniswap',
            rule=sample_rule,
            links={},
        )
        
        # Test various queries
        rules = await accounting_rule_repository.get_rules_for_event(
            event_type=HistoryEventType.TRADE,
        )
        assert len(rules) == 3
        
        rules = await accounting_rule_repository.get_rules_for_event(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
        )
        assert len(rules) == 2
        
        rules = await accounting_rule_repository.get_rules_for_event(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
        )
        assert len(rules) == 1
        assert rules[0].counterparty == 'uniswap'

    async def test_get_all_rules_with_filter(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
        sample_rule: BaseEventSettings,
    ):
        """Test getting all rules with filter."""
        # Add multiple rules
        for i in range(5):
            await accounting_rule_repository.add_accounting_rule(
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                counterparty=f'dex_{i}',
                rule=sample_rule,
                links={},
            )
        
        # Get all rules
        rules, total = await accounting_rule_repository.get_all_rules_with_filter()
        assert len(rules) == 5
        assert total == 5
        
        # Test with filter
        filter_query = AccountingRulesFilterQuery.make(
            event_types=[HistoryEventType.TRADE],
            limit=3,
        )
        rules, total = await accounting_rule_repository.get_all_rules_with_filter(filter_query)
        assert len(rules) == 3
        assert total == 5

    async def test_rule_with_no_counterparty(
        self,
        accounting_rule_repository: AsyncAccountingRuleRepository,
        sample_rule: BaseEventSettings,
    ):
        """Test handling rules with no counterparty."""
        # Add rule without counterparty
        rule_id = await accounting_rule_repository.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty=None,
            rule=sample_rule,
            links={},
        )
        
        # Verify it's stored correctly
        rule = await accounting_rule_repository.get(rule_id)
        assert rule is not None
        assert rule.counterparty == NO_ACCOUNTING_COUNTERPARTY
        
        # Remove and check return value
        event_type, event_subtype, counterparty = await accounting_rule_repository.remove_accounting_rule(rule_id)
        assert counterparty is None


class TestAsyncAccountingRulesService:
    """Test async accounting rules service functionality."""

    async def test_add_accounting_rule_service(
        self,
        accounting_rules_service: AsyncAccountingRulesService,
        sample_rule: BaseEventSettings,
        sample_links: dict,
    ):
        """Test adding a rule through the service."""
        result = await accounting_rules_service.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links=sample_links,
        )
        
        assert 'identifier' in result
        assert result['identifier'] > 0
        assert 'Successfully added' in result['message']

    async def test_remove_accounting_rule_service(
        self,
        accounting_rules_service: AsyncAccountingRulesService,
        sample_rule: BaseEventSettings,
    ):
        """Test removing a rule through the service."""
        # Add rule
        add_result = await accounting_rules_service.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links={},
        )
        
        rule_id = add_result['identifier']
        
        # Remove rule
        remove_result = await accounting_rules_service.remove_accounting_rule(rule_id)
        assert 'Successfully removed' in remove_result['message']

    async def test_update_accounting_rule_service(
        self,
        accounting_rules_service: AsyncAccountingRulesService,
        sample_rule: BaseEventSettings,
    ):
        """Test updating a rule through the service."""
        # Add rule
        add_result = await accounting_rules_service.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links={},
        )
        
        rule_id = add_result['identifier']
        
        # Update rule
        updated_rule = BaseEventSettings(
            taxable=False,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=False,
            accounting_treatment=None,
        )
        
        update_result = await accounting_rules_service.update_accounting_rule(
            rule_id=rule_id,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.RECEIVE,
            counterparty='compound',
            rule=updated_rule,
            links={},
        )
        
        assert f'Successfully updated accounting rule {rule_id}' == update_result['message']

    async def test_get_accounting_rules_service(
        self,
        accounting_rules_service: AsyncAccountingRulesService,
        sample_rule: BaseEventSettings,
    ):
        """Test getting rules through the service."""
        # Add multiple rules
        for i in range(3):
            await accounting_rules_service.add_accounting_rule(
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                counterparty=f'dex_{i}',
                rule=sample_rule,
                links={},
            )
        
        # Get all rules
        result = await accounting_rules_service.get_accounting_rules()
        
        assert 'entries' in result
        assert 'entries_found' in result
        assert 'entries_total' in result
        assert len(result['entries']) == 3
        assert result['entries_found'] == 3
        assert result['entries_total'] == 3
        
        # Verify serialization
        for entry in result['entries']:
            assert 'identifier' in entry
            assert 'event_type' in entry
            assert 'event_subtype' in entry
            assert 'counterparty' in entry
            assert 'taxable' in entry
            assert 'count_entire_amount_spend' in entry
            assert 'count_cost_basis_pnl' in entry
            assert 'accounting_treatment' in entry
            assert 'links' in entry

    async def test_get_specific_accounting_rule_service(
        self,
        accounting_rules_service: AsyncAccountingRulesService,
        sample_rule: BaseEventSettings,
        sample_links: dict,
    ):
        """Test getting a specific rule through the service."""
        # Add rule
        add_result = await accounting_rules_service.add_accounting_rule(
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            counterparty='uniswap',
            rule=sample_rule,
            links=sample_links,
        )
        
        rule_id = add_result['identifier']
        
        # Get specific rule
        rule_data = await accounting_rules_service.get_accounting_rule(rule_id)
        
        assert rule_data['identifier'] == rule_id
        assert rule_data['event_type'] == HistoryEventType.TRADE
        assert rule_data['event_subtype'] == HistoryEventSubType.SPEND
        assert rule_data['counterparty'] == 'uniswap'
        assert rule_data['taxable'] is True
        assert rule_data['count_entire_amount_spend'] is False
        assert rule_data['count_cost_basis_pnl'] is True
        assert rule_data['accounting_treatment'] == TxAccountingTreatment.SWAP
        assert rule_data['links'] == sample_links

    async def test_get_nonexistent_rule_service(
        self,
        accounting_rules_service: AsyncAccountingRulesService,
    ):
        """Test getting a nonexistent rule through the service."""
        with pytest.raises(InputError, match='not found'):
            await accounting_rules_service.get_accounting_rule(999)

    async def test_export_import_accounting_rules(
        self,
        accounting_rules_service: AsyncAccountingRulesService,
        sample_rule: BaseEventSettings,
        sample_links: dict,
    ):
        """Test exporting and importing rules."""
        # Add some rules
        for i in range(3):
            await accounting_rules_service.add_accounting_rule(
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.SPEND,
                counterparty=f'dex_{i}',
                rule=sample_rule,
                links=sample_links if i == 0 else {},
            )
        
        # Export rules
        exported = await accounting_rules_service.export_accounting_rules()
        assert 'rules' in exported
        assert len(exported['rules']) == 3
        
        # Clear existing rules
        all_rules = await accounting_rules_service.get_accounting_rules()
        for rule in all_rules['entries']:
            await accounting_rules_service.remove_accounting_rule(rule['identifier'])
        
        # Import rules back
        import_result = await accounting_rules_service.import_accounting_rules(
            rules=exported['rules'],
            force_update=False,
        )
        
        assert import_result['imported'] == 3
        assert len(import_result['errors']) == 0
        
        # Verify imported rules
        result = await accounting_rules_service.get_accounting_rules()
        assert len(result['entries']) == 3

    async def test_import_invalid_rules(
        self,
        accounting_rules_service: AsyncAccountingRulesService,
    ):
        """Test importing invalid rules."""
        invalid_rules = [
            {
                'event_type': 'INVALID_TYPE',
                'event_subtype': 'spend',
                'counterparty': 'test',
                'taxable': True,
                'count_entire_amount_spend': False,
                'count_cost_basis_pnl': True,
                'accounting_treatment': None,
                'links': {},
            }
        ]
        
        result = await accounting_rules_service.import_accounting_rules(
            rules=invalid_rules,
            force_update=False,
        )
        
        assert result['imported'] == 0
        assert len(result['errors']) == 1
        assert 'INVALID_TYPE' in result['errors'][0]['rule']
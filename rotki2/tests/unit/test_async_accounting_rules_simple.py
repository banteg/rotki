"""Simple tests for async accounting rules without model loading issues."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.repositories.async_accounting_rule import AsyncAccountingRuleRepository
from rotki2.api.v2.services.async_accounting_rules import AsyncAccountingRulesService
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY
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


@pytest.mark.asyncio
async def test_add_accounting_rule_raw_sql(async_session: AsyncSession):
    """Test adding a rule using raw SQL to avoid model loading issues."""
    # Insert a rule using raw SQL
    result = await async_session.execute(
        text("""
            INSERT INTO accounting_rules (
                type, subtype, counterparty, taxable, 
                count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
            ) VALUES (:type, :subtype, :counterparty, :taxable, 
                    :count_entire_amount_spend, :count_cost_basis_pnl, :accounting_treatment)
            RETURNING identifier
        """),
        {
            'type': HistoryEventType.TRADE.serialize(),
            'subtype': HistoryEventSubType.SPEND.serialize(),
            'counterparty': 'uniswap',
            'taxable': 1,  # True
            'count_entire_amount_spend': 0,  # False
            'count_cost_basis_pnl': 1,  # True
            'accounting_treatment': TxAccountingTreatment.SWAP.serialize_for_db(),
        }
    )
    
    rule_id = result.scalar()
    assert rule_id > 0
    
    # Verify the rule was created
    result = await async_session.execute(
        text("SELECT * FROM accounting_rules WHERE identifier = :id"),
        {'id': rule_id}
    )
    row = result.fetchone()
    assert row is not None
    assert row[1] == HistoryEventType.TRADE.serialize()  # type
    assert row[2] == HistoryEventSubType.SPEND.serialize()  # subtype
    assert row[3] == 'uniswap'  # counterparty
    assert row[4] == 1  # taxable
    assert row[5] == 0  # count_entire_amount_spend
    assert row[6] == 1  # count_cost_basis_pnl
    assert row[7] == TxAccountingTreatment.SWAP.serialize_for_db()  # accounting_treatment


@pytest.mark.asyncio  
async def test_add_accounting_rule_with_links_raw_sql(async_session: AsyncSession):
    """Test adding a rule with links using raw SQL."""
    # Insert a rule
    result = await async_session.execute(text("""
        INSERT INTO accounting_rules (
            type, subtype, counterparty, taxable, 
            count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING identifier
    """, [
        HistoryEventType.TRADE.serialize(),
        HistoryEventSubType.SPEND.serialize(),
        'uniswap',
        1,
        0,
        1,
        None,
    ])
    
    rule_id = result.scalar()
    
    # Insert links
    await async_session.execute(text("""
        INSERT INTO linked_rules_properties (
            accounting_rule, property_name, setting_name
        ) VALUES (?, ?, ?)
    """, [rule_id, 'taxable', 'include_crypto2crypto'])
    
    await async_session.execute(text("""
        INSERT INTO linked_rules_properties (
            accounting_rule, property_name, setting_name
        ) VALUES (?, ?, ?)
    """, [rule_id, 'count_cost_basis_pnl', 'include_gas_costs'])
    
    await async_session.commit()
    
    # Verify links were created
    result = await async_session.execute(text(
        "SELECT * FROM linked_rules_properties WHERE accounting_rule = ?", [rule_id]
    )
    rows = result.fetchall()
    assert len(rows) == 2
    
    links = {row[2]: row[3] for row in rows}  # property_name: setting_name
    assert links['taxable'] == 'include_crypto2crypto'
    assert links['count_cost_basis_pnl'] == 'include_gas_costs'


@pytest.mark.asyncio
async def test_duplicate_rule_fails_raw_sql(async_session: AsyncSession):
    """Test that adding a duplicate rule fails using raw SQL."""
    # Insert initial rule
    await async_session.execute(text("""
        INSERT INTO accounting_rules (
            type, subtype, counterparty, taxable, 
            count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        HistoryEventType.TRADE.serialize(),
        HistoryEventSubType.SPEND.serialize(),
        'uniswap',
        1, 0, 1, None,
    ])
    
    await async_session.commit()
    
    # Attempt to insert duplicate - should fail due to UNIQUE constraint
    with pytest.raises(Exception):  # IntegrityError
        await async_session.execute(text("""
            INSERT INTO accounting_rules (
                type, subtype, counterparty, taxable, 
                count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            HistoryEventType.TRADE.serialize(),
            HistoryEventSubType.SPEND.serialize(),
            'uniswap',
            0, 1, 0, None,
        ])
        await async_session.commit()


@pytest.mark.asyncio
async def test_remove_rule_raw_sql(async_session: AsyncSession):
    """Test removing a rule using raw SQL."""
    # Insert a rule with links
    result = await async_session.execute(text("""
        INSERT INTO accounting_rules (
            type, subtype, counterparty, taxable, 
            count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING identifier
    """, [
        HistoryEventType.TRADE.serialize(),
        HistoryEventSubType.SPEND.serialize(),
        'uniswap',
        1, 0, 1, None,
    ])
    
    rule_id = result.scalar()
    
    # Add a link
    await async_session.execute(text("""
        INSERT INTO linked_rules_properties (
            accounting_rule, property_name, setting_name
        ) VALUES (?, ?, ?)
    """, [rule_id, 'taxable', 'include_crypto2crypto'])
    
    await async_session.commit()
    
    # Delete the rule
    await async_session.execute(text(
        "DELETE FROM linked_rules_properties WHERE accounting_rule = ?", [rule_id]
    )
    await async_session.execute(text(
        "DELETE FROM accounting_rules WHERE identifier = ?", [rule_id]
    )
    await async_session.commit()
    
    # Verify rule is gone
    result = await async_session.execute(text(
        "SELECT * FROM accounting_rules WHERE identifier = ?", [rule_id]
    )
    assert result.fetchone() is None
    
    # Verify links are gone
    result = await async_session.execute(text(
        "SELECT * FROM linked_rules_properties WHERE accounting_rule = ?", [rule_id]
    )
    assert result.fetchone() is None


@pytest.mark.asyncio
async def test_update_rule_raw_sql(async_session: AsyncSession):
    """Test updating a rule using raw SQL."""
    # Insert initial rule
    result = await async_session.execute(text("""
        INSERT INTO accounting_rules (
            type, subtype, counterparty, taxable, 
            count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING identifier
    """, [
        HistoryEventType.TRADE.serialize(),
        HistoryEventSubType.SPEND.serialize(),
        'uniswap',
        1, 0, 1, None,
    ])
    
    rule_id = result.scalar()
    await async_session.commit()
    
    # Update the rule
    await async_session.execute(text("""
        UPDATE accounting_rules 
        SET type=?, subtype=?, counterparty=?, taxable=?, 
            count_entire_amount_spend=?, count_cost_basis_pnl=?, accounting_treatment=?
        WHERE identifier=?
    """, [
        HistoryEventType.DEPOSIT.serialize(),
        HistoryEventSubType.RECEIVE.serialize(),
        'compound',
        0, 1, 0, TxAccountingTreatment.SWAP.serialize_for_db(),
        rule_id,
    ])
    await async_session.commit()
    
    # Verify update
    result = await async_session.execute(text(
        "SELECT * FROM accounting_rules WHERE identifier = ?", [rule_id]
    )
    row = result.fetchone()
    assert row[1] == HistoryEventType.DEPOSIT.serialize()
    assert row[2] == HistoryEventSubType.RECEIVE.serialize()
    assert row[3] == 'compound'
    assert row[4] == 0
    assert row[5] == 1
    assert row[6] == 0
    assert row[7] == TxAccountingTreatment.SWAP.serialize_for_db()


@pytest.mark.asyncio
async def test_query_rules_by_event_raw_sql(async_session: AsyncSession):
    """Test querying rules by event criteria using raw SQL."""
    # Insert multiple rules
    rules_data = [
        (HistoryEventType.TRADE, HistoryEventSubType.SPEND, 'uniswap'),
        (HistoryEventType.TRADE, HistoryEventSubType.SPEND, 'sushiswap'),
        (HistoryEventType.TRADE, HistoryEventSubType.RECEIVE, 'uniswap'),
        (HistoryEventType.DEPOSIT, HistoryEventSubType.RECEIVE, 'compound'),
    ]
    
    for event_type, event_subtype, counterparty in rules_data:
        await async_session.execute(text("""
            INSERT INTO accounting_rules (
                type, subtype, counterparty, taxable, 
                count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            event_type.serialize(),
            event_subtype.serialize(),
            counterparty,
            1, 0, 1, None,
        ])
    
    await async_session.commit()
    
    # Query all TRADE rules
    result = await async_session.execute(text(
        "SELECT COUNT(*) FROM accounting_rules WHERE type = ?",
        [HistoryEventType.TRADE.serialize()]
    )
    assert result.scalar() == 3
    
    # Query TRADE + SPEND rules
    result = await async_session.execute(text(
        "SELECT COUNT(*) FROM accounting_rules WHERE type = ? AND subtype = ?",
        [HistoryEventType.TRADE.serialize(), HistoryEventSubType.SPEND.serialize()]
    )
    assert result.scalar() == 2
    
    # Query specific counterparty
    result = await async_session.execute(text(
        "SELECT COUNT(*) FROM accounting_rules WHERE type = ? AND subtype = ? AND counterparty = ?",
        [HistoryEventType.TRADE.serialize(), HistoryEventSubType.SPEND.serialize(), 'uniswap']
    )
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_rule_with_no_counterparty_raw_sql(async_session: AsyncSession):
    """Test handling rules with no counterparty using raw SQL."""
    # Insert rule without counterparty (use NO_ACCOUNTING_COUNTERPARTY)
    result = await async_session.execute(text("""
        INSERT INTO accounting_rules (
            type, subtype, counterparty, taxable, 
            count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING identifier
    """, [
        HistoryEventType.TRADE.serialize(),
        HistoryEventSubType.SPEND.serialize(),
        NO_ACCOUNTING_COUNTERPARTY,
        1, 0, 1, None,
    ])
    
    rule_id = result.scalar()
    await async_session.commit()
    
    # Verify it's stored correctly
    result = await async_session.execute(text(
        "SELECT counterparty FROM accounting_rules WHERE identifier = ?", [rule_id]
    )
    assert result.scalar() == NO_ACCOUNTING_COUNTERPARTY
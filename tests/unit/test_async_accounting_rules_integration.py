"""Integration tests for async accounting rules that avoid model loading issues."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType


@pytest.mark.asyncio
async def test_accounting_rules_basic_operations(async_session: AsyncSession):
    """Test basic CRUD operations for accounting rules using raw SQL."""
    
    # 1. Test INSERT
    result = await async_session.execute(
        text("""
            INSERT INTO accounting_rules (
                type, subtype, counterparty, taxable, 
                count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
            ) VALUES (:type, :subtype, :counterparty, :taxable, 
                    :spend, :pnl, :treatment)
            RETURNING identifier
        """),
        {
            'type': 'trade',
            'subtype': 'spend',
            'counterparty': 'uniswap',
            'taxable': 1,
            'spend': 0,
            'pnl': 1,
            'treatment': 'swap',
        }
    )
    rule_id = result.scalar()
    assert rule_id > 0
    
    # 2. Test SELECT
    result = await async_session.execute(
        text("SELECT * FROM accounting_rules WHERE identifier = :id"),
        {'id': rule_id}
    )
    row = result.fetchone()
    assert row is not None
    assert row[1] == 'trade'  # type
    assert row[2] == 'spend'  # subtype
    assert row[3] == 'uniswap'  # counterparty
    
    # 3. Test UPDATE
    await async_session.execute(
        text("""
            UPDATE accounting_rules 
            SET counterparty = :new_counterparty
            WHERE identifier = :id
        """),
        {'new_counterparty': 'sushiswap', 'id': rule_id}
    )
    await async_session.commit()
    
    # Verify update
    result = await async_session.execute(
        text("SELECT counterparty FROM accounting_rules WHERE identifier = :id"),
        {'id': rule_id}
    )
    assert result.scalar() == 'sushiswap'
    
    # 4. Test DELETE
    await async_session.execute(
        text("DELETE FROM accounting_rules WHERE identifier = :id"),
        {'id': rule_id}
    )
    await async_session.commit()
    
    # Verify deletion
    result = await async_session.execute(
        text("SELECT COUNT(*) FROM accounting_rules WHERE identifier = :id"),
        {'id': rule_id}
    )
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_accounting_rules_with_links(async_session: AsyncSession):
    """Test accounting rules with linked properties."""
    
    # Insert a rule
    result = await async_session.execute(
        text("""
            INSERT INTO accounting_rules (
                type, subtype, counterparty, taxable, 
                count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
            ) VALUES ('trade', 'spend', 'uniswap', 1, 0, 1, NULL)
            RETURNING identifier
        """)
    )
    rule_id = result.scalar()
    
    # Insert linked properties
    await async_session.execute(
        text("""
            INSERT INTO linked_rules_properties (
                accounting_rule, property_name, setting_name
            ) VALUES (:rule_id, :property, :setting)
        """),
        {
            'rule_id': rule_id,
            'property': 'taxable',
            'setting': 'include_crypto2crypto'
        }
    )
    await async_session.commit()
    
    # Verify link exists
    result = await async_session.execute(
        text("""
            SELECT property_name, setting_name 
            FROM linked_rules_properties 
            WHERE accounting_rule = :rule_id
        """),
        {'rule_id': rule_id}
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == 'taxable'
    assert row[1] == 'include_crypto2crypto'


@pytest.mark.asyncio
async def test_accounting_rules_unique_constraint(async_session: AsyncSession):
    """Test unique constraint on (type, subtype, counterparty)."""
    
    # Insert first rule
    await async_session.execute(
        text("""
            INSERT INTO accounting_rules (
                type, subtype, counterparty, taxable, 
                count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
            ) VALUES ('trade', 'spend', 'uniswap', 1, 0, 1, NULL)
        """)
    )
    await async_session.commit()
    
    # Try to insert duplicate - should fail
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        await async_session.execute(
            text("""
                INSERT INTO accounting_rules (
                    type, subtype, counterparty, taxable, 
                    count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
                ) VALUES ('trade', 'spend', 'uniswap', 0, 1, 0, NULL)
            """)
        )
        await async_session.commit()


@pytest.mark.asyncio
async def test_accounting_rules_no_counterparty(async_session: AsyncSession):
    """Test rules without specific counterparty."""
    
    # Insert rule with NO_ACCOUNTING_COUNTERPARTY
    result = await async_session.execute(
        text("""
            INSERT INTO accounting_rules (
                type, subtype, counterparty, taxable, 
                count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment
            ) VALUES (:type, :subtype, :counterparty, 1, 0, 1, NULL)
            RETURNING identifier
        """),
        {
            'type': 'trade',
            'subtype': 'spend',
            'counterparty': NO_ACCOUNTING_COUNTERPARTY
        }
    )
    rule_id = result.scalar()
    
    # Verify it's stored correctly
    result = await async_session.execute(
        text("SELECT counterparty FROM accounting_rules WHERE identifier = :id"),
        {'id': rule_id}
    )
    assert result.scalar() == NO_ACCOUNTING_COUNTERPARTY
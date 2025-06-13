"""Unit test fixtures."""
import pytest
import pytest_asyncio
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlmodel import SQLModel


@pytest_asyncio.fixture
async def async_engine():
    """Create an async test database engine."""
    # Use in-memory SQLite database for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # Create only the necessary tables
    async with engine.begin() as conn:
        # Create tables using raw SQL to avoid relationship issues
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS settings (
                name VARCHAR(24) PRIMARY KEY NOT NULL,
                value TEXT
            )
        """)
        
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS accounting_rules (
                identifier INTEGER PRIMARY KEY,
                type TEXT NOT NULL,
                subtype TEXT NOT NULL,
                counterparty TEXT NOT NULL,
                taxable INTEGER NOT NULL CHECK (taxable IN (0, 1)),
                count_entire_amount_spend INTEGER NOT NULL CHECK (count_entire_amount_spend IN (0, 1)),
                count_cost_basis_pnl INTEGER NOT NULL CHECK (count_cost_basis_pnl IN (0, 1)),
                accounting_treatment TEXT,
                UNIQUE(type, subtype, counterparty)
            )
        """)
        
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS linked_rules_properties (
                identifier INTEGER PRIMARY KEY,
                accounting_rule INTEGER,
                property_name TEXT NOT NULL,
                setting_name TEXT NOT NULL,
                FOREIGN KEY (accounting_rule) REFERENCES accounting_rules(identifier),
                FOREIGN KEY (setting_name) REFERENCES settings(name)
            )
        """)
        
        # Create history events tables
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS history_events (
                identifier INTEGER PRIMARY KEY,
                event_identifier TEXT NOT NULL,
                sequence_index INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                location TEXT NOT NULL,
                location_label TEXT,
                asset TEXT NOT NULL,
                amount TEXT NOT NULL,
                usd_value TEXT NOT NULL,
                notes TEXT,
                type TEXT NOT NULL,
                subtype TEXT,
                entry_type INTEGER NOT NULL DEFAULT 1,
                UNIQUE(event_identifier, sequence_index)
            )
        """)
        
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS history_events_mappings (
                parent_identifier INTEGER NOT NULL,
                name TEXT NOT NULL,
                value INTEGER NOT NULL,
                FOREIGN KEY(parent_identifier) REFERENCES history_events(identifier) ON DELETE CASCADE,
                PRIMARY KEY(parent_identifier, name)
            )
        """)
        
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS evm_events_info (
                identifier INTEGER PRIMARY KEY,
                tx_hash TEXT NOT NULL,
                counterparty TEXT,
                product TEXT,
                address TEXT,
                FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON DELETE CASCADE
            )
        """)
        
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS eth_staking_events_info (
                identifier INTEGER PRIMARY KEY,
                validator_index INTEGER NOT NULL,
                is_exit_or_blocknumber INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON DELETE CASCADE
            )
        """)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine: AsyncEngine):
    """Create an async database session for tests."""
    async with AsyncSession(async_engine) as session:
        # Add default settings needed for accounting rules using raw SQL
        from sqlalchemy import text
        await session.execute(
            text("INSERT INTO settings (name, value) VALUES ('include_crypto2crypto', 'True')")
        )
        await session.execute(
            text("INSERT INTO settings (name, value) VALUES ('include_gas_costs', 'True')")
        )
        await session.commit()
        
        yield session
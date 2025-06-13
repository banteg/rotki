"""FastAPI dependency injection"""
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import Session

from rotki2.api.v2.repositories.accounting_rule import AccountingRuleRepository
from rotki2.api.v2.repositories.addressbook import AddressBookRepository
from rotki2.api.v2.repositories.blockchain_account import BlockchainAccountRepository
from rotki2.api.v2.repositories.eth2 import Eth2Repository
from rotki2.api.v2.repositories.evm_transaction import EvmTransactionRepository
from rotki2.api.v2.repositories.nft import NFTRepository
from rotki2.api.v2.repositories.settings import MultiSettingsRepository, SettingsRepository
from rotki2.api.v2.repositories.tag import TagRepository
from rotki2.api.v2.services.auth import AuthService
from rotki2.api.v2.services.database import DatabaseService
from rotkehlchen.db.drivers.gevent import DBConnection

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.data_handler import DataHandler
    from rotkehlchen.exchanges.manager import ExchangeManager
    from rotkehlchen.history.manager import HistoryQueryingManager
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.tasks.manager import TaskManager


def get_rotkehlchen(request: Request) -> 'Rotkehlchen':
    """Get Rotkehlchen instance from request state"""
    if not hasattr(request.app.state, 'rotkehlchen'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Rotkehlchen instance not initialized',
        )
    return request.app.state.rotkehlchen


def get_db_connection(request: Request) -> DBConnection:
    """Get database connection from request state"""
    rotkehlchen = get_rotkehlchen(request)
    if not rotkehlchen.user_is_logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='No user is logged in',
        )
    return rotkehlchen.data.db


def get_db_session(request: Request) -> Session:
    """Get SQLModel session from request state"""
    db_connection = get_db_connection(request)
    return db_connection.session_manager.user_session


def get_database_service(
    db_connection: Annotated[DBConnection, Depends(get_db_connection)],
) -> DatabaseService:
    """Get database service instance"""
    return DatabaseService(db_connection)


async def get_auth_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AuthService:
    """Get authentication service instance"""
    return AuthService(db_service, session)


def get_data_handler(request: Request) -> 'DataHandler':
    """Get DataHandler instance"""
    rotkehlchen = get_rotkehlchen(request)
    return rotkehlchen.data


def get_chains_aggregator(request: Request) -> 'ChainsAggregator':
    """Get ChainsAggregator instance"""
    rotkehlchen = get_rotkehlchen(request)
    if not rotkehlchen.user_is_logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='No user is logged in',
        )
    return rotkehlchen.chains_aggregator


def get_exchange_manager(request: Request) -> 'ExchangeManager':
    """Get ExchangeManager instance"""
    rotkehlchen = get_rotkehlchen(request)
    return rotkehlchen.exchange_manager


def get_history_querying_manager(request: Request) -> 'HistoryQueryingManager':
    """Get HistoryQueryingManager instance"""
    rotkehlchen = get_rotkehlchen(request)
    if not rotkehlchen.user_is_logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='No user is logged in',
        )
    return rotkehlchen.history_querying_manager


def get_accountant(request: Request) -> 'Accountant':
    """Get Accountant instance"""
    rotkehlchen = get_rotkehlchen(request)
    if not rotkehlchen.user_is_logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='No user is logged in',
        )
    return rotkehlchen.accountant


def get_task_manager(request: Request) -> 'TaskManager':
    """Get TaskManager instance"""
    rotkehlchen = get_rotkehlchen(request)
    if not rotkehlchen.user_is_logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='No user is logged in',
        )
    if rotkehlchen.task_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Task manager not initialized',
        )
    return rotkehlchen.task_manager


def get_rotki_notifier(request: Request) -> 'RotkiNotifier':
    """Get RotkiNotifier instance for WebSocket notifications"""
    if not hasattr(request.app.state, 'rotki_notifier'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Notifier not initialized',
        )
    return request.app.state.rotki_notifier


def get_history_service(
    db_connection: Annotated[DBConnection, Depends(get_db_connection)],
    session: Annotated[Session, Depends(get_db_session)],
    history_manager: Annotated['HistoryQueryingManager', Depends(get_history_querying_manager)],
    task_manager: Annotated['TaskManager', Depends(get_task_manager)],
    notifier: Annotated['RotkiNotifier', Depends(get_rotki_notifier)],
) -> 'HistoryService':
    """Get history service instance with repositories"""
    from rotki2.api.v2.services.history import HistoryService
    return HistoryService(
        db_connection=db_connection,
        session=session,
        history_manager=history_manager,
        task_manager=task_manager,
        notifier=notifier,
    )


async def require_logged_in_user(  # noqa: RUF029
    request: Request,
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> str:
    """Dependency to ensure user is logged in"""
    if not rotkehlchen.user_is_logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='No user is logged in',
        )

    # Check for API key authentication
    api_key = request.headers.get('X-API-Key')
    if api_key:
        # TODO: Implement API key authentication
        # This would involve checking the API key against the database
        pass

    # Return the current username
    return rotkehlchen.data.username


def get_optional_logged_in_user(
    request: Request,
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
) -> str | None:
    """Get the current user if logged in, but don't require it"""
    if not rotkehlchen.user_is_logged_in:
        return None
    
    # Check for API key authentication
    api_key = request.headers.get('X-API-Key')
    if api_key:
        # TODO: Implement API key authentication
        pass
    
    return rotkehlchen.data.username


# Repository dependencies
def get_accounting_rule_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> AccountingRuleRepository:
    """Get AccountingRuleRepository instance"""
    return AccountingRuleRepository(session)


def get_blockchain_account_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> BlockchainAccountRepository:
    """Get BlockchainAccountRepository instance"""
    return BlockchainAccountRepository(session)


def get_nft_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> NFTRepository:
    """Get NFTRepository instance"""
    return NFTRepository(session)


def get_evm_transaction_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> EvmTransactionRepository:
    """Get EvmTransactionRepository instance"""
    return EvmTransactionRepository(session)


def get_eth2_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Eth2Repository:
    """Get Eth2Repository instance"""
    return Eth2Repository(session)


def get_tag_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> TagRepository:
    """Get TagRepository instance"""
    return TagRepository(session)


def get_settings_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> SettingsRepository:
    """Get SettingsRepository instance"""
    return SettingsRepository(session)


def get_multi_settings_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> MultiSettingsRepository:
    """Get MultiSettingsRepository instance"""
    return MultiSettingsRepository(session)


def get_addressbook_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> AddressBookRepository:
    """Get AddressBookRepository instance"""
    return AddressBookRepository(session)


# Async database dependencies
async def get_async_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Get async database session.
    
    This dependency provides an async session for database operations.
    It will be initialized once the async engine is set up in the application.
    """
    # Check if user is logged in first
    rotkehlchen = get_rotkehlchen(request)
    if not rotkehlchen.user_is_logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='No user is logged in',
        )
    
    if not hasattr(request.app.state, 'async_session_factory'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Async database not initialized',
        )

    session_factory: async_sessionmaker[AsyncSession] = request.app.state.async_session_factory

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for consistency with naming convention
get_session = get_async_session


# Async repository dependencies
def get_async_ens_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> 'ENSRepository':
    """Get ENSRepository instance"""
    from rotki2.api.v2.repositories.ens import ENSRepository
    return ENSRepository(session)


def get_async_addressbook_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> 'AddressBookRepository':
    """Get AddressBookRepository instance"""
    from rotki2.api.v2.repositories.addressbook import AddressBookRepository
    return AddressBookRepository(session)


def get_async_loopring_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> 'LoopringRepository':
    """Get LoopringRepository instance"""
    from rotki2.api.v2.repositories.loopring import LoopringRepository
    return LoopringRepository(session)


def get_async_accounting_rule_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> 'AccountingRuleRepository':
    """Get AccountingRuleRepository instance"""
    from rotki2.api.v2.repositories.accounting_rule import AccountingRuleRepository
    return AccountingRuleRepository(session)


# Async service dependencies
def get_async_ens_service(
    ens_repository: Annotated['ENSRepository', Depends(get_async_ens_repository)],
) -> 'AsyncENSService':
    """Get AsyncENSService instance"""
    from rotki2.api.v2.services.async_ens import AsyncENSService
    return AsyncENSService(ens_repository)


def get_async_addressbook_service(
    addressbook_repository: Annotated['AddressBookRepository', Depends(get_async_addressbook_repository)],
) -> 'AsyncAddressBookService':
    """Get AsyncAddressBookService instance"""
    from rotki2.api.v2.services.async_addressbook import AsyncAddressBookService
    return AsyncAddressBookService(addressbook_repository)


def get_async_loopring_service(
    loopring_repository: Annotated['LoopringRepository', Depends(get_async_loopring_repository)],
) -> 'AsyncLoopringService':
    """Get AsyncLoopringService instance"""
    from rotki2.api.v2.services.async_loopring import AsyncLoopringService
    return AsyncLoopringService(loopring_repository)


def get_async_accounting_rules_service(
    accounting_rule_repository: Annotated['AccountingRuleRepository', Depends(get_async_accounting_rule_repository)],
    accountant: Annotated['Accountant', Depends(get_accountant)],
) -> 'AsyncAccountingRulesService':
    """Get AsyncAccountingRulesService instance"""
    from rotki2.api.v2.services.async_accounting_rules import AsyncAccountingRulesService
    return AsyncAccountingRulesService(accounting_rule_repository, accountant)


def get_async_history_events_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> 'HistoryEventsRepository':
    """Get HistoryEventsRepository instance"""
    from rotki2.api.v2.repositories.history_events import HistoryEventsRepository
    return HistoryEventsRepository(session)


def get_async_history_events_service(
    history_events_repository: Annotated['HistoryEventsRepository', Depends(get_async_history_events_repository)],
    notifier: Annotated['RotkiNotifier', Depends(get_rotki_notifier)],
) -> 'AsyncHistoryEventsService':
    """Get AsyncHistoryEventsService instance"""
    from rotki2.api.v2.services.async_history_events import AsyncHistoryEventsService
    return AsyncHistoryEventsService(history_events_repository, notifier)

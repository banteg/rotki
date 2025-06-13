"""FastAPI dependency injection"""
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from rotkehlchen.api.v2.repositories.accounting_rule import AccountingRuleRepository
from rotkehlchen.api.v2.repositories.blockchain_account import BlockchainAccountRepository
from rotkehlchen.api.v2.repositories.eth2_validator import Eth2ValidatorRepository
from rotkehlchen.api.v2.repositories.evm_transaction import EvmTransactionRepository
from rotkehlchen.api.v2.repositories.nft import NFTRepository
from rotkehlchen.api.v2.services.auth import AuthService
from rotkehlchen.api.v2.services.database import DatabaseService
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.errors.api import AuthenticationError

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


def get_auth_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    session: Annotated[Session, Depends(get_db_session)],
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
    from rotkehlchen.api.v2.services.history import HistoryService
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


def get_eth2_validator_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> Eth2ValidatorRepository:
    """Get Eth2ValidatorRepository instance"""
    return Eth2ValidatorRepository(session)

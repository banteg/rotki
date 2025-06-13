"""Info router for system information endpoints"""
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import get_rotkehlchen, require_logged_in_user
from rotkehlchen.globaldb.utils import GLOBAL_DB_VERSION
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = RotkehlchenLogsAdapter(__name__)

router = APIRouter()


class PingResponse(BaseModel):
    """Response model for ping endpoint"""
    result: bool = True
    message: str = 'pong'


class InfoResponse(BaseModel):
    """Response model for info endpoint"""
    data_directory: str
    log_level: str
    version: dict
    backend_default_arguments: dict
    acceptance_of_terms: bool
    premium_active: bool
    premium_should_sync: bool


@router.get('/ping', response_model=PingResponse)
async def ping() -> PingResponse:
    """Simple health check endpoint"""
    return PingResponse()


@router.get('/info', response_model=InfoResponse)
async def get_info(
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
    logged_in_user: Annotated[str, Depends(require_logged_in_user)],
) -> InfoResponse:
    """Get application information"""
    data_dir = rotkehlchen.data_dir
    log_level = rotkehlchen.args.loglevel

    # Get version info
    version_info = {
        'version': get_current_version(),
        'latest_version': get_current_version(),  # TODO: Check for updates
        'download_url': None,
    }

    # Get backend default arguments
    backend_args = {
        'max_logfiles_num': rotkehlchen.args.max_logfiles_num,
        'max_size_in_mb_all_logs': rotkehlchen.args.max_size_in_mb_all_logs,
        'sqlite_instructions': rotkehlchen.args.sqlite_instructions,
        'data_migration_version': GLOBAL_DB_VERSION,
    }

    # Check premium status
    premium = rotkehlchen.data.db.get_premium()
    premium_active = premium is not None
    premium_should_sync = premium.should_sync() if premium else False

    # Check if user accepted terms
    acceptance_of_terms = rotkehlchen.data.db.get_setting('user_accepted_terms_of_service')

    return InfoResponse(
        data_directory=str(data_dir),
        log_level=log_level,
        version=version_info,
        backend_default_arguments=backend_args,
        acceptance_of_terms=bool(acceptance_of_terms),
        premium_active=premium_active,
        premium_should_sync=premium_should_sync,
    )


@router.post('/ping', response_model=PingResponse)
async def ping_post() -> PingResponse:
    """Simple health check endpoint (POST version)"""
    return PingResponse()


@router.post('/info', response_model=InfoResponse)
async def get_info_post(
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
    logged_in_user: Annotated[str, Depends(require_logged_in_user)],
) -> InfoResponse:
    """Get application information (POST version)"""
    return await get_info(rotkehlchen, logged_in_user)

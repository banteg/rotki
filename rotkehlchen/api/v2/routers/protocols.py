"""Protocols router for DeFi protocol data management"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.protocols import ProtocolsService

router = APIRouter()


class ProtocolsResponse(BaseModel):
    """Response model for protocols operations"""
    result: dict[str, Any]
    message: str = ''


class ProtocolRefreshRequest(BaseModel):
    """Request model for protocol data refresh"""
    protocols: list[str] | None = None
    force_refresh: bool = False


def get_protocols_service() -> ProtocolsService:
    """Get protocols service instance"""
    return ProtocolsService()


@router.get('/data/refresh')
async def get_protocol_refresh_status(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ProtocolsService, Depends(get_protocols_service)],
) -> ProtocolsResponse:
    """Get a list of protocols with refreshable cache - Compatible with v1 GET /api/1/protocols/data/refresh"""
    status = service.get_refresh_status()
    
    return ProtocolsResponse(result=status)


@router.post('/data/refresh')
async def refresh_protocol_data(
    request_data: ProtocolRefreshRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[ProtocolsService, Depends(get_protocols_service)],
) -> ProtocolsResponse:
    """Refresh data for a DeFi protocol cache - Compatible with v1 POST /api/1/protocols/data/refresh"""
    try:
        result = service.refresh_protocol_data(
            protocols=request_data.protocols,
            force_refresh=request_data.force_refresh,
        )
        
        return ProtocolsResponse(
            result=result,
            message='Protocol data refresh initiated',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
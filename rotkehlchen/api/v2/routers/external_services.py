"""External services router for managing API keys and external service configurations"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import require_logged_in_user
from rotkehlchen.api.v2.services.external_services import ExternalServicesService
from rotkehlchen.types import ExternalService

router = APIRouter()


class ExternalServicesResponse(BaseModel):
    """Response model for external services operations"""
    result: dict[str, Any]
    message: str = ''


class ExternalServiceCredentials(BaseModel):
    """Model for external service credentials"""
    name: str
    api_key: str | None = None
    username: str | None = None
    password: str | None = None


class ExternalServicesAddRequest(BaseModel):
    """Request model for adding external service credentials"""
    services: list[ExternalServiceCredentials]


class ExternalServicesDeleteRequest(BaseModel):
    """Request model for deleting external services"""
    services: list[str]


def get_external_services() -> ExternalServicesService:
    """Get external services instance"""
    return ExternalServicesService()


@router.get('/')
async def get_external_services_status(
    _: Annotated[str, Depends(require_logged_in_user)],
    services: Annotated[ExternalServicesService, Depends(get_external_services)],
) -> ExternalServicesResponse:
    """Get status of all external services"""
    status = services.get_all_services_status()

    return ExternalServicesResponse(
        result={
            'services': status,
        },
    )


@router.put('/')
async def add_external_service_credentials(
    credentials_data: ExternalServicesAddRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    services: Annotated[ExternalServicesService, Depends(get_external_services)],
) -> ExternalServicesResponse:
    """Add credentials for external services - Compatible with v1 PUT /api/1/external_services"""
    results = {}

    for service_creds in credentials_data.services:
        try:
            service = ExternalService(service_creds.name)
            services.set_service_credentials(
                service=service,
                api_key=service_creds.api_key,
                username=service_creds.username,
                password=service_creds.password,
            )
            results[service_creds.name] = {'success': True}
        except Exception as e:
            results[service_creds.name] = {'success': False, 'error': str(e)}

    return ExternalServicesResponse(
        result=results,
        message='External service credentials updated',
    )


@router.delete('/')
async def delete_external_service_credentials(
    delete_data: ExternalServicesDeleteRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    services: Annotated[ExternalServicesService, Depends(get_external_services)],
) -> ExternalServicesResponse:
    """Delete credentials for external services - Compatible with v1 DELETE /api/1/external_services"""
    results = {}

    for service_name in delete_data.services:
        try:
            service = ExternalService(service_name)
            services.delete_service_credentials(service)
            results[service_name] = {'success': True}
        except ValueError:
            results[service_name] = {'success': False, 'error': f'Unknown service: {service_name}'}
        except Exception as e:
            results[service_name] = {'success': False, 'error': str(e)}

    return ExternalServicesResponse(
        result=results,
        message='External service credentials deleted',
    )

"""Accounting router for accounting rules and configurations"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import (
    get_database_service,
    require_logged_in_user,
)
from rotkehlchen.api.v2.services.accounting import AccountingService
from rotkehlchen.api.v2.services.database import DatabaseService

router = APIRouter()


class AccountingRuleRequest(BaseModel):
    """Request model for accounting rules"""
    event_type: str
    event_subtype: str
    counterparty: str | None = None
    taxable: bool
    count_entire_amount_spend: bool
    count_cost_basis_pnl: bool
    method: str = 'fifo'
    accounting_treatment: str | None = None


class LinkedRuleRequest(BaseModel):
    """Request model for linked accounting rules"""
    property_name: str
    setting_name: str
    value: Any


class AccountingResponse(BaseModel):
    """Response model for accounting operations"""
    result: dict[str, Any] | list[dict[str, Any]]
    message: str = ''


def get_accounting_service(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> AccountingService:
    """Get accounting service instance"""
    return AccountingService(db_service)


@router.get('/rules')
async def get_accounting_rules(
    event_type: str | None = None,
    event_subtype: str | None = None,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Get accounting rules with optional filtering"""
    rules = service.get_accounting_rules(
        event_type=event_type,
        event_subtype=event_subtype,
    )
    return AccountingResponse(result=rules)


@router.post('/rules')
async def create_accounting_rule(
    request: AccountingRuleRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Create a new accounting rule"""
    try:
        rule_id = service.create_accounting_rule(
            event_type=request.event_type,
            event_subtype=request.event_subtype,
            counterparty=request.counterparty,
            taxable=request.taxable,
            count_entire_amount_spend=request.count_entire_amount_spend,
            count_cost_basis_pnl=request.count_cost_basis_pnl,
            method=request.method,
            accounting_treatment=request.accounting_treatment,
        )
        
        return AccountingResponse(
            result={'rule_id': rule_id},
            message='Accounting rule created successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.put('/rules/{rule_id}')
async def update_accounting_rule(
    rule_id: int,
    request: AccountingRuleRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Update an existing accounting rule"""
    success = service.update_accounting_rule(
        rule_id=rule_id,
        event_type=request.event_type,
        event_subtype=request.event_subtype,
        counterparty=request.counterparty,
        taxable=request.taxable,
        count_entire_amount_spend=request.count_entire_amount_spend,
        count_cost_basis_pnl=request.count_cost_basis_pnl,
        method=request.method,
        accounting_treatment=request.accounting_treatment,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Accounting rule not found',
        )
    
    return AccountingResponse(
        result={'success': True},
        message='Accounting rule updated successfully',
    )


@router.delete('/rules/{rule_id}')
async def delete_accounting_rule(
    rule_id: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Delete an accounting rule"""
    success = service.delete_accounting_rule(rule_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Accounting rule not found',
        )
    
    return AccountingResponse(
        result={'success': True},
        message='Accounting rule deleted successfully',
    )


@router.get('/rules/linked')
async def get_linked_rules(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Get all linked accounting settings"""
    linked_rules = service.get_linked_rules()
    return AccountingResponse(result=linked_rules)


@router.post('/rules/linked')
async def create_linked_rule(
    request: LinkedRuleRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Create a new linked accounting setting"""
    try:
        service.create_linked_rule(
            property_name=request.property_name,
            setting_name=request.setting_name,
            value=request.value,
        )
        
        return AccountingResponse(
            result={'success': True},
            message='Linked rule created successfully',
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete('/rules/linked')
async def delete_linked_rule(
    property_name: str,
    setting_name: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Delete a linked accounting setting"""
    success = service.delete_linked_rule(property_name, setting_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Linked rule not found',
        )
    
    return AccountingResponse(
        result={'success': True},
        message='Linked rule deleted successfully',
    )
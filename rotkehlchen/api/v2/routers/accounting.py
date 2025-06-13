"""Accounting router for accounting rules and configurations"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
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
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
    event_type: str | None = None,
    event_subtype: str | None = None,
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


# v1 compatibility endpoints
@router.post('/rules')
async def query_accounting_rules_v1(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
    event_types: list[str] | None = None,
    event_subtypes: list[str] | None = None,
    counterparties: list[str] | None = None,
) -> AccountingResponse:
    """Query accounting rules - Compatible with v1 POST /api/1/accounting/rules"""
    rules = service.query_accounting_rules(
        event_types=event_types,
        event_subtypes=event_subtypes,
        counterparties=counterparties,
    )

    return AccountingResponse(result={'entries': rules, 'entries_total': len(rules)})


@router.put('/rules')
async def add_accounting_rule_v1(
    rule_data: AccountingRuleRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Add an accounting rule - Compatible with v1 PUT /api/1/accounting/rules"""
    rule_id = service.add_accounting_rule(
        event_type=rule_data.event_type,
        event_subtype=rule_data.event_subtype,
        counterparty=rule_data.counterparty,
        taxable=rule_data.taxable,
        count_entire_amount_spend=rule_data.count_entire_amount_spend,
        count_cost_basis_pnl=rule_data.count_cost_basis_pnl,
        accounting_treatment=rule_data.accounting_treatment,
    )

    return AccountingResponse(
        result={'identifier': rule_id},
        message='Accounting rule added successfully',
    )


@router.patch('/rules')
async def edit_accounting_rule_v1(
    identifier: int,
    rule_data: AccountingRuleRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Edit an accounting rule - Compatible with v1 PATCH /api/1/accounting/rules"""
    success = service.edit_accounting_rule(
        identifier=identifier,
        event_type=rule_data.event_type,
        event_subtype=rule_data.event_subtype,
        counterparty=rule_data.counterparty,
        taxable=rule_data.taxable,
        count_entire_amount_spend=rule_data.count_entire_amount_spend,
        count_cost_basis_pnl=rule_data.count_cost_basis_pnl,
        accounting_treatment=rule_data.accounting_treatment,
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


@router.delete('/rules')
async def delete_accounting_rule_v1(
    identifier: int,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Delete an accounting rule - Compatible with v1 DELETE /api/1/accounting/rules"""
    success = service.delete_accounting_rule(identifier)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Accounting rule not found',
        )

    return AccountingResponse(
        result={'success': True},
        message='Accounting rule deleted successfully',
    )


@router.get('/rules/info')
async def get_accounting_rule_info(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Get info on linkable accounting rule properties - Compatible with v1 GET /api/1/accounting/rules/info"""
    info = service.get_accounting_rule_info()

    return AccountingResponse(result=info)


@router.post('/rules/import')
async def import_accounting_rules_upload(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
    file: UploadFile = File(...),
) -> AccountingResponse:
    """Import accounting rules via file upload - Compatible with v1 POST /api/1/accounting/rules/import"""
    # Save uploaded file temporarily
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = service.import_accounting_rules(tmp_path)
        return AccountingResponse(
            result=result,
            message='Accounting rules imported successfully',
        )
    finally:
        os.unlink(tmp_path)


@router.put('/rules/import')
async def import_accounting_rules_path(
    filepath: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Import accounting rules via file path - Compatible with v1 PUT /api/1/accounting/rules/import"""
    result = service.import_accounting_rules(filepath)

    return AccountingResponse(
        result=result,
        message='Accounting rules imported successfully',
    )


@router.post('/rules/export')
async def export_accounting_rules(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
    directory_path: str | None = None,
) -> AccountingResponse:
    """Export accounting rules - Compatible with v1 POST /api/1/accounting/rules/export"""
    file_path = service.export_accounting_rules(directory_path)

    return AccountingResponse(
        result={'file': file_path},
        message='Accounting rules exported successfully',
    )


@router.post('/rules/conflicts')
async def list_accounting_rule_conflicts(
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """List accounting rule conflicts - Compatible with v1 POST /api/1/accounting/rules/conflicts"""
    conflicts = service.get_accounting_rule_conflicts()

    return AccountingResponse(result={'conflicts': conflicts})


class AccountingRuleConflictRequest(BaseModel):
    """Request model for resolving accounting rule conflicts"""
    conflicts: list[dict[str, Any]]
    resolution: str = 'keep_both'  # keep_both, keep_local, keep_remote


@router.patch('/rules/conflicts')
async def resolve_accounting_rule_conflicts(
    conflict_data: AccountingRuleConflictRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountingResponse:
    """Solve accounting rule conflicts - Compatible with v1 PATCH /api/1/accounting/rules/conflicts"""
    resolved = service.resolve_accounting_rule_conflicts(
        conflicts=conflict_data.conflicts,
        resolution=conflict_data.resolution,
    )

    return AccountingResponse(
        result={'resolved': resolved},
        message=f'Resolved {resolved} conflicts',
    )

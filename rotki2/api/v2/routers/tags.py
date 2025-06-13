"""Tags router for managing tags"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from rotki2.api.v2.dependencies import get_tag_repository, require_logged_in_user

if TYPE_CHECKING:
    from rotki2.api.v2.repositories.tag import TagRepository

router = APIRouter()


class TagModel(BaseModel):
    """Tag data model"""
    name: str
    description: str | None = None
    background_color: str = 'ffffff'
    foreground_color: str = '000000'


class TagsResponse(BaseModel):
    """Response model for tags operations"""
    result: list[dict[str, Any]] | dict[str, Any]
    message: str = ''


class TagCreateRequest(BaseModel):
    """Request model for creating a tag"""
    name: str
    description: str | None = None
    background_color: str = 'ffffff'
    foreground_color: str = '000000'


class TagUpdateRequest(BaseModel):
    """Request model for updating a tag"""
    description: str | None = None
    background_color: str | None = None
    foreground_color: str | None = None


@router.get('/', response_model=TagsResponse)
async def get_tags(
    _: Annotated[str, Depends(require_logged_in_user)],
    tag_repo: Annotated['TagRepository', Depends(get_tag_repository)],
) -> TagsResponse:
    """Get all tags"""
    tags = tag_repo.get_all()

    result = [
        {
            'name': tag.name,
            'description': tag.description,
            'background_color': tag.background_color,
            'foreground_color': tag.foreground_color,
        }
        for tag in tags
    ]

    return TagsResponse(result=result)


@router.post('/', response_model=TagsResponse)
async def create_tag(
    tag_data: TagCreateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    tag_repo: Annotated['TagRepository', Depends(get_tag_repository)],
) -> TagsResponse:
    """Create a new tag"""
    # Check if tag already exists
    existing = tag_repo.get_tag_by_name(tag_data.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f'Tag "{tag_data.name}" already exists',
        )

    try:
        tag = tag_repo.create_tag(
            name=tag_data.name,
            description=tag_data.description,
            background_color=tag_data.background_color,
            foreground_color=tag_data.foreground_color,
        )

        result = {
            'name': tag.name,
            'description': tag.description,
            'background_color': tag.background_color,
            'foreground_color': tag.foreground_color,
        }

        return TagsResponse(
            result=result,
            message=f'Tag "{tag.name}" created successfully',
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to create tag: {e!s}',
        )


@router.put('/{tag_name}', response_model=TagsResponse)
async def update_tag(
    tag_name: str,
    tag_update: TagUpdateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    tag_repo: Annotated['TagRepository', Depends(get_tag_repository)],
) -> TagsResponse:
    """Update an existing tag"""
    tag = tag_repo.update_tag(
        name=tag_name,
        description=tag_update.description,
        background_color=tag_update.background_color,
        foreground_color=tag_update.foreground_color,
    )

    if not tag:
        raise HTTPException(
            status_code=404,
            detail=f'Tag "{tag_name}" not found',
        )

    result = {
        'name': tag.name,
        'description': tag.description,
        'background_color': tag.background_color,
        'foreground_color': tag.foreground_color,
    }

    return TagsResponse(
        result=result,
        message=f'Tag "{tag.name}" updated successfully',
    )


@router.delete('/{tag_name}', response_model=TagsResponse)
async def delete_tag(
    tag_name: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    tag_repo: Annotated['TagRepository', Depends(get_tag_repository)],
) -> TagsResponse:
    """Delete a tag"""
    success = tag_repo.delete_tag(tag_name)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f'Tag "{tag_name}" not found',
        )

    return TagsResponse(
        result={},
        message=f'Tag "{tag_name}" deleted successfully',
    )

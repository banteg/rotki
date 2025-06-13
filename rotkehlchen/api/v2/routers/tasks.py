"""Tasks router for managing background tasks"""
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from rotkehlchen.api.v2.dependencies import (
    get_rotkehlchen,
    get_task_manager,
    require_logged_in_user,
)
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.tasks.manager import TaskManager

router = APIRouter()


class TaskModel(BaseModel):
    """Task data model"""
    task_id: str
    task_type: str
    status: str
    progress: float
    started_at: Timestamp
    completed_at: Timestamp | None = None
    result: Any | None = None
    error: str | None = None


class TasksResponse(BaseModel):
    """Response model for tasks operations"""
    result: list[dict[str, Any]] | dict[str, Any]
    message: str = ''


class TaskCreateRequest(BaseModel):
    """Request model for creating a task"""
    task_type: str
    params: dict[str, Any] = {}


@router.get('/', response_model=TasksResponse)
async def get_tasks(
    _: Annotated[str, Depends(require_logged_in_user)],
    task_manager: Annotated['TaskManager', Depends(get_task_manager)],
) -> TasksResponse:
    """Get all tasks"""
    tasks = []
    
    # Get running tasks
    running = task_manager.get_running_tasks()
    for task_id, task_info in running.items():
        tasks.append({
            'task_id': task_id,
            'task_type': task_info.get('type', 'unknown'),
            'status': 'running',
            'progress': task_info.get('progress', 0.0),
            'started_at': task_info.get('started_at', 0),
            'completed_at': None,
            'result': None,
            'error': None,
        })
    
    # Get completed tasks
    completed = task_manager.get_completed_tasks()
    for task_id, task_info in completed.items():
        tasks.append({
            'task_id': task_id,
            'task_type': task_info.get('type', 'unknown'),
            'status': 'completed',
            'progress': 1.0,
            'started_at': task_info.get('started_at', 0),
            'completed_at': task_info.get('completed_at', 0),
            'result': task_info.get('result'),
            'error': task_info.get('error'),
        })
    
    return TasksResponse(result=tasks)


@router.post('/', response_model=TasksResponse)
async def create_task(
    task_data: TaskCreateRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    rotkehlchen: Annotated['Rotkehlchen', Depends(get_rotkehlchen)],
    task_manager: Annotated['TaskManager', Depends(get_task_manager)],
) -> TasksResponse:
    """Create a new background task"""
    # Map task types to actual functions
    task_mapping = {
        'query_balances': lambda: rotkehlchen.query_balances(save_data=True),
        'query_history': lambda: rotkehlchen.history_querying_manager.query_history(
            start_ts=task_data.params.get('start_ts', 0),
            end_ts=task_data.params.get('end_ts', Timestamp(int(time.time()))),
        ),
        'export_history': lambda: rotkehlchen.history_exporter.export(
            directory=task_data.params.get('directory', '/tmp'),
        ),
    }
    
    if task_data.task_type not in task_mapping:
        raise HTTPException(
            status_code=400,
            detail=f'Unknown task type: {task_data.task_type}',
        )
    
    # Create the task
    task_id = task_manager.create_task(
        task_type=task_data.task_type,
        task_fn=task_mapping[task_data.task_type],
    )
    
    return TasksResponse(
        result={
            'task_id': task_id,
            'task_type': task_data.task_type,
            'status': 'created',
        },
        message=f'Task {task_id} created successfully',
    )


@router.get('/{task_id}', response_model=TasksResponse)
async def get_task(
    task_id: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    task_manager: Annotated['TaskManager', Depends(get_task_manager)],
) -> TasksResponse:
    """Get a specific task"""
    # Check running tasks
    running = task_manager.get_running_tasks()
    if task_id in running:
        task_info = running[task_id]
        return TasksResponse(result={
            'task_id': task_id,
            'task_type': task_info.get('type', 'unknown'),
            'status': 'running',
            'progress': task_info.get('progress', 0.0),
            'started_at': task_info.get('started_at', 0),
            'completed_at': None,
            'result': None,
            'error': None,
        })
    
    # Check completed tasks
    completed = task_manager.get_completed_tasks()
    if task_id in completed:
        task_info = completed[task_id]
        return TasksResponse(result={
            'task_id': task_id,
            'task_type': task_info.get('type', 'unknown'),
            'status': 'completed',
            'progress': 1.0,
            'started_at': task_info.get('started_at', 0),
            'completed_at': task_info.get('completed_at', 0),
            'result': task_info.get('result'),
            'error': task_info.get('error'),
        })
    
    raise HTTPException(
        status_code=404,
        detail=f'Task {task_id} not found',
    )


@router.delete('/{task_id}', response_model=TasksResponse)
async def cancel_task(
    task_id: str,
    _: Annotated[str, Depends(require_logged_in_user)],
    task_manager: Annotated['TaskManager', Depends(get_task_manager)],
) -> TasksResponse:
    """Cancel a running task"""
    success = task_manager.cancel_task(task_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f'Task {task_id} not found or already completed',
        )
    
    return TasksResponse(
        result={},
        message=f'Task {task_id} cancelled successfully',
    )


import time
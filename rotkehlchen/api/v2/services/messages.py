"""Messages service for managing user messages"""
import time
import uuid
from typing import TYPE_CHECKING, Any

from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen


class MessagesService:
    """Service for managing user messages"""

    def __init__(self, rotkehlchen: 'Rotkehlchen | None' = None) -> None:
        self.rotkehlchen = rotkehlchen
        self._messages: list[dict[str, Any]] = []
        self._message_counter = 0

    def get_all_messages(self, unread_only: bool = False) -> list[dict[str, Any]]:
        """Get all messages for the user"""
        messages = []

        # Add version check message if needed
        version_message = self._check_version_update()
        if version_message:
            messages.append(version_message)

        # Add task-related messages
        if self.rotkehlchen and hasattr(self.rotkehlchen, 'task_manager'):
            task_messages = self._get_task_messages()
            messages.extend(task_messages)

        # Add stored messages
        if unread_only:
            messages.extend([msg for msg in self._messages if not msg.get('read', False)])
        else:
            messages.extend(self._messages)

        # Sort by timestamp, newest first
        messages.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        return messages

    def mark_message_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        for msg in self._messages:
            if msg['id'] == message_id:
                msg['read'] = True
                return True
        return False

    def add_message(
        self,
        message: str,
        level: str = 'info',
        category: str = 'general',
    ) -> str:
        """Add a new message"""
        message_id = str(uuid.uuid4())

        self._messages.append({
            'id': message_id,
            'message': message,
            'level': level,
            'category': category,
            'timestamp': int(time.time()),
            'read': False,
        })

        # Keep only last 100 messages
        if len(self._messages) > 100:
            self._messages = self._messages[-100:]

        return message_id

    def _check_version_update(self) -> dict[str, Any] | None:
        """Check if there's a version update available"""
        try:
            version_info = get_current_version()

            # Would check against latest version
            # For now, return None (no update)
            return None
        except Exception:
            return None

    def _get_task_messages(self) -> list[dict[str, Any]]:
        """Get messages related to running tasks"""
        messages = []

        if not self.rotkehlchen or not hasattr(self.rotkehlchen, 'task_manager'):
            return messages

        try:
            running_tasks = self.rotkehlchen.task_manager.get_running_tasks()

            for task_id, task_info in running_tasks.items():
                messages.append({
                    'id': f'task_{task_id}',
                    'message': f'Task in progress: {task_info.get("description", "Unknown task")}',
                    'level': 'info',
                    'category': 'task',
                    'timestamp': int(time.time()),
                    'read': False,
                    'task_id': task_id,
                })
        except Exception:
            pass

        return messages

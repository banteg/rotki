"""Actions service for managing ignored actions"""
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class ActionsService:
    """Service for managing actions and ignored actions"""
    
    def __init__(self) -> None:
        # In-memory storage for ignored actions
        self._ignored_actions: dict[str, set[str]] = {
            'trades': set(),
            'transactions': set(),
            'ledger_actions': set(),
            'history_events': set(),
        }
    
    def get_ignored_actions(self) -> dict[str, list[str]]:
        """Get all ignored actions grouped by type"""
        result = {}
        
        for action_type, action_ids in self._ignored_actions.items():
            if action_ids:
                result[action_type] = list(action_ids)
        
        return result
    
    def add_ignored_actions(self, action_type: str, action_ids: list[str]) -> int:
        """Add actions to ignore list"""
        if action_type not in self._ignored_actions:
            raise ValueError(f'Invalid action type: {action_type}. Valid types are: {", ".join(self._ignored_actions.keys())}')
        
        before_count = len(self._ignored_actions[action_type])
        self._ignored_actions[action_type].update(action_ids)
        after_count = len(self._ignored_actions[action_type])
        
        return after_count - before_count
    
    def remove_ignored_actions(self, action_type: str, action_ids: list[str]) -> int:
        """Remove actions from ignore list"""
        if action_type not in self._ignored_actions:
            raise ValueError(f'Invalid action type: {action_type}')
        
        before_count = len(self._ignored_actions[action_type])
        self._ignored_actions[action_type].difference_update(action_ids)
        after_count = len(self._ignored_actions[action_type])
        
        return before_count - after_count
    
    def is_action_ignored(self, action_type: str, action_id: str) -> bool:
        """Check if a specific action is ignored"""
        return (
            action_type in self._ignored_actions and 
            action_id in self._ignored_actions[action_type]
        )
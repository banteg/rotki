"""Bridge between the old RotkiNotifier and the new WebSocket system

This module provides compatibility between the v1 messaging system and the v2 WebSocket implementation.
"""
from typing import TYPE_CHECKING, Any

from rotki2.api.v2.websocket import (
    broadcast_notification,
    broadcast_task_status,
    broadcast_balance_update,
    broadcast_transaction_event,
    broadcast_history_event,
    broadcast_price_update,
)

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.typedefs import WSMessageType


class WebSocketBridge:
    """Provides compatibility layer for v1 message types to v2 WebSocket system"""
    
    @staticmethod
    async def send_legacy_message(
        message_type: 'WSMessageType',
        data: dict[str, Any] | list[Any],
        user_id: str | None = None,
    ) -> None:
        """Convert and send legacy message types through the new WebSocket system
        
        Args:
            message_type: The v1 WebSocket message type
            data: The message data
            user_id: Optional user ID for targeted messages
        """
        # Map legacy message types to new broadcasting functions
        message_type_str = str(message_type)
        
        # Handle different legacy message types
        if message_type_str == 'legacy':
            # Legacy warning/error messages
            verbosity = data.get('verbosity', 'info') if isinstance(data, dict) else 'info'
            value = data.get('value', str(data)) if isinstance(data, dict) else str(data)
            severity = 'error' if verbosity == 'error' else 'warning' if verbosity == 'warning' else 'info'
            await broadcast_notification(
                title=f'System {verbosity.title()}',
                message=value,
                severity=severity,
                user_id=user_id,
            )
            
        elif message_type_str == 'balance_snapshot_error':
            # Balance snapshot errors
            await broadcast_notification(
                title='Balance Snapshot Error',
                message=str(data),
                severity='error',
                user_id=user_id,
            )
            
        elif message_type_str == 'evm_transaction_status':
            # Transaction status updates
            await broadcast_transaction_event(
                event_type='status_update',
                transaction_data=data if isinstance(data, dict) else {'data': data},
                user_id=user_id,
            )
            
        elif message_type_str == 'premium_status_update':
            # Premium status updates
            await broadcast_notification(
                title='Premium Status Update',
                message='Premium status has been updated',
                severity='info',
                user_id=user_id,
            )
            
        elif message_type_str == 'db_upgrade_status':
            # Database upgrade status
            await broadcast_task_status(
                task_id='db_upgrade',
                status='running',
                progress=data.get('progress') if isinstance(data, dict) else None,
                user_id=user_id,
            )
            
        elif message_type_str == 'new_evm_token_detected':
            # New token detection
            await broadcast_notification(
                title='New Token Detected',
                message=f'New EVM token detected: {data}',
                severity='info',
                user_id=user_id,
            )
            
        elif message_type_str == 'history_events_status':
            # History events status
            await broadcast_history_event(
                event_type='status_update',
                history_data=data if isinstance(data, dict) else {'data': data},
                user_id=user_id,
            )
            
        elif message_type_str == 'refresh_balances':
            # Balance refresh trigger
            await broadcast_balance_update(
                data={'action': 'refresh_requested'},
                user_id=user_id,
            )
            
        elif message_type_str == 'calendar_reminder':
            # Calendar reminder
            await broadcast_notification(
                title='Calendar Reminder',
                message=str(data),
                severity='info',
                user_id=user_id,
            )
            
        elif message_type_str == 'progress_updates':
            # Generic progress updates
            progress_data = data if isinstance(data, dict) else {'progress': data}
            await broadcast_task_status(
                task_id=progress_data.get('task_id', 'unknown'),
                status='running',
                progress=progress_data.get('progress'),
                user_id=user_id,
            )
            
        else:
            # Fallback for unknown message types
            await broadcast_notification(
                title=f'System Message ({message_type_str})',
                message=str(data),
                severity='info',
                user_id=user_id,
            )


# Utility function to create a notifier-compatible interface
async def broadcast_legacy_compatible(
    message_type: 'WSMessageType',
    data: dict[str, Any] | list[Any],
    user_id: str | None = None,
) -> None:
    """Compatibility function that matches the old notifier broadcast signature
    
    This allows the v1 code to use the new WebSocket system without modification.
    """
    await WebSocketBridge.send_legacy_message(message_type, data, user_id)
"""WebSocket support for v2 API

This module replaces the gevent-based WebSocket system with a FastAPI-native one.
It handles topic subscriptions, targeted messages, and broadcasts.
"""
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class WebSocketTopic(str, Enum):
    """Available WebSocket topics for subscription"""
    BALANCES = "balances"
    PRICES = "prices"
    TRANSACTIONS = "transactions"
    TASKS = "tasks"
    NOTIFICATIONS = "notifications"
    HISTORY = "history"
    DEFI = "defi"
    NFT = "nft"
    STATISTICS = "statistics"
    ALL = "all"  # Subscribe to all topics


@dataclass
class WebSocketClient:
    """Represents a connected WebSocket client"""
    websocket: WebSocket
    client_id: str
    subscribed_topics: set[WebSocketTopic]
    user_id: str | None = None  # Optional user association


class ConnectionManager:
    """Manages WebSocket connections with topic-based subscriptions"""

    def __init__(self):
        self.active_connections: dict[str, WebSocketClient] = {}
        self.topic_subscribers: dict[WebSocketTopic, set[str]] = defaultdict(set)
        self.user_connections: dict[str, set[str]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, user_id: str | None = None) -> str:
        """Accept new WebSocket connection and return client ID"""
        await websocket.accept()
        
        # Generate unique client ID
        client_id = str(uuid.uuid4())
        
        # Create client object
        client = WebSocketClient(
            websocket=websocket,
            client_id=client_id,
            subscribed_topics=set(),
            user_id=user_id,
        )
        
        # Store client
        self.active_connections[client_id] = client
        
        # Track user connection if user_id provided
        if user_id:
            self.user_connections[user_id].add(client_id)
        
        return client_id

    def disconnect(self, client_id: str):
        """Remove disconnected WebSocket"""
        if client_id not in self.active_connections:
            return
            
        client = self.active_connections[client_id]
        
        # Remove from topic subscribers
        for topic in client.subscribed_topics:
            self.topic_subscribers[topic].discard(client_id)
        
        # Remove from user connections
        if client.user_id:
            self.user_connections[client.user_id].discard(client_id)
            if not self.user_connections[client.user_id]:
                del self.user_connections[client.user_id]
        
        # Remove client
        del self.active_connections[client_id]

    async def subscribe_to_topic(self, client_id: str, topic: WebSocketTopic) -> bool:
        """Subscribe a client to a specific topic"""
        if client_id not in self.active_connections:
            return False
            
        client = self.active_connections[client_id]
        client.subscribed_topics.add(topic)
        self.topic_subscribers[topic].add(client_id)
        
        # If subscribing to ALL, add to all topics
        if topic == WebSocketTopic.ALL:
            for t in WebSocketTopic:
                if t != WebSocketTopic.ALL:
                    client.subscribed_topics.add(t)
                    self.topic_subscribers[t].add(client_id)
        
        return True

    async def unsubscribe_from_topic(self, client_id: str, topic: WebSocketTopic) -> bool:
        """Unsubscribe a client from a specific topic"""
        if client_id not in self.active_connections:
            return False
            
        client = self.active_connections[client_id]
        client.subscribed_topics.discard(topic)
        self.topic_subscribers[topic].discard(client_id)
        
        # If unsubscribing from ALL, remove from all topics
        if topic == WebSocketTopic.ALL:
            for t in WebSocketTopic:
                client.subscribed_topics.discard(t)
                self.topic_subscribers[t].discard(client_id)
        
        return True

    async def send_personal_message(self, client_id: str, message: dict[str, Any]):
        """Send message to specific client"""
        if client_id not in self.active_connections:
            return
            
        client = self.active_connections[client_id]
        if client.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await client.websocket.send_json(message)
            except Exception:
                # Connection might have been closed
                self.disconnect(client_id)

    async def send_to_user(self, user_id: str, message: dict[str, Any]):
        """Send message to all connections of a specific user"""
        if user_id not in self.user_connections:
            return
            
        # Send to all user's connections
        for client_id in list(self.user_connections[user_id]):
            await self.send_personal_message(client_id, message)

    async def broadcast_to_topic(self, topic: WebSocketTopic, message: dict[str, Any]):
        """Broadcast message to all subscribers of a topic"""
        if topic not in self.topic_subscribers:
            return
            
        # Send to all topic subscribers
        for client_id in list(self.topic_subscribers[topic]):
            await self.send_personal_message(client_id, message)

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast message to all connections"""
        for client_id in list(self.active_connections.keys()):
            await self.send_personal_message(client_id, message)


# Global connection manager instance
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, user_id: str | None = None):
    """Main WebSocket endpoint handler
    
    Args:
        websocket: The WebSocket connection
        user_id: Optional user ID to associate with the connection
    """
    client_id = await manager.connect(websocket, user_id)

    try:
        # Send welcome message with client ID
        await websocket.send_json({
            'type': 'connection',
            'message': 'Connected to Rotki WebSocket',
            'client_id': client_id,
            'available_topics': [topic.value for topic in WebSocketTopic],
        })

        while True:
            # Receive and handle messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get('type')

                # Handle different message types
                if msg_type == 'ping':
                    await manager.send_personal_message(client_id, {'type': 'pong'})
                    
                elif msg_type == 'subscribe':
                    # Handle subscription to specific topic
                    topic_str = message.get('topic')
                    try:
                        topic = WebSocketTopic(topic_str)
                        success = await manager.subscribe_to_topic(client_id, topic)
                        await manager.send_personal_message(client_id, {
                            'type': 'subscribed',
                            'topic': topic.value,
                            'success': success,
                        })
                    except ValueError:
                        await manager.send_personal_message(client_id, {
                            'type': 'error',
                            'message': f'Invalid topic: {topic_str}',
                        })
                        
                elif msg_type == 'unsubscribe':
                    # Handle unsubscription from topic
                    topic_str = message.get('topic')
                    try:
                        topic = WebSocketTopic(topic_str)
                        success = await manager.unsubscribe_from_topic(client_id, topic)
                        await manager.send_personal_message(client_id, {
                            'type': 'unsubscribed',
                            'topic': topic.value,
                            'success': success,
                        })
                    except ValueError:
                        await manager.send_personal_message(client_id, {
                            'type': 'error',
                            'message': f'Invalid topic: {topic_str}',
                        })
                        
                elif msg_type == 'get_subscriptions':
                    # Return current subscriptions
                    client = manager.active_connections.get(client_id)
                    if client:
                        await manager.send_personal_message(client_id, {
                            'type': 'subscriptions',
                            'topics': [topic.value for topic in client.subscribed_topics],
                        })
                        
                else:
                    # Unknown message type
                    await manager.send_personal_message(client_id, {
                        'type': 'error',
                        'message': f'Unknown message type: {msg_type}',
                        'supported_types': ['ping', 'subscribe', 'unsubscribe', 'get_subscriptions'],
                    })

            except json.JSONDecodeError:
                await manager.send_personal_message(client_id, {
                    'type': 'error',
                    'message': 'Invalid JSON',
                })
            except Exception as e:
                await manager.send_personal_message(client_id, {
                    'type': 'error',
                    'message': f'Error processing message: {str(e)}',
                })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        manager.disconnect(client_id)
        print(f'WebSocket error for client {client_id}: {e}')


# Event broadcasting functions that can be called from services
async def broadcast_balance_update(data: dict[str, Any], user_id: str | None = None):
    """Broadcast balance update to subscribers
    
    Args:
        data: Balance update data
        user_id: If provided, only send to this user's connections
    """
    message = {
        'type': 'balance_update',
        'data': data,
        'timestamp': json.dumps(None),  # Would use actual timestamp
    }
    
    if user_id:
        await manager.send_to_user(user_id, message)
    else:
        await manager.broadcast_to_topic(WebSocketTopic.BALANCES, message)


async def broadcast_task_status(
    task_id: str,
    status: str,
    progress: float | None = None,
    user_id: str | None = None,
    result: Any = None,
    error: str | None = None,
):
    """Broadcast task status update
    
    Args:
        task_id: The task identifier
        status: Task status (pending, running, completed, failed)
        progress: Optional progress percentage (0-100)
        user_id: If provided, only send to this user
        result: Task result data (for completed tasks)
        error: Error message (for failed tasks)
    """
    message = {
        'type': 'task_status',
        'task_id': task_id,
        'status': status,
        'progress': progress,
        'result': result,
        'error': error,
    }
    
    if user_id:
        await manager.send_to_user(user_id, message)
    else:
        await manager.broadcast_to_topic(WebSocketTopic.TASKS, message)


async def broadcast_price_update(asset: str, price: str, usd_price: str):
    """Broadcast price update for an asset"""
    await manager.broadcast_to_topic(WebSocketTopic.PRICES, {
        'type': 'price_update',
        'asset': asset,
        'price': price,
        'usd_price': usd_price,
    })


async def broadcast_notification(
    title: str,
    message: str,
    severity: str = 'info',
    user_id: str | None = None,
):
    """Broadcast notification
    
    Args:
        title: Notification title
        message: Notification message
        severity: Severity level (info, warning, error, success)
        user_id: If provided, only send to this user
    """
    notification = {
        'type': 'notification',
        'title': title,
        'message': message,
        'severity': severity,
    }
    
    if user_id:
        await manager.send_to_user(user_id, notification)
    else:
        await manager.broadcast_to_topic(WebSocketTopic.NOTIFICATIONS, notification)


async def broadcast_transaction_event(
    event_type: str,
    transaction_data: dict[str, Any],
    user_id: str | None = None,
):
    """Broadcast transaction event (new transaction, confirmation update, etc.)"""
    message = {
        'type': 'transaction_event',
        'event_type': event_type,
        'data': transaction_data,
    }
    
    if user_id:
        await manager.send_to_user(user_id, message)
    else:
        await manager.broadcast_to_topic(WebSocketTopic.TRANSACTIONS, message)


async def broadcast_history_event(
    event_type: str,
    history_data: dict[str, Any],
    user_id: str | None = None,
):
    """Broadcast history event (new history entry, update, etc.)"""
    message = {
        'type': 'history_event',
        'event_type': event_type,
        'data': history_data,
    }
    
    if user_id:
        await manager.send_to_user(user_id, message)
    else:
        await manager.broadcast_to_topic(WebSocketTopic.HISTORY, message)


async def broadcast_defi_event(
    protocol: str,
    event_type: str,
    data: dict[str, Any],
    user_id: str | None = None,
):
    """Broadcast DeFi protocol event"""
    message = {
        'type': 'defi_event',
        'protocol': protocol,
        'event_type': event_type,
        'data': data,
    }
    
    if user_id:
        await manager.send_to_user(user_id, message)
    else:
        await manager.broadcast_to_topic(WebSocketTopic.DEFI, message)


async def broadcast_nft_event(
    event_type: str,
    nft_data: dict[str, Any],
    user_id: str | None = None,
):
    """Broadcast NFT event (new NFT, price update, etc.)"""
    message = {
        'type': 'nft_event',
        'event_type': event_type,
        'data': nft_data,
    }
    
    if user_id:
        await manager.send_to_user(user_id, message)
    else:
        await manager.broadcast_to_topic(WebSocketTopic.NFT, message)


async def broadcast_statistics_update(
    stat_type: str,
    data: dict[str, Any],
    user_id: str | None = None,
):
    """Broadcast statistics update"""
    message = {
        'type': 'statistics_update',
        'stat_type': stat_type,
        'data': data,
    }
    
    if user_id:
        await manager.send_to_user(user_id, message)
    else:
        await manager.broadcast_to_topic(WebSocketTopic.STATISTICS, message)


# Utility function to get connection statistics
def get_connection_stats() -> dict[str, Any]:
    """Get current WebSocket connection statistics"""
    total_connections = len(manager.active_connections)
    users_connected = len(manager.user_connections)
    
    topic_stats = {}
    for topic, subscribers in manager.topic_subscribers.items():
        topic_stats[topic.value] = len(subscribers)
    
    return {
        'total_connections': total_connections,
        'unique_users': users_connected,
        'topic_subscribers': topic_stats,
    }

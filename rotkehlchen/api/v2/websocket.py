"""WebSocket support for v2 API"""
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific connection"""
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connections"""
        # Remove disconnected websockets
        self.active_connections = [
            ws for ws in self.active_connections 
            if ws.client_state == WebSocketState.CONNECTED
        ]
        
        # Send to all active connections
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Connection might have been closed
                pass
    
    async def broadcast_json(self, data: dict[str, Any]):
        """Broadcast JSON data to all connections"""
        message = json.dumps(data)
        await self.broadcast(message)


# Global connection manager instance
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint handler"""
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            'type': 'connection',
            'message': 'Connected to Rotki WebSocket',
        })
        
        while True:
            # Receive and echo messages (or handle commands)
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types
                if message.get('type') == 'ping':
                    await websocket.send_json({'type': 'pong'})
                elif message.get('type') == 'subscribe':
                    # Handle subscription to specific events
                    topic = message.get('topic')
                    await websocket.send_json({
                        'type': 'subscribed',
                        'topic': topic,
                    })
                else:
                    # Echo back unknown messages
                    await websocket.send_json({
                        'type': 'echo',
                        'data': message,
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    'type': 'error',
                    'message': 'Invalid JSON',
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # Could broadcast user left message here
    except Exception as e:
        manager.disconnect(websocket)
        print(f"WebSocket error: {e}")


# Event broadcasting functions that can be called from services
async def broadcast_balance_update(data: dict[str, Any]):
    """Broadcast balance update to all connected clients"""
    await manager.broadcast_json({
        'type': 'balance_update',
        'data': data,
    })


async def broadcast_task_status(task_id: str, status: str, progress: float | None = None):
    """Broadcast task status update"""
    await manager.broadcast_json({
        'type': 'task_status',
        'task_id': task_id,
        'status': status,
        'progress': progress,
    })


async def broadcast_price_update(asset: str, price: str, usd_price: str):
    """Broadcast price update for an asset"""
    await manager.broadcast_json({
        'type': 'price_update',
        'asset': asset,
        'price': price,
        'usd_price': usd_price,
    })


async def broadcast_notification(
    title: str,
    message: str,
    severity: str = 'info',
):
    """Broadcast notification to all clients"""
    await manager.broadcast_json({
        'type': 'notification',
        'title': title,
        'message': message,
        'severity': severity,
    })
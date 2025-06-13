"""WebSocket router for real-time communications"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket

from rotki2.api.v2.dependencies import get_optional_logged_in_user
from rotki2.api.v2.websocket import get_connection_stats, websocket_endpoint

router = APIRouter()


@router.websocket("/ws")
async def websocket_route(
    websocket: WebSocket,
    user_id: Annotated[str | None, Depends(get_optional_logged_in_user)] = None,
    token: str | None = Query(None, description="Authentication token"),
):
    """WebSocket endpoint for real-time updates
    
    Clients can connect and subscribe to various topics:
    - balances: Balance updates
    - prices: Asset price updates
    - transactions: Transaction events
    - tasks: Background task status
    - notifications: System notifications
    - history: History events
    - defi: DeFi protocol events
    - nft: NFT events
    - statistics: Statistics updates
    - all: Subscribe to all topics
    
    Message format:
    - Subscribe: {"type": "subscribe", "topic": "balances"}
    - Unsubscribe: {"type": "unsubscribe", "topic": "balances"}
    - Get subscriptions: {"type": "get_subscriptions"}
    - Ping: {"type": "ping"}
    """
    # If token is provided in query, use it to get user_id
    # This is a fallback for clients that can't use cookies
    if token and not user_id:
        # TODO: Validate token and get user_id
        pass
    
    await websocket_endpoint(websocket, user_id)


@router.get("/ws/stats")
async def get_websocket_stats(
    _: Annotated[str | None, Depends(get_optional_logged_in_user)] = None,
):
    """Get WebSocket connection statistics
    
    Returns information about active connections and topic subscribers.
    """
    return get_connection_stats()
"""Main FastAPI application setup"""
import argparse
import logging
from contextlib import asynccontextmanager
from typing import Any

import gevent
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from rotkehlchen.api.v2.config import Settings
from rotkehlchen.api.v2.routers import (
    accounting,
    assets,
    auth,
    balances,
    blockchain,
    data,
    defi,
    eth2,
    exchanges,
    history,
    info,
    locations,
    messages,
    names,
    nfts,
    notes,
    reports,
    settings as settings_router,
    statistics,
    tags,
    tasks,
    users,
    watchers,
)
from rotkehlchen.api.v2.websocket import websocket_endpoint
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.args import app_args
from rotkehlchen.db.drivers.gevent import DBConnection
from rotkehlchen.logging import RotkehlchenLogsAdapter, configure_logging
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.utils.version_check import get_current_version

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: RUF029
    """Manage application lifecycle events"""
    # Initialize Rotkehlchen instance during startup
    arg_parser = app_args(
        prog='rotki-api-v2',
        description='Rotki v2 API server',
    )
    args = arg_parser.parse_args()
    configure_logging(args)
    
    log.info('Starting Rotki v2 API server')
    
    # Create Rotkehlchen instance
    rotkehlchen = Rotkehlchen(args)
    app.state.rotkehlchen = rotkehlchen
    
    # Store the notifier for WebSocket connections
    app.state.rotki_notifier = rotkehlchen.rotki_notifier
    
    # Start the main loop
    main_loop_greenlet = rotkehlchen.start()
    app.state.main_loop_greenlet = main_loop_greenlet
    
    yield
    
    # Cleanup on shutdown
    log.info('Shutting down Rotki v2 API server')
    rotkehlchen.shutdown()
    gevent.wait([main_loop_greenlet])


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application"""
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title='Rotki API',
        description='Accounting, asset management and tax report helper for cryptocurrencies',
        version=get_current_version().our_version,
        lifespan=lifespan,
        docs_url='/api/v2/docs',
        redoc_url='/api/v2/redoc',
        openapi_url='/api/v2/openapi.json',
    )

    # Configure CORS
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

    # Include routers
    app.include_router(auth.router, prefix='/api/v2/auth', tags=['authentication'])
    app.include_router(users.router, prefix='/api/v2/users', tags=['users'])
    app.include_router(settings_router.router, prefix='/api/v2/settings', tags=['settings'])
    app.include_router(assets.router, prefix='/api/v2/assets', tags=['assets'])
    app.include_router(balances.router, prefix='/api/v2/balances', tags=['balances'])
    app.include_router(blockchain.router, prefix='/api/v2/blockchain', tags=['blockchain'])
    app.include_router(exchanges.router, prefix='/api/v2/exchanges', tags=['exchanges'])
    app.include_router(history.router, prefix='/api/v2/history', tags=['history'])
    app.include_router(statistics.router, prefix='/api/v2/statistics', tags=['statistics'])
    app.include_router(reports.router, prefix='/api/v2/reports', tags=['reports'])
    app.include_router(accounting.router, prefix='/api/v2/accounting', tags=['accounting'])
    app.include_router(eth2.router, prefix='/api/v2/blockchains/eth2', tags=['eth2'])
    app.include_router(data.router, prefix='/api/v2/data', tags=['data'])
    app.include_router(nfts.router, prefix='/api/v2/nfts', tags=['nfts'])
    app.include_router(defi.router, prefix='/api/v2/defi', tags=['defi'])
    app.include_router(defi.router, prefix='/api/v2', tags=['defi'])
    app.include_router(names.router, prefix='/api/v2/names', tags=['names'])
    app.include_router(watchers.router, prefix='/api/v2/watchers', tags=['watchers'])
    app.include_router(info.router, prefix='/api/v2', tags=['info'])
    app.include_router(tags.router, prefix='/api/v2/tags', tags=['tags'])
    app.include_router(notes.router, prefix='/api/v2/notes', tags=['notes'])
    app.include_router(locations.router, prefix='/api/v2/locations', tags=['locations'])
    app.include_router(messages.router, prefix='/api/v2/messages', tags=['messages'])
    app.include_router(tasks.router, prefix='/api/v2/tasks', tags=['tasks'])

    # WebSocket endpoint
    @app.websocket('/api/v2/ws')
    async def websocket(websocket: WebSocket):
        """WebSocket endpoint for real-time updates"""
        await websocket_endpoint(websocket)
    
    return app

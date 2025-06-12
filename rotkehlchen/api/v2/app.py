"""Main FastAPI application setup"""
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rotkehlchen.api.v2.config import Settings
from rotkehlchen.api.v2.routers import (
    assets,
    auth,
    balances,
    blockchain,
    exchanges,
    history,
    settings as settings_router,
    statistics,
    users,
)
from rotkehlchen.utils.version_check import get_current_version


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle events"""
    yield


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

    @app.get('/api/v2/ping')
    async def ping() -> dict[str, Any]:
        """Health check endpoint"""
        return {'result': True}

    @app.get('/api/v2/info')
    async def info() -> dict[str, Any]:
        """Get application information"""
        version_info = get_current_version()
        return {
            'result': {
                'version': version_info.our_version,
                'data_directory': str(settings.data_dir),
            },
        }

    return app

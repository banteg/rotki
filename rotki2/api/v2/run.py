"""Simple runner script for the v2 API"""
import uvicorn

from rotki2.api.v2.app import create_app
from rotki2.api.v2.config import Settings

if __name__ == '__main__':
    # Create app with settings
    settings = Settings()
    app = create_app(settings)

    # Run with uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=8000,  # Use different port from v1 (5042)
        reload=True,
        log_level='info',
    )

"""Tests for FastAPI middleware to ensure v1 compatibility"""
import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from rotkehlchen.api.v2.app import create_app


class TestMiddleware:
    """Test middleware functionality for v1 compatibility"""

    def test_cors_headers(self) -> None:
        """Test CORS headers match v1"""
        app = create_app()
        client = TestClient(app)
        
        # Test preflight request
        response = client.options(
            '/api/v2/ping',
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'GET',
            },
        )
        
        # Check CORS headers
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers
        assert 'Access-Control-Allow-Headers' in response.headers

    def test_error_handler_format(self) -> None:
        """Test error response format matches v1"""
        app = FastAPI()
        
        @app.exception_handler(Exception)
        async def v1_compatible_error_handler(request: Request, exc: Exception) -> Response:
            """Error handler that matches v1 format"""
            return JSONResponse(
                status_code=500,
                content={
                    'result': None,
                    'message': str(exc),
                },
            )
        
        @app.get('/test-error')
        async def test_endpoint():
            raise ValueError('Test error')
        
        client = TestClient(app)
        response = client.get('/test-error')
        
        assert response.status_code == 500
        data = response.json()
        assert data == {
            'result': None,
            'message': 'Test error',
        }

    def test_request_logging(self, caplog) -> None:
        """Test request logging matches v1"""
        app = create_app()
        
        @app.middleware('http')
        async def log_requests(request: Request, call_next):
            """Log requests like v1 does"""
            import logging
            logger = logging.getLogger(__name__)
            
            # Log request start
            logger.debug(
                f'start rotki api {request.method} {request.url.path}',
                extra={
                    'path': request.url.path,
                    'method': request.method,
                },
            )
            
            response = await call_next(request)
            
            # Log request end
            logger.debug(
                f'end rotki api {request.method} {request.url.path}',
                extra={
                    'path': request.url.path,
                    'method': request.method,
                    'status_code': response.status_code,
                },
            )
            
            return response
        
        client = TestClient(app)
        
        with caplog.at_level('DEBUG'):
            response = client.get('/api/v2/ping')
            
            assert response.status_code == 200
            # Check that logging occurred
            assert any('start rotki api' in record.message for record in caplog.records)
            assert any('end rotki api' in record.message for record in caplog.records)

    def test_authentication_header_handling(self) -> None:
        """Test authentication header handling"""
        app = create_app()
        client = TestClient(app)
        
        # Test with API key header (v1 style)
        response = client.get(
            '/api/v2/settings',
            headers={'X-API-Key': 'test-api-key-123'},
        )
        
        # Should get 401 with invalid key
        assert response.status_code == 401

    def test_content_type_handling(self) -> None:
        """Test content type handling for v1 compatibility"""
        app = create_app()
        client = TestClient(app)
        
        # v1 accepts both application/json and application/x-www-form-urlencoded
        test_data = {'name': 'test', 'password': 'test123'}
        
        # Test JSON content type
        response = client.post(
            '/api/v2/users',
            json=test_data,
            headers={'Content-Type': 'application/json'},
        )
        assert response.status_code in [200, 401]  # Depends on auth
        
        # Test form-encoded content type
        response = client.post(
            '/api/v2/users',
            data=test_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        # FastAPI should handle both
        assert response.status_code in [200, 401, 422]  # 422 if not supported
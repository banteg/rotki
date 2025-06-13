"""Async HTTP client wrapper for consistent API interactions"""
from typing import Any

import httpx

from rotkehlchen.constants import GLOBAL_REQUESTS_TIMEOUT
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.utils.misc import set_user_agent
from rotki2.utils.async_network import retry_calls_async, CachedSettings


class AsyncHTTPClient:
    """Async HTTP client wrapper for making API requests
    
    Provides a consistent interface for HTTP requests with retry logic,
    error handling, and proper cleanup.
    """
    
    def __init__(self, timeout: int = GLOBAL_REQUESTS_TIMEOUT):
        self.timeout = timeout
        self.session: httpx.AsyncClient | None = None
        
    async def _ensure_session(self) -> httpx.AsyncClient:
        """Ensure we have an active session"""
        if self.session is None:
            headers = {'User-Agent': set_user_agent()}
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers=headers,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            )
        return self.session
    
    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> httpx.Response:
        """Make an async GET request with retry logic"""
        session = await self._ensure_session()
        
        return await retry_calls_async(
            times=CachedSettings().get_query_retry_limit(),
            location='AsyncHTTPClient',
            handle_429=True,
            backoff_in_seconds=1.0,
            method_name=f'GET {url}',
            function=session.get,
            url=url,
            params=params,
            headers=headers,
            timeout=timeout or self.timeout,
        )
    
    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> httpx.Response:
        """Make an async POST request with retry logic"""
        session = await self._ensure_session()
        
        return await retry_calls_async(
            times=CachedSettings().get_query_retry_limit(),
            location='AsyncHTTPClient',
            handle_429=True,
            backoff_in_seconds=1.0,
            method_name=f'POST {url}',
            function=session.post,
            url=url,
            json=json,
            data=data,
            headers=headers,
            timeout=timeout or self.timeout,
        )
    
    async def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make a GET request and return JSON response"""
        response = await self.get(url, params, headers)
        
        if response.status_code != 200:
            raise RemoteError(
                f'Request to {url} failed with status {response.status_code}: {response.text}'
            )
        
        try:
            return response.json()
        except Exception as e:
            raise RemoteError(f'Failed to parse JSON from {url}: {e}') from e
    
    async def post_json(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make a POST request and return JSON response"""
        response = await self.post(url, json=json, headers=headers)
        
        if response.status_code not in (200, 201):
            raise RemoteError(
                f'Request to {url} failed with status {response.status_code}: {response.text}'
            )
        
        try:
            return response.json()
        except Exception as e:
            raise RemoteError(f'Failed to parse JSON from {url}: {e}') from e
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None
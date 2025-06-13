"""Generic API client wrapper for exchange implementations.

This module provides a reusable HTTP client that handles common concerns
like retries, timeouts, rate limiting, and error handling.
"""
import logging
from collections.abc import Mapping
from enum import Enum, auto
from http import HTTPStatus
from typing import Any, Literal, overload

import aiohttp
from aiohttp import ClientResponse, ClientSession, ClientTimeout
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from rotki2.errors.api import (
    ExchangeApiError,
    ExchangeDataError,
    ExchangePermissionError,
    ExchangeRateLimitError,
)
from rotki2.errors.misc import RemoteError
from rotki2.globaldb.updates import GLOBAL_DB_VERSION
from rotki2.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RequestMethod(Enum):
    """HTTP request methods."""
    GET = auto()
    POST = auto()
    PUT = auto()
    DELETE = auto()
    PATCH = auto()


class GenericApiClient:
    """A generic HTTP client for exchange API interactions.
    
    This client provides:
    - Automatic retries with exponential backoff
    - Rate limit handling
    - Timeout configuration
    - JSON response parsing
    - Common error handling patterns
    """
    
    def __init__(
        self,
        name: str,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the generic API client.
        
        Args:
            name: Name of the exchange for logging
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            session: Optional aiohttp session to reuse
        """
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self._session = session
        self._owned_session = session is None
        
    async def __aenter__(self) -> 'GenericApiClient':
        """Async context manager entry."""
        if self._owned_session and self._session is None:
            self._session = ClientSession(
                timeout=self.timeout,
                headers={
                    'User-Agent': f'rotki/{GLOBAL_DB_VERSION}',
                },
            )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._owned_session and self._session is not None:
            await self._session.close()
            self._session = None
    
    @overload
    async def request(
        self,
        method: RequestMethod,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_response: Literal[True] = True,
    ) -> dict[str, Any] | list[Any]: ...
    
    @overload
    async def request(
        self,
        method: RequestMethod,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_response: Literal[False],
    ) -> str: ...
    
    async def request(
        self,
        method: RequestMethod,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_response: bool = True,
    ) -> dict[str, Any] | list[Any] | str:
        """Make an HTTP request to the API.
        
        Args:
            method: HTTP method to use
            path: API endpoint path (will be appended to base_url)
            params: Query parameters
            data: Form data to send
            json: JSON data to send
            headers: Additional headers
            json_response: Whether to parse response as JSON
            
        Returns:
            Parsed JSON response or raw text
            
        Raises:
            ExchangeApiError: For API-specific errors
            ExchangeRateLimitError: For rate limit errors
            RemoteError: For network/connection errors
        """
        if self._session is None:
            raise RuntimeError('Client session not initialized. Use async context manager.')
            
        url = f'{self.base_url}/{path.lstrip("/")}'
        
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((
                aiohttp.ClientError,
                ExchangeRateLimitError,
            )),
            reraise=True,
        ):
            with attempt:
                try:
                    async with self._session.request(
                        method=method.name,
                        url=url,
                        params=params,
                        data=data,
                        json=json,
                        headers=headers,
                    ) as response:
                        return await self._handle_response(
                            response=response,
                            json_response=json_response,
                        )
                except aiohttp.ClientError as e:
                    log.error(
                        f'{self.name} API request failed',
                        url=url,
                        method=method.name,
                        error=str(e),
                    )
                    raise RemoteError(f'{self.name} API request failed: {e}') from e
    
    async def _handle_response(
        self,
        response: ClientResponse,
        json_response: bool,
    ) -> dict[str, Any] | list[Any] | str:
        """Handle API response and errors.
        
        Args:
            response: The HTTP response
            json_response: Whether to parse as JSON
            
        Returns:
            Parsed response data
            
        Raises:
            ExchangeApiError: For API errors
            ExchangeRateLimitError: For rate limiting
            ExchangePermissionError: For permission errors
        """
        if response.status == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = response.headers.get('Retry-After', '60')
            raise ExchangeRateLimitError(
                f'{self.name} rate limit exceeded. Retry after {retry_after}s',
            )
            
        text = await response.text()
        
        if response.status >= 400:
            self._handle_error_response(
                status=response.status,
                text=text,
                headers=response.headers,
            )
            
        if not json_response:
            return text
            
        try:
            return await response.json()
        except (ValueError, aiohttp.ContentTypeError) as e:
            raise ExchangeDataError(
                f'{self.name} returned invalid JSON: {text[:200]}',
            ) from e
    
    def _handle_error_response(
        self,
        status: int,
        text: str,
        headers: Mapping[str, str],
    ) -> None:
        """Handle error responses from the API.
        
        Args:
            status: HTTP status code
            text: Response text
            headers: Response headers
            
        Raises:
            ExchangePermissionError: For 401/403 errors
            ExchangeApiError: For other errors
        """
        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise ExchangePermissionError(
                f'{self.name} permission denied. Check API credentials.',
            )
            
        # Try to extract error message from common patterns
        error_msg = text
        try:
            import json as json_module
            data = json_module.loads(text)
            # Common error message fields across exchanges
            for field in ('error', 'message', 'msg', 'error_message'):
                if field in data:
                    error_msg = data[field]
                    break
        except (ValueError, TypeError):
            pass
            
        raise ExchangeApiError(
            f'{self.name} API error (status={status}): {error_msg[:200]}',
        )
    
    async def get(
        self,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """Make a GET request."""
        return await self.request(
            RequestMethod.GET,
            path,
            **kwargs,
        )
    
    async def post(
        self,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """Make a POST request."""
        return await self.request(
            RequestMethod.POST,
            path,
            **kwargs,
        )
    
    async def put(
        self,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """Make a PUT request."""
        return await self.request(
            RequestMethod.PUT,
            path,
            **kwargs,
        )
    
    async def delete(
        self,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """Make a DELETE request."""
        return await self.request(
            RequestMethod.DELETE,
            path,
            **kwargs,
        )
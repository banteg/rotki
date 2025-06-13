"""Base node client for interacting with blockchain RPC nodes."""
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from rotki2.common.errors import RemoteError

logger = logging.getLogger(__name__)


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request structure."""
    jsonrpc: str = "2.0"
    method: str
    params: list[Any] | dict[str, Any] = []
    id: int = 1


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response structure."""
    jsonrpc: str
    id: int
    result: Any = None
    error: dict[str, Any] | None = None


class BaseNodeClient(ABC):
    """Base class for blockchain node clients using httpx for async HTTP requests."""
    
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        node_url: str,
        chain_name: str,
    ) -> None:
        """
        Initialize the base node client.
        
        Args:
            http_client: Async HTTP client for making requests
            node_url: URL of the RPC node
            chain_name: Name of the blockchain
        """
        self.http_client = http_client
        self.node_url = node_url
        self.chain_name = chain_name
        self._request_counter = 0
    
    async def post(
        self,
        method: str,
        params: list[Any] | dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """
        Make a JSON-RPC request to the node.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            timeout: Request timeout in seconds
            
        Returns:
            The result from the JSON-RPC response
            
        Raises:
            RemoteError: If the request fails or returns an error
        """
        self._request_counter += 1
        
        request = JsonRpcRequest(
            method=method,
            params=params or [],
            id=self._request_counter,
        )
        
        logger.debug(f"Making JSON-RPC request to {self.chain_name}: {method}")
        
        try:
            response = await self.http_client.post(
                self.node_url,
                json=request.model_dump(),
                timeout=timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            msg = f"HTTP error calling {self.chain_name} node at {self.node_url}: {e}"
            logger.error(msg)
            raise RemoteError(msg) from e
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON response from {self.chain_name} node: {response.text}"
            logger.error(msg)
            raise RemoteError(msg) from e
        
        # Parse response
        try:
            rpc_response = JsonRpcResponse(**data)
        except Exception as e:
            msg = f"Invalid JSON-RPC response structure from {self.chain_name}: {data}"
            logger.error(msg)
            raise RemoteError(msg) from e
        
        # Check for errors
        if rpc_response.error:
            error_msg = rpc_response.error.get("message", "Unknown error")
            error_code = rpc_response.error.get("code", -1)
            msg = f"JSON-RPC error from {self.chain_name}: [{error_code}] {error_msg}"
            logger.error(msg)
            raise RemoteError(msg)
        
        return rpc_response.result
    
    async def batch_post(
        self,
        requests: list[tuple[str, list[Any] | dict[str, Any] | None]],
        timeout: float | None = None,
    ) -> list[Any]:
        """
        Make a batch JSON-RPC request to the node.
        
        Args:
            requests: List of (method, params) tuples
            timeout: Request timeout in seconds
            
        Returns:
            List of results in the same order as requests
            
        Raises:
            RemoteError: If the request fails or returns errors
        """
        batch_requests = []
        for i, (method, params) in enumerate(requests):
            self._request_counter += 1
            batch_requests.append(
                JsonRpcRequest(
                    method=method,
                    params=params or [],
                    id=self._request_counter,
                ).model_dump()
            )
        
        logger.debug(f"Making batch JSON-RPC request to {self.chain_name}: {len(requests)} calls")
        
        try:
            response = await self.http_client.post(
                self.node_url,
                json=batch_requests,
                timeout=timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            msg = f"HTTP error calling {self.chain_name} node at {self.node_url}: {e}"
            logger.error(msg)
            raise RemoteError(msg) from e
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON response from {self.chain_name} node: {response.text}"
            logger.error(msg)
            raise RemoteError(msg) from e
        
        if not isinstance(data, list):
            msg = f"Expected list response from batch request, got: {type(data)}"
            raise RemoteError(msg)
        
        # Sort responses by ID to match request order
        responses_by_id = {}
        for item in data:
            try:
                rpc_response = JsonRpcResponse(**item)
                responses_by_id[rpc_response.id] = rpc_response
            except Exception as e:
                msg = f"Invalid JSON-RPC response in batch from {self.chain_name}: {item}"
                logger.error(msg)
                raise RemoteError(msg) from e
        
        # Extract results in order
        results = []
        start_id = self._request_counter - len(requests) + 1
        for i in range(len(requests)):
            response_id = start_id + i
            if response_id not in responses_by_id:
                msg = f"Missing response for request ID {response_id} in batch"
                raise RemoteError(msg)
            
            rpc_response = responses_by_id[response_id]
            if rpc_response.error:
                error_msg = rpc_response.error.get("message", "Unknown error")
                error_code = rpc_response.error.get("code", -1)
                msg = f"JSON-RPC error in batch from {self.chain_name}: [{error_code}] {error_msg}"
                logger.error(msg)
                raise RemoteError(msg)
            
            results.append(rpc_response.result)
        
        return results
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if the node is connected and responsive."""
        ...
    
    @abstractmethod
    async def get_block_number(self) -> int:
        """Get the current block number."""
        ...
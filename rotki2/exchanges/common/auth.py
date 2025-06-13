"""Common authentication helpers for exchange implementations.

This module provides reusable authentication components like HMAC signers
that can be configured for different exchanges.
"""
import base64
import hashlib
import hmac
import time
from enum import Enum, auto
from typing import Any, Callable, Literal

from rotki2.types import Timestamp


class HashAlgorithm(Enum):
    """Supported hash algorithms for HMAC signing."""
    SHA256 = auto()
    SHA512 = auto()
    SHA384 = auto()
    MD5 = auto()
    
    def get_hashlib(self) -> Callable:
        """Get the hashlib function for this algorithm."""
        mapping = {
            HashAlgorithm.SHA256: hashlib.sha256,
            HashAlgorithm.SHA512: hashlib.sha512,
            HashAlgorithm.SHA384: hashlib.sha384,
            HashAlgorithm.MD5: hashlib.md5,
        }
        return mapping[self]


class Encoding(Enum):
    """Supported encoding formats for signatures."""
    HEX = auto()
    BASE64 = auto()
    BASE64_URLSAFE = auto()


class HmacSigner:
    """A configurable HMAC signer for API authentication.
    
    This class consolidates the scattered HMAC logic from various exchanges
    into a single, reusable component.
    """
    
    def __init__(
        self,
        secret: str | bytes,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
        encoding: Encoding = Encoding.HEX,
        decode_secret: bool = True,
    ) -> None:
        """Initialize the HMAC signer.
        
        Args:
            secret: The API secret key
            algorithm: Hash algorithm to use
            encoding: Output encoding format
            decode_secret: Whether to base64-decode the secret first
        """
        if isinstance(secret, str):
            if decode_secret:
                self.secret = base64.b64decode(secret)
            else:
                self.secret = secret.encode('utf-8')
        else:
            self.secret = secret
            
        self.algorithm = algorithm
        self.encoding = encoding
        self.hash_func = algorithm.get_hashlib()
    
    def sign(self, message: str | bytes) -> str:
        """Sign a message with HMAC.
        
        Args:
            message: The message to sign
            
        Returns:
            The HMAC signature as a string
        """
        if isinstance(message, str):
            message = message.encode('utf-8')
            
        h = hmac.new(
            self.secret,
            message,
            self.hash_func,
        )
        
        if self.encoding == Encoding.HEX:
            return h.hexdigest()
        elif self.encoding == Encoding.BASE64:
            return base64.b64encode(h.digest()).decode('ascii')
        elif self.encoding == Encoding.BASE64_URLSAFE:
            return base64.urlsafe_b64encode(h.digest()).decode('ascii')
        else:
            raise ValueError(f'Unsupported encoding: {self.encoding}')
    
    def sign_dict(
        self,
        data: dict[str, Any],
        separator: str = '&',
        sort_keys: bool = True,
    ) -> str:
        """Sign a dictionary by converting it to a query string.
        
        Args:
            data: Dictionary to sign
            separator: Separator between key-value pairs
            sort_keys: Whether to sort keys before signing
            
        Returns:
            The HMAC signature
        """
        pairs = []
        items = sorted(data.items()) if sort_keys else data.items()
        
        for key, value in items:
            pairs.append(f'{key}={value}')
            
        message = separator.join(pairs)
        return self.sign(message)


class ApiKeySigner:
    """Simple API key signer for exchanges that don't use HMAC."""
    
    def __init__(self, api_key: str) -> None:
        """Initialize with API key."""
        self.api_key = api_key
    
    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        return {'X-API-KEY': self.api_key}


class NonceGenerator:
    """Generate nonces for API requests.
    
    Some exchanges require unique, increasing nonces for each request.
    """
    
    def __init__(
        self,
        mode: Literal['timestamp_ms', 'timestamp_us', 'counter'] = 'timestamp_ms',
        initial_value: int = 0,
    ) -> None:
        """Initialize the nonce generator.
        
        Args:
            mode: Nonce generation mode
            initial_value: Initial counter value (for counter mode)
        """
        self.mode = mode
        self._counter = initial_value
        self._last_nonce = 0
    
    def generate(self) -> str:
        """Generate a new nonce."""
        if self.mode == 'timestamp_ms':
            nonce = int(time.time() * 1000)
        elif self.mode == 'timestamp_us':
            nonce = int(time.time() * 1000000)
        elif self.mode == 'counter':
            self._counter += 1
            nonce = self._counter
        else:
            raise ValueError(f'Unsupported nonce mode: {self.mode}')
        
        # Ensure nonce is always increasing
        if nonce <= self._last_nonce:
            nonce = self._last_nonce + 1
        self._last_nonce = nonce
        
        return str(nonce)


def create_signature_payload(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    body: str | None = None,
    timestamp: Timestamp | None = None,
) -> str:
    """Create a signature payload in a common format.
    
    Many exchanges use a similar pattern for creating the message to sign:
    timestamp + method + path + body
    
    Args:
        method: HTTP method
        path: Request path
        params: Query parameters
        body: Request body
        timestamp: Request timestamp
        
    Returns:
        The payload to sign
    """
    if timestamp is None:
        timestamp = Timestamp(int(time.time()))
        
    parts = [str(timestamp), method.upper(), path]
    
    if params:
        # Convert params to query string
        query_parts = []
        for key, value in sorted(params.items()):
            query_parts.append(f'{key}={value}')
        if query_parts:
            parts.append('?' + '&'.join(query_parts))
    
    if body:
        parts.append(body)
        
    return ''.join(parts)
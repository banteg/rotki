# Exchange Architecture Migration Guide

This guide explains how to migrate an exchange from the monolithic architecture to the new Ports & Adapters architecture.

## Overview

The new architecture separates concerns into three main components:
1. **API Client**: Handles HTTP communication and authentication
2. **Data Mapper**: Transforms raw API data to Rotki domain models
3. **Service**: Orchestrates client and mapper

## Step-by-Step Migration

### 1. Create Directory Structure

```bash
rotki2/exchanges/adapters/<exchange_name>/
├── __init__.py
├── client.py     # API client implementation
└── mapper.py     # Data mapper implementation
```

### 2. Implement the API Client

Create `client.py` implementing `ExchangeApiClientPort`:

```python
from rotki2.exchanges.common.client import GenericApiClient
from rotki2.exchanges.ports import ExchangeApiClientPort

class YourExchangeApiClient(ExchangeApiClientPort):
    def __init__(self, api_key: str, secret: str, **kwargs):
        self.api_key = api_key
        self.secret = secret
        self.client = GenericApiClient(
            name='YourExchange',
            base_url='https://api.yourexchange.com',
        )
    
    async def __aenter__(self):
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    # Implement required methods...
```

### 3. Implement the Data Mapper

Create `mapper.py` implementing `ExchangeDataMapperPort`:

```python
from rotki2.exchanges.ports import ExchangeDataMapperPort

class YourExchangeDataMapper(ExchangeDataMapperPort):
    def to_balances(self, raw_data: list[dict]) -> dict[Asset, AssetAmount]:
        # Transform raw balance data
        pass
    
    def to_trades(self, raw_data: list[dict], location: Location) -> list[Trade]:
        # Transform raw trade data
        pass
    
    # Implement other required methods...
```

### 4. Register with the Factory

In `service.py`, add:

```python
from rotki2.exchanges.adapters.yourexchange.client import YourExchangeApiClient
from rotki2.exchanges.adapters.yourexchange.mapper import YourExchangeDataMapper

ExchangeServiceFactory.register(
    Location.YOUREXCHANGE,
    YourExchangeApiClient,
    YourExchangeDataMapper,
)
```

### 5. Enable in Manager

In `manager_v2.py`, add your exchange to:

```python
MIGRATED_EXCHANGES = {Location.OKX, Location.YOUREXCHANGE}
```

## Migration Checklist

- [ ] Extract authentication logic to use `common/auth.py` utilities
- [ ] Move HTTP requests to client adapter
- [ ] Move data transformation to mapper adapter
- [ ] Remove business logic from API communication
- [ ] Add proper error handling in both adapters
- [ ] Write unit tests for mapper (no mocking needed!)
- [ ] Write integration tests for client
- [ ] Update factory registration
- [ ] Add to MIGRATED_EXCHANGES set
- [ ] Test full flow through manager

## Common Patterns

### Authentication

Most exchanges use HMAC signatures. Use the common `HmacSigner`:

```python
from rotki2.exchanges.common.auth import HmacSigner, HashAlgorithm, Encoding

# For SHA256 with hex encoding (e.g., Binance)
signer = HmacSigner(
    secret=self.secret,
    algorithm=HashAlgorithm.SHA256,
    encoding=Encoding.HEX,
)

# For SHA512 with base64 (e.g., Kraken)
signer = HmacSigner(
    secret=self.secret,
    algorithm=HashAlgorithm.SHA512,
    encoding=Encoding.BASE64,
    decode_secret=True,  # If secret needs base64 decoding
)
```

### Error Handling

The `GenericApiClient` handles common errors. Exchange-specific errors should be handled in the client:

```python
response = await self.client.get(path)
if response.get('error'):
    # Handle exchange-specific error format
    raise ExchangeApiError(response['error'])
```

### Asset Mapping

Always use the exchange's asset converter:

```python
from rotki2.assets.converters import asset_from_yourexchange

try:
    asset = asset_from_yourexchange(symbol)
except (UnknownAsset, UnsupportedAsset):
    # Handle unknown assets
    return None
```

## Testing

The new architecture greatly improves testability:

### Unit Testing Mappers

```python
def test_balance_mapping():
    mapper = YourExchangeDataMapper()
    raw_data = [{'symbol': 'BTC', 'free': '1.5', 'locked': '0.5'}]
    
    balances = mapper.to_balances(raw_data)
    
    assert balances[A_BTC] == AssetAmount('2.0')
```

### Integration Testing Clients

```python
async def test_client_authentication():
    async with YourExchangeApiClient(api_key='test', secret='test') as client:
        # Test with mock server or exchange sandbox
        balances = await client.get_balances()
        assert isinstance(balances, list)
```

## Benefits

1. **Testability**: Test business logic without network calls
2. **Maintainability**: Changes isolated to specific components
3. **Reusability**: Common patterns extracted to shared utilities
4. **Flexibility**: Easy to mock/stub for testing
5. **Performance**: Opportunities for optimization in each layer
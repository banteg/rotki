# V1 API Deprecation Guide

## Overview

The v1 API is being deprecated in favor of the new v2 FastAPI implementation. This guide helps you migrate from v1 to v2.

## Timeline

- **Current Status**: Both v1 and v2 APIs are available
- **Deprecation Date**: TBD (recommended: 6 months from v2 release)
- **Removal Date**: TBD (recommended: 12 months from v2 release)

## Key Changes

### 1. Base URL

- **v1**: `/api/1/*`
- **v2**: `/api/v2/*`

### 2. Authentication

#### API Keys
- **v1**: Use header `rotki-api-key`
- **v2**: Use header `X-API-Key`

```bash
# v1
curl -H "rotki-api-key: your-key" http://localhost:8080/api/1/balances

# v2
curl -H "X-API-Key: your-key" http://localhost:8080/api/v2/balances
```

### 3. Response Format

Both versions use the same response format:
- Success: `{"result": <data>}`
- Error: `{"message": <error>, "status_code": <code>}`

### 4. Endpoint Mapping

| v1 Endpoint | v2 Endpoint | Notes |
|------------|-------------|-------|
| `/api/1/users` | `/api/v2/users` | Same functionality |
| `/api/1/balances` | `/api/v2/balances` | Same response format |
| `/api/1/assets/all` | `/api/v2/assets/all` | Same response format |
| `/api/1/history/events` | `/api/v2/history/events` | Same query parameters |
| `/api/1/reports` | `/api/v2/reports` | Same functionality |
| `/api/1/exchanges` | `/api/v2/exchanges` | Same functionality |
| `/api/1/blockchains/eth2/*` | `/api/v2/blockchains/eth2/*` | New ETH2 endpoints |
| `/api/1/import` | `/api/v2/data/import` | Moved under data namespace |
| `/api/1/export` | `/api/v2/data/export` | Moved under data namespace |

### 5. New Features in v2

- **WebSocket Support**: Real-time updates at `/api/v2/ws`
- **Better Documentation**: OpenAPI docs at `/api/v2/docs`
- **Type Safety**: All endpoints have proper type validation
- **Async Support**: Better performance for concurrent operations

### 6. Migration Steps

1. **Update API Key Headers**
   ```python
   # Old
   headers = {"rotki-api-key": api_key}
   
   # New
   headers = {"X-API-Key": api_key}
   ```

2. **Update Base URLs**
   ```python
   # Old
   base_url = "http://localhost:8080/api/1"
   
   # New
   base_url = "http://localhost:8080/api/v2"
   ```

3. **Test Your Integration**
   - Run both APIs in parallel during migration
   - Compare responses to ensure compatibility
   - Use the compatibility test suite

4. **Update WebSocket Connections**
   ```javascript
   // New WebSocket support
   const ws = new WebSocket('ws://localhost:8080/api/v2/ws');
   ws.onmessage = (event) => {
     const data = JSON.parse(event.data);
     // Handle real-time updates
   };
   ```

### 7. Running Both APIs

During the migration period, you can run both APIs:

```bash
# Start v1 API (default port 8080)
rotki-api

# Start v2 API (different port)
uv run uvicorn rotkehlchen.api.v2.app:create_app --factory --port 8001
```

### 8. Common Issues

1. **Authentication Errors**
   - Ensure you're using the correct header name
   - API keys are the same between v1 and v2

2. **Missing Endpoints**
   - Some specialized endpoints may not be ported yet
   - Check the migration status document

3. **Response Format Differences**
   - Core format is the same
   - Some field names may have changed for clarity

### 9. Getting Help

- Report issues: https://github.com/rotki/rotki/issues
- Documentation: https://rotki.readthedocs.io
- Discord: https://discord.rotki.com

## Deprecation Warnings

Starting from version X.Y.Z, v1 endpoints will return deprecation warnings:

```json
{
  "result": {...},
  "_deprecation": {
    "message": "This v1 endpoint is deprecated. Please use v2.",
    "v2_endpoint": "/api/v2/balances",
    "deprecation_date": "2024-12-01",
    "removal_date": "2025-06-01"
  }
}
```

## Final Notes

The v2 API is designed to be more maintainable, performant, and developer-friendly. While we've maintained compatibility where possible, some breaking changes were necessary to fix architectural issues in v1.

We recommend starting migration as soon as possible to take advantage of the improvements in v2.
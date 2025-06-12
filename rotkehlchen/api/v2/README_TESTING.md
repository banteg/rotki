# Testing the FastAPI v2 API

## Quick Start

### 1. Run the FastAPI server standalone

```bash
# Install dependencies
uv sync

# Run the FastAPI server
uv run uvicorn rotkehlchen.api.v2.app:create_app --factory --reload --port 8000

# Or create a simple runner script
uv run python -m rotkehlchen.api.v2.run
```

### 2. Test with curl

```bash
# Test ping endpoint (no auth required)
curl http://localhost:8000/api/v2/ping

# Test info endpoint
curl http://localhost:8000/api/v2/info

# Test with API key header
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v2/settings
```

### 3. Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/api/v2/docs
- **ReDoc**: http://localhost:8000/api/v2/redoc

## Running Tests

### Unit Tests

```bash
# Run v2 API tests
uv run pytest rotkehlchen/tests/api/v2/ -v

# Run specific test file
uv run pytest rotkehlchen/tests/api/v2/test_response_format.py -v

# Run with coverage
uv run pytest rotkehlchen/tests/api/v2/ --cov=rotkehlchen.api.v2 --cov-report=html
```

### Compatibility Tests

```bash
# Run compatibility tests between v1 and v2
uv run pytest rotkehlchen/tests/api/v2/test_compatibility.py -v

# Run endpoint parity tests
uv run pytest rotkehlchen/tests/api/v2/test_endpoint_parity.py -v
```

### Integration Tests

```bash
# Test with real database
uv run pytest rotkehlchen/tests/api/v2/ -m integration

# Test with mock services
uv run pytest rotkehlchen/tests/api/v2/ -m "not integration"
```

## Manual Testing

### 1. Create a test script

```python
# test_v2_api.py
import requests
import json

BASE_URL = "http://localhost:8000/api/v2"

# Test ping
response = requests.get(f"{BASE_URL}/ping")
print(f"Ping: {response.json()}")

# Test user creation
user_data = {
    "name": "test_user",
    "password": "test_password123",
    "initial_settings": {
        "main_currency": "USD",
        "submit_usage_analytics": False
    }
}
response = requests.post(f"{BASE_URL}/users", json=user_data)
print(f"Create user: {response.json()}")

# Test login
login_data = {
    "name": "test_user",
    "password": "test_password123"
}
response = requests.post(f"{BASE_URL}/users/login", json=login_data)
print(f"Login: {response.json()}")
```

### 2. Use HTTPie for better CLI testing

```bash
# Install httpie
pip install httpie

# Test endpoints
http GET localhost:8000/api/v2/ping
http GET localhost:8000/api/v2/info
http POST localhost:8000/api/v2/users name=test password=test123
```

### 3. Use Postman or Insomnia

Import the OpenAPI schema from http://localhost:8000/api/v2/openapi.json

## Testing Specific Features

### Authentication

```python
# Test API key authentication
headers = {"X-API-Key": "test-api-key-123"}
response = requests.get(f"{BASE_URL}/settings", headers=headers)
```

### Assets

```python
# Search assets
params = {"search_term": "BTC", "limit": 10}
response = requests.get(f"{BASE_URL}/assets/search", params=params)

# Get asset prices
price_data = {
    "assets": ["BTC", "ETH", "USDC"],
    "target_asset": "USD"
}
response = requests.post(f"{BASE_URL}/assets/prices/latest", json=price_data)
```

### Balances

```python
# Get all balances
response = requests.get(f"{BASE_URL}/balances", headers=headers)

# Get blockchain balances
response = requests.get(f"{BASE_URL}/balances/blockchains", headers=headers)
```

## Performance Testing

```bash
# Install locust
pip install locust

# Create locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class RotkiUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def ping(self):
        self.client.get("/api/v2/ping")
    
    @task(3)
    def get_assets(self):
        self.client.get("/api/v2/assets/all?limit=100")
    
    @task(2)
    def search_assets(self):
        self.client.get("/api/v2/assets/search?search_term=BTC")
EOF

# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

## Debugging

### Enable debug logging

```python
# In your test or script
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check request/response details

```python
# Use FastAPI TestClient for detailed debugging
from fastapi.testclient import TestClient
from rotkehlchen.api.v2.app import create_app

app = create_app()
client = TestClient(app)

response = client.get("/api/v2/ping")
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Body: {response.json()}")
```

## Common Issues

### 1. Port already in use
```bash
# Find process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
```

### 2. Database connection issues
```bash
# Use in-memory database for testing
export ROTKI_DATA_DIR=/tmp/test_rotki
```

### 3. Missing dependencies
```bash
# Ensure all dependencies are installed
uv sync
```

## CI/CD Integration

```yaml
# .github/workflows/test-v2-api.yml
name: Test V2 API

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run pytest rotkehlchen/tests/api/v2/ -v
      - run: uv run pytest rotkehlchen/tests/api/v2/test_compatibility.py -v
```
#!/usr/bin/env python
"""Demo script showing v2 API features"""
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

# Create demo FastAPI app
app = FastAPI(
    title='Rotki v2 API Demo',
    description='Demonstration of clean architecture patterns',
    version='2.0.0',
)

# --- Models (Pure validation, no I/O) ---


class UserCreateRequest(BaseModel):
    """Pure validation model - no DB calls"""
    name: str
    password: str
    initial_settings: dict[str, Any] | None = None


class AssetPriceRequest(BaseModel):
    """Pure validation model"""
    assets: list[str]
    target_asset: str = 'USD'


class BlockchainAccountRequest(BaseModel):
    """Pure validation model - no ENS resolution here"""
    accounts: list[str]  # Can be addresses or ENS names
    labels: list[str] | None = None

# --- Services (Business logic goes here) ---


class MockDatabaseService:
    """Mock database service"""
    def __init__(self):
        self.users = {}
        self.settings = {}
        self.accounts = {}

    def create_user(self, name: str, password: str) -> dict:
        """Create user in DB"""
        self.users[name] = {'password': password}
        return {'name': name}

    def get_settings(self, user: str) -> dict:
        """Get user settings"""
        return self.settings.get(user, {'main_currency': 'USD'})


class MockBlockchainService:
    """Mock blockchain service - ENS resolution happens here"""
    def resolve_ens(self, name: str) -> str:
        """Resolve ENS name to address (mock)"""
        # In real implementation, this would make network call
        mock_ens = {
            'vitalik.eth': '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045',
            'uniswap.eth': '0x1a9C8182C09F50C8318d769245beA52c32BE35BC',
        }
        return mock_ens.get(name, f"0x{'0' * 40}")

    def add_accounts(self, accounts: list[str]) -> list[str]:
        """Add blockchain accounts - handles ENS resolution"""
        resolved = []
        for account in accounts:
            if account.endswith('.eth'):
                # ENS resolution in service layer, not validation!
                address = self.resolve_ens(account)
                resolved.append(address)
            else:
                resolved.append(account)
        return resolved


class MockAssetService:
    """Mock asset service"""
    def get_prices(self, assets: list[str], target: str) -> dict[str, str]:
        """Get asset prices"""
        mock_prices = {
            'BTC': '50000',
            'ETH': '3000',
            'USDC': '1',
        }
        return {asset: mock_prices.get(asset, '0') for asset in assets}


# --- Dependency Injection ---

# Create singleton instances
db_service = MockDatabaseService()
blockchain_service = MockBlockchainService()
asset_service = MockAssetService()


def get_db() -> MockDatabaseService:
    return db_service


def get_blockchain_service() -> MockBlockchainService:
    return blockchain_service


def get_asset_service() -> MockAssetService:
    return asset_service


# Mock authentication
async def require_logged_in_user() -> str:
    """Mock auth dependency"""
    return 'demo_user'

# --- API Endpoints ---


@app.get('/api/v2/ping')
async def ping():
    """Health check - no auth required"""
    return {'result': True}


@app.post('/api/v2/users')
async def create_user(
    user_data: UserCreateRequest,
    db: Annotated[MockDatabaseService, Depends(get_db)],
):
    """Create user - validation is pure, DB access in service"""
    # Validation already happened in UserCreateRequest
    # Business logic in service
    user = db.create_user(user_data.name, user_data.password)
    return {'result': user, 'message': 'User created successfully'}


@app.get('/api/v2/settings')
async def get_settings(
    user: Annotated[str, Depends(require_logged_in_user)],
    db: Annotated[MockDatabaseService, Depends(get_db)],
):
    """Get settings - requires authentication"""
    settings = db.get_settings(user)
    return {'result': settings}


@app.post('/api/v2/blockchain/eth/accounts')
async def add_blockchain_accounts(
    account_data: BlockchainAccountRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    blockchain: Annotated[MockBlockchainService, Depends(get_blockchain_service)],
):
    """Add blockchain accounts - ENS resolution in service, not validation"""
    # Validation is pure - just checks it's a list of strings
    # ENS resolution happens in service layer
    resolved_accounts = blockchain.add_accounts(account_data.accounts)
    return {
        'result': {
            'accounts': resolved_accounts,
            'original': account_data.accounts,
        },
        'message': f'Added {len(resolved_accounts)} accounts',
    }


@app.post('/api/v2/assets/prices/latest')
async def get_asset_prices(
    price_request: AssetPriceRequest,
    _: Annotated[str, Depends(require_logged_in_user)],
    assets: Annotated[MockAssetService, Depends(get_asset_service)],
):
    """Get asset prices - business logic in service"""
    prices = assets.get_prices(price_request.assets, price_request.target_asset)
    return {
        'result': {
            'prices': prices,
            'target_asset': price_request.target_asset,
        },
    }

# --- Demo Script ---


def run_demo():
    """Run demo showing clean architecture"""
    client = TestClient(app)

    print('🚀 Rotki v2 API Demo - Clean Architecture')
    print('=' * 50)

    # 1. Test ping (no auth)
    print('\n1. Testing ping endpoint (no auth required):')
    response = client.get('/api/v2/ping')
    print(f'   Response: {response.json()}')

    # 2. Create user
    print('\n2. Creating user (pure validation):')
    user_data = {
        'name': 'alice',
        'password': 'secure123',
        'initial_settings': {'main_currency': 'EUR'},
    }
    response = client.post('/api/v2/users', json=user_data)
    print(f'   Response: {response.json()}')

    # 3. Get settings (with auth)
    print('\n3. Getting settings (with authentication):')
    response = client.get('/api/v2/settings')
    print(f'   Response: {response.json()}')

    # 4. Add blockchain accounts with ENS
    print('\n4. Adding blockchain accounts (ENS resolution in service):')
    account_data = {
        'accounts': ['vitalik.eth', 'uniswap.eth', '0x123...'],
        'labels': ['Vitalik', 'Uniswap', 'My wallet'],
    }
    response = client.post('/api/v2/blockchain/eth/accounts', json=account_data)
    result = response.json()
    print(f"   Original: {result['result']['original']}")
    print(f"   Resolved: {result['result']['accounts']}")

    # 5. Get asset prices
    print('\n5. Getting asset prices (business logic in service):')
    price_data = {
        'assets': ['BTC', 'ETH', 'USDC'],
        'target_asset': 'USD',
    }
    response = client.post('/api/v2/assets/prices/latest', json=price_data)
    print(f'   Response: {response.json()}')

    # 6. Show validation error
    print('\n6. Testing validation (pure, no DB/network calls):')
    invalid_user = {
        'name': '',  # Invalid: empty name
        'password': 'test',
    }
    response = client.post('/api/v2/users', json=invalid_user)
    print(f'   Status: {response.status_code}')
    print(f'   Error: {response.json()}')

    print('\n' + '=' * 50)
    print('✅ Demo complete! Key improvements over v1:')
    print('   - Pure validation (no DB/network in schemas)')
    print('   - Explicit dependency injection')
    print('   - Business logic in services')
    print('   - No global state')
    print('   - Testable architecture')


if __name__ == '__main__':
    run_demo()

    print('\n📚 Interactive API docs available at:')
    print('   http://localhost:8000/docs')
    print('\nTo run the server:')
    print('   uvicorn demo_v2_api:app --reload --port 8000')

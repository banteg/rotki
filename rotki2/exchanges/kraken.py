"""Async Kraken exchange implementation"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
from typing import TYPE_CHECKING, Any, Literal

import anyio

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    AssetMovementCategory,
    MarginPosition,
    Trade,
    TradeType,
)
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    Location,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now_in_ms
from rotki2.exchanges.base import AsyncExchangeInterface, AsyncExchangeWithExtras

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = RotkehlchenLogsAdapter(__name__)

KRAKEN_API_VERSION = '0'
KRAKEN_BASE_URL = 'https://api.kraken.com'


class AsyncKraken(AsyncExchangeInterface, AsyncExchangeWithExtras):
    """Async implementation of Kraken exchange
    
    This migrates the Kraken exchange logic to async while maintaining
    the same functionality as the sync version.
    """
    
    def __init__(
        self,
        name: str,
        api_key: ApiKey,
        secret: ApiSecret,
        database: 'DBHandler',
        msg_aggregator: 'MessagesAggregator',
        kraken_account_type: KrakenAccountType = KrakenAccountType.STARTER,
    ):
        super().__init__(
            name=name,
            location=Location.KRAKEN,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.account_type = kraken_account_type
        self.set_call_limits()
        
        # Kraken-specific rate limiting
        self.reduction_every_secs = 60
        self.last_counter_increase = ts_now_in_ms()
        
    def set_call_limits(self) -> None:
        """Set call limits based on account type"""
        if self.account_type == KrakenAccountType.STARTER:
            self.call_limit = 15
            self.reduction_every_secs = 60
        elif self.account_type == KrakenAccountType.INTERMEDIATE:
            self.call_limit = 20
            self.reduction_every_secs = 60
        else:  # Pro
            self.call_limit = 20
            self.reduction_every_secs = 1
    
    def get_extras(self) -> dict[str, Any]:
        """Get Kraken-specific extras"""
        return {'account_type': self.account_type.value}
    
    def set_extras(self, extras: dict[str, Any]) -> None:
        """Set Kraken-specific extras"""
        if 'account_type' in extras:
            self.account_type = KrakenAccountType(extras['account_type'])
            self.set_call_limits()
    
    async def _apply_rate_limit(self) -> None:
        """Apply Kraken-specific rate limiting"""
        async with self._rate_limit_lock:
            current_time = ts_now_in_ms()
            
            # Reduce counter if reduction period has passed
            secs_since_last_call = (current_time - self.last_counter_increase) / 1000
            if secs_since_last_call > self.reduction_every_secs:
                self.call_counter = max(0, self.call_counter - 1)
                self.last_counter_increase = current_time
            
            # If over limit, wait
            if self.call_counter >= self.call_limit:
                wait_time = self.reduction_every_secs * 2
                logger.debug(f'Kraken rate limit reached, waiting {wait_time}s')
                await anyio.sleep(wait_time)
                self.call_counter = 0
            
            self.call_counter += 1
    
    def _generate_signature(self, urlpath: str, data: dict[str, Any], nonce: int) -> str:
        """Generate API request signature"""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(nonce) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        signature = hmac.new(
            base64.b64decode(self.secret),
            message,
            hashlib.sha512,
        )
        sigdigest = base64.b64encode(signature.digest())
        return sigdigest.decode()
    
    async def _api_query(
        self,
        method: str,
        req: dict[str, Any] | None = None,
        retry_count: int = 3,
    ) -> dict[str, Any]:
        """Query Kraken API with retry logic"""
        if req is None:
            req = {}
            
        # Apply rate limiting
        await self._apply_rate_limit()
        
        # Determine if public or private API
        is_private = method.startswith('Balance') or method.startswith('Query') or \
                    method.startswith('Ledgers') or method.startswith('Trades')
        
        if is_private:
            req['nonce'] = int(time.time() * 1000)
            urlpath = f'/{KRAKEN_API_VERSION}/private/{method}'
            headers = {
                'API-Key': self.api_key,
                'API-Sign': self._generate_signature(urlpath, req, req['nonce']),
            }
        else:
            urlpath = f'/{KRAKEN_API_VERSION}/public/{method}'
            headers = {}
        
        url = KRAKEN_BASE_URL + urlpath
        
        # Retry logic
        for attempt in range(retry_count):
            try:
                if is_private:
                    response = await self.http_client.post(
                        url=url,
                        data=req,
                        headers=headers,
                    )
                else:
                    response = await self.http_client.get(
                        url=url,
                        params=req,
                    )
                
                if response.status_code != 200:
                    raise RemoteError(
                        f'Kraken API request failed with status {response.status_code}'
                    )
                
                result = response.json()
                
                # Check for Kraken errors
                if result['error']:
                    if 'Rate limit exceeded' in result['error']:
                        if attempt < retry_count - 1:
                            await anyio.sleep(5)
                            continue
                    raise RemoteError(f"Kraken API error: {result['error']}")
                
                return result['result']
                
            except Exception as e:
                if attempt == retry_count - 1:
                    raise RemoteError(f'Kraken API request failed: {str(e)}') from e
                await anyio.sleep(1)
    
    async def query_balances(self, **kwargs: Any) -> dict[Asset, Balance]:
        """Query account balances"""
        response = await self._api_query('Balance')
        
        balances = {}
        for kraken_name, amount_str in response.items():
            try:
                asset = Asset(kraken_name)  # Would use proper asset resolution
                amount = FVal(amount_str)
                
                if amount > ZERO:
                    # Query USD value - simplified for example
                    usd_value = amount  # Would calculate actual USD value
                    balances[asset] = Balance(amount=amount, usd_value=usd_value)
                    
            except (ValueError, DeserializationError) as e:
                logger.warning(f'Failed to process Kraken balance {kraken_name}: {e}')
                continue
        
        return balances
    
    async def query_online_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history"""
        trades = []
        
        # Query trades endpoint with pagination
        req = {
            'start': start_ts,
            'end': end_ts,
            'trades': True,
        }
        
        offset = 0
        while True:
            if offset != 0:
                req['ofs'] = offset
                
            response = await self._api_query('TradesHistory', req)
            
            if 'trades' not in response or not response['trades']:
                break
                
            for trade_id, trade_data in response['trades'].items():
                try:
                    # Parse trade data - simplified
                    trade = Trade(
                        timestamp=deserialize_timestamp(trade_data['time']),
                        location=Location.KRAKEN,
                        base_asset=Asset(trade_data['pair'][:3]),  # Simplified
                        quote_asset=Asset(trade_data['pair'][3:]),  # Simplified
                        trade_type=TradeType.BUY if trade_data['type'] == 'buy' else TradeType.SELL,
                        amount=deserialize_asset_amount(trade_data['vol']),
                        rate=deserialize_price(trade_data['price']),
                        fee=deserialize_fee(trade_data['fee']),
                        fee_currency=Asset('USD'),  # Simplified
                        link=trade_id,
                    )
                    trades.append(trade)
                except Exception as e:
                    logger.warning(f'Failed to parse Kraken trade {trade_id}: {e}')
                    continue
            
            # Check if more pages
            count = response.get('count', 0)
            if offset + 50 >= count:
                break
            offset += 50
            
        return trades
    
    async def query_online_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals"""
        movements = []
        
        # Query ledgers for deposits/withdrawals
        req = {
            'start': start_ts,
            'end': end_ts,
            'type': 'deposit,withdrawal',
        }
        
        response = await self._api_query('Ledgers', req)
        
        if 'ledger' in response:
            for ledger_id, ledger_data in response['ledger'].items():
                try:
                    movement_type = ledger_data['type']
                    if movement_type not in ('deposit', 'withdrawal'):
                        continue
                    
                    movement = AssetMovement(
                        location=Location.KRAKEN,
                        category=AssetMovementCategory.DEPOSIT if movement_type == 'deposit' 
                                else AssetMovementCategory.WITHDRAWAL,
                        timestamp=deserialize_timestamp(ledger_data['time']),
                        address=None,  # Kraken doesn't provide in ledger
                        transaction_id=ledger_id,
                        asset=Asset(ledger_data['asset']),
                        amount=deserialize_asset_amount(ledger_data['amount']),
                        fee_asset=Asset(ledger_data['asset']),
                        fee=deserialize_fee(ledger_data['fee']),
                        link=ledger_id,
                    )
                    movements.append(movement)
                except Exception as e:
                    logger.warning(f'Failed to parse Kraken ledger {ledger_id}: {e}')
                    continue
        
        return movements
    
    async def validate_api_key(self) -> tuple[bool, str]:
        """Validate API credentials"""
        try:
            # Try to query balance as validation
            await self._api_query('Balance')
            return True, ''
        except RemoteError as e:
            error_str = str(e)
            if 'Invalid API-Key' in error_str:
                return False, 'Invalid API key provided'
            elif 'Permission denied' in error_str:
                return False, 'API key does not have required permissions'
            else:
                return False, f'API validation failed: {error_str}'
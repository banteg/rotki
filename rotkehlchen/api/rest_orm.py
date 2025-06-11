"""REST API implementation using ORM - partial example"""

import logging
from http import HTTPStatus
from pathlib import Path
from typing import Any, TYPE_CHECKING

from flask import Response

from rotkehlchen.api.v1.types import Response as APIResponse
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.orm.database import RotkehlchenDatabase
    from rotkehlchen.rotkehlchen_orm import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RestAPI:
    """REST API implementation using ORM database layer"""
    
    def __init__(self, rotkehlchen: 'Rotkehlchen') -> None:
        self.rotkehlchen = rotkehlchen
        
    def _get_db(self) -> 'RotkehlchenDatabase':
        """Get the ORM database instance"""
        if not self.rotkehlchen.user_is_logged_in:
            raise RuntimeError("User not logged in")
        return self.rotkehlchen.data.db
    
    def get_settings(self) -> Response:
        """Get application settings using ORM"""
        db = self._get_db()
        
        # Get all settings using repository
        settings_dict = db.repos.settings.get_all_settings()
        
        # Get cache data
        cache_data = {}
        cache_entries = db.repos.cache.get_all_cache()
        for entry in cache_entries:
            cache_data[entry.key] = {
                'value': entry.value,
                'last_queried_ts': entry.last_queried_ts,
            }
        
        # Combine settings and cache
        result = {**settings_dict, 'cache': cache_data}
        
        return self._make_api_response(result, HTTPStatus.OK)
    
    def set_settings(self, settings: ModifiableDBSettings) -> Response:
        """Update settings using ORM"""
        db = self._get_db()
        
        try:
            # Update settings using repository with transaction
            with db.repos.unit_of_work():
                settings_dict = settings.serialize_for_db()
                for key, value in settings_dict.items():
                    db.repos.settings.set_setting(key, value)
            
            return self._make_api_response({'result': True}, HTTPStatus.OK)
            
        except Exception as e:
            return self._make_error_response(str(e), HTTPStatus.CONFLICT)
    
    def get_exchanges(self) -> Response:
        """Get configured exchanges using ORM"""
        db = self._get_db()
        
        # Get all exchange credentials
        all_credentials = db.repos.credentials.get_all_credentials()
        
        exchanges = []
        for cred in all_credentials:
            exchanges.append({
                'location': cred.location,
                'name': cred.name,
                'kraken_account_type': cred.kraken_account_type,
            })
        
        return self._make_api_response(exchanges, HTTPStatus.OK)
    
    def setup_exchange(
            self,
            name: str,
            location: Location,
            api_key: str,
            api_secret: str | None,
            passphrase: str | None,
            kraken_account_type: str | None,
            binance_markets: list[str] | None,
    ) -> Response:
        """Setup a new exchange using ORM"""
        db = self._get_db()
        
        try:
            # Check if exchange already exists
            existing = db.repos.credentials.get_credential(name, location)
            if existing:
                return self._make_error_response(
                    f"Exchange {name} at {location} already exists",
                    HTTPStatus.CONFLICT,
                )
            
            # Add exchange credential
            with db.repos.unit_of_work():
                db.repos.credentials.add_credential(
                    name=name,
                    location=location.serialize_for_db(),
                    api_key=api_key,
                    api_secret=api_secret,
                    passphrase=passphrase,
                    kraken_account_type=kraken_account_type,
                )
                
                # TODO: Initialize exchange in exchange manager
                # TODO: This would need to be updated to work with ORM
                # self.rotkehlchen.exchange_manager.setup_exchange(...)
            
            return self._make_api_response({'result': True}, HTTPStatus.OK)
            
        except Exception as e:
            return self._make_error_response(str(e), HTTPStatus.BAD_REQUEST)
    
    def remove_exchange(self, name: str, location: Location) -> Response:
        """Remove an exchange using ORM"""
        db = self._get_db()
        
        try:
            with db.repos.unit_of_work():
                success = db.repos.credentials.delete_credential(name, location)
                if not success:
                    return self._make_error_response(
                        f"Exchange {name} at {location} not found",
                        HTTPStatus.NOT_FOUND,
                    )
                
                # TODO: Remove from exchange manager
                # TODO: self.rotkehlchen.exchange_manager.delete_exchange(name, location)
            
            return self._make_api_response({'result': True}, HTTPStatus.OK)
            
        except Exception as e:
            return self._make_error_response(str(e), HTTPStatus.BAD_REQUEST)
    
    def get_blockchain_accounts(self) -> Response:
        """Get blockchain accounts using ORM"""
        db = self._get_db()
        
        # Get all accounts grouped by blockchain
        accounts_by_blockchain = {}
        all_accounts = db.repos.accounts.get_all_accounts()
        
        for account in all_accounts:
            blockchain = account.blockchain
            if blockchain not in accounts_by_blockchain:
                accounts_by_blockchain[blockchain] = []
            
            accounts_by_blockchain[blockchain].append({
                'address': account.account,
                'label': account.label,
                'tags': db.repos.accounts.get_account_tags(account.account, blockchain),
            })
        
        return self._make_api_response(accounts_by_blockchain, HTTPStatus.OK)
    
    def add_blockchain_accounts(
            self,
            blockchain: str,
            accounts: list[dict[str, Any]],
    ) -> Response:
        """Add blockchain accounts using ORM"""
        db = self._get_db()
        
        try:
            with db.repos.unit_of_work():
                for account_data in accounts:
                    address = account_data['address']
                    label = account_data.get('label')
                    tags = account_data.get('tags', [])
                    
                    # Add account
                    db.repos.accounts.add_account(
                        blockchain=blockchain,
                        address=address,
                        label=label,
                    )
                    
                    # Add tags if any
                    for tag in tags:
                        db.repos.tags.add_tag_mapping(tag, address, blockchain)
            
            return self._make_api_response({'result': True}, HTTPStatus.OK)
            
        except Exception as e:
            return self._make_error_response(str(e), HTTPStatus.BAD_REQUEST)
    
    def remove_blockchain_accounts(
            self,
            blockchain: str,
            accounts: list[str],
    ) -> Response:
        """Remove blockchain accounts using ORM"""
        db = self._get_db()
        
        try:
            with db.repos.unit_of_work():
                for address in accounts:
                    success = db.repos.accounts.delete_account(blockchain, address)
                    if not success:
                        return self._make_error_response(
                            f"Account {address} not found on {blockchain}",
                            HTTPStatus.NOT_FOUND,
                        )
            
            return self._make_api_response({'result': True}, HTTPStatus.OK)
            
        except Exception as e:
            return self._make_error_response(str(e), HTTPStatus.BAD_REQUEST)
    
    def get_tags(self) -> Response:
        """Get all tags using ORM"""
        db = self._get_db()
        
        tags = []
        all_tags = db.repos.tags.get_all_tags()
        
        for tag in all_tags:
            tags.append({
                'name': tag.name,
                'description': tag.description,
                'background_color': tag.background_color,
                'foreground_color': tag.foreground_color,
            })
        
        return self._make_api_response(tags, HTTPStatus.OK)
    
    def add_tag(
            self,
            name: str,
            description: str,
            background_color: str,
            foreground_color: str,
    ) -> Response:
        """Add a new tag using ORM"""
        db = self._get_db()
        
        try:
            with db.repos.unit_of_work():
                db.repos.tags.add_tag(
                    name=name,
                    description=description,
                    background_color=background_color,
                    foreground_color=foreground_color,
                )
            
            return self._make_api_response({'result': True}, HTTPStatus.OK)
            
        except Exception as e:
            return self._make_error_response(str(e), HTTPStatus.CONFLICT)
    
    def edit_tag(
            self,
            name: str,
            description: str | None = None,
            background_color: str | None = None,
            foreground_color: str | None = None,
    ) -> Response:
        """Edit an existing tag using ORM"""
        db = self._get_db()
        
        try:
            with db.repos.unit_of_work():
                updated = db.repos.tags.update_tag(
                    name=name,
                    description=description,
                    background_color=background_color,
                    foreground_color=foreground_color,
                )
                
                if not updated:
                    return self._make_error_response(
                        f"Tag {name} not found",
                        HTTPStatus.NOT_FOUND,
                    )
            
            return self._make_api_response({'result': True}, HTTPStatus.OK)
            
        except Exception as e:
            return self._make_error_response(str(e), HTTPStatus.BAD_REQUEST)
    
    def delete_tag(self, name: str) -> Response:
        """Delete a tag using ORM"""
        db = self._get_db()
        
        try:
            with db.repos.unit_of_work():
                success = db.repos.tags.delete_tag(name)
                if not success:
                    return self._make_error_response(
                        f"Tag {name} not found",
                        HTTPStatus.NOT_FOUND,
                    )
            
            return self._make_api_response({'result': True}, HTTPStatus.OK)
            
        except Exception as e:
            return self._make_error_response(str(e), HTTPStatus.BAD_REQUEST)
    
    def get_manual_balances(self) -> Response:
        """Get manual balances using ORM"""
        db = self._get_db()
        
        balances = []
        all_balances = db.repos.manual_balances.get_all_balances()
        
        for balance in all_balances:
            balances.append({
                'id': balance.identifier,
                'asset': balance.asset,
                'label': balance.label,
                'amount': balance.amount,
                'location': balance.location,
                'tags': db.repos.manual_balances.get_balance_tags(balance.identifier),
            })
        
        return self._make_api_response(balances, HTTPStatus.OK)
    
    def add_manual_balance(
            self,
            asset: str,
            label: str,
            amount: str,
            location: str,
            tags: list[str] | None = None,
    ) -> Response:
        """Add manual balance using ORM"""
        db = self._get_db()
        
        try:
            with db.repos.unit_of_work():
                balance = db.repos.manual_balances.add_balance(
                    asset=asset,
                    label=label,
                    amount=amount,
                    location=location,
                    tags=tags or [],
                )
            
            return self._make_api_response({'id': balance.identifier}, HTTPStatus.OK)
            
        except Exception as e:
            return self._make_error_response(str(e), HTTPStatus.BAD_REQUEST)
    
    def _make_api_response(self, result: Any, status_code: HTTPStatus) -> Response:
        """Create API response"""
        return APIResponse(
            result={'result': result, 'message': ''},
            status_code=status_code,
        )
    
    def _make_error_response(self, message: str, status_code: HTTPStatus) -> Response:
        """Create error response"""
        return APIResponse(
            result={'result': None, 'message': message},
            status_code=status_code,
        )
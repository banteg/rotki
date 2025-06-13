"""Repository for exchange-related database operations"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete

from rotkehlchen.types import ApiKey, ApiSecret, Location
from rotki2.db.models.exchanges import (
    ExchangeCachedData,
    ExchangeCredentials,
    ExchangeExtras,
    ExchangeTradePairs,
    UserExchangePairs,
)


class ExchangeRepository:
    """Repository for exchange data operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add_exchange_credentials(
        self,
        name: str,
        location: Location,
        api_key: ApiKey,
        api_secret: ApiSecret | None = None,
        passphrase: str | None = None,
    ) -> ExchangeCredentials:
        """Add exchange credentials to database"""
        credentials = ExchangeCredentials(
            name=name,
            location=location.value,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )
        
        self.session.add(credentials)
        await self.session.commit()
        await self.session.refresh(credentials)
        
        return credentials
    
    async def get_exchange_credentials(
        self,
        name: str | None = None,
        location: Location | None = None,
    ) -> list[ExchangeCredentials]:
        """Get exchange credentials from database"""
        query = select(ExchangeCredentials)
        
        if name:
            query = query.where(ExchangeCredentials.name == name)
        if location:
            query = query.where(ExchangeCredentials.location == location.value)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_exchange_credentials(
        self,
        name: str,
        location: Location,
        api_key: ApiKey | None = None,
        api_secret: ApiSecret | None = None,
        passphrase: str | None = None,
        new_name: str | None = None,
    ) -> bool:
        """Update exchange credentials"""
        query = select(ExchangeCredentials).where(
            ExchangeCredentials.name == name,
            ExchangeCredentials.location == location.value,
        )
        
        result = await self.session.execute(query)
        credentials = result.scalar_one_or_none()
        
        if not credentials:
            return False
        
        if api_key is not None:
            credentials.api_key = api_key
        if api_secret is not None:
            credentials.api_secret = api_secret
        if passphrase is not None:
            credentials.passphrase = passphrase
        if new_name is not None:
            credentials.name = new_name
        
        await self.session.commit()
        return True
    
    async def delete_exchange_credentials(
        self,
        name: str,
        location: Location,
    ) -> bool:
        """Delete exchange credentials"""
        query = delete(ExchangeCredentials).where(
            ExchangeCredentials.name == name,
            ExchangeCredentials.location == location.value,
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount > 0
    
    async def set_exchange_extras(
        self,
        name: str,
        location: Location,
        extras: dict[str, Any],
    ) -> ExchangeExtras:
        """Set exchange-specific extras"""
        # Check if extras already exist
        query = select(ExchangeExtras).where(
            ExchangeExtras.exchange_name == name,
            ExchangeExtras.exchange_location == location.value,
        )
        
        result = await self.session.execute(query)
        exchange_extras = result.scalar_one_or_none()
        
        if exchange_extras:
            # Update existing
            exchange_extras.extras = extras
        else:
            # Create new
            exchange_extras = ExchangeExtras(
                exchange_name=name,
                exchange_location=location.value,
                extras=extras,
            )
            self.session.add(exchange_extras)
        
        await self.session.commit()
        await self.session.refresh(exchange_extras)
        
        return exchange_extras
    
    async def get_exchange_extras(
        self,
        name: str,
        location: Location,
    ) -> dict[str, Any] | None:
        """Get exchange-specific extras"""
        query = select(ExchangeExtras).where(
            ExchangeExtras.exchange_name == name,
            ExchangeExtras.exchange_location == location.value,
        )
        
        result = await self.session.execute(query)
        exchange_extras = result.scalar_one_or_none()
        
        return exchange_extras.extras if exchange_extras else None
    
    async def cache_exchange_data(
        self,
        name: str,
        location: Location,
        data_type: str,
        data: dict[str, Any],
        timestamp: int,
    ) -> ExchangeCachedData:
        """Cache exchange data"""
        # Delete old cache for this type
        delete_query = delete(ExchangeCachedData).where(
            ExchangeCachedData.exchange_name == name,
            ExchangeCachedData.exchange_location == location.value,
            ExchangeCachedData.data_type == data_type,
        )
        await self.session.execute(delete_query)
        
        # Insert new cache
        cached_data = ExchangeCachedData(
            exchange_name=name,
            exchange_location=location.value,
            data_type=data_type,
            timestamp=timestamp,
            data=data,
        )
        
        self.session.add(cached_data)
        await self.session.commit()
        await self.session.refresh(cached_data)
        
        return cached_data
    
    async def get_cached_exchange_data(
        self,
        name: str,
        location: Location,
        data_type: str,
    ) -> ExchangeCachedData | None:
        """Get cached exchange data"""
        query = select(ExchangeCachedData).where(
            ExchangeCachedData.exchange_name == name,
            ExchangeCachedData.exchange_location == location.value,
            ExchangeCachedData.data_type == data_type,
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def purge_exchange_cache(
        self,
        name: str | None = None,
        location: Location | None = None,
    ) -> int:
        """Purge cached exchange data"""
        query = delete(ExchangeCachedData)
        
        if name:
            query = query.where(ExchangeCachedData.exchange_name == name)
        if location:
            query = query.where(ExchangeCachedData.exchange_location == location.value)
        
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount
    
    async def update_trade_pairs(
        self,
        location: Location,
        pairs: list[dict[str, Any]],
        timestamp: int,
    ) -> None:
        """Update available trading pairs for an exchange"""
        # Delete old pairs
        delete_query = delete(ExchangeTradePairs).where(
            ExchangeTradePairs.exchange_location == location.value
        )
        await self.session.execute(delete_query)
        
        # Insert new pairs
        for pair_data in pairs:
            pair = ExchangeTradePairs(
                exchange_location=location.value,
                pair=pair_data['pair'],
                base_asset=pair_data['base_asset'],
                quote_asset=pair_data['quote_asset'],
                active=pair_data.get('active', True),
                min_trade_size=pair_data.get('min_trade_size'),
                timestamp=timestamp,
            )
            self.session.add(pair)
        
        await self.session.commit()
    
    async def get_trade_pairs(
        self,
        location: Location,
        active_only: bool = True,
    ) -> list[ExchangeTradePairs]:
        """Get available trading pairs for an exchange"""
        query = select(ExchangeTradePairs).where(
            ExchangeTradePairs.exchange_location == location.value
        )
        
        if active_only:
            query = query.where(ExchangeTradePairs.active == True)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def set_user_pairs(
        self,
        name: str,
        location: Location,
        pairs: list[str],
    ) -> None:
        """Set user-selected trading pairs"""
        # Delete old selections
        delete_query = delete(UserExchangePairs).where(
            UserExchangePairs.exchange_name == name,
            UserExchangePairs.exchange_location == location.value,
        )
        await self.session.execute(delete_query)
        
        # Insert new selections
        for pair in pairs:
            user_pair = UserExchangePairs(
                exchange_name=name,
                exchange_location=location.value,
                pair=pair,
                enabled=True,
            )
            self.session.add(user_pair)
        
        await self.session.commit()
    
    async def get_user_pairs(
        self,
        name: str,
        location: Location,
    ) -> list[str]:
        """Get user-selected trading pairs"""
        query = select(UserExchangePairs).where(
            UserExchangePairs.exchange_name == name,
            UserExchangePairs.exchange_location == location.value,
            UserExchangePairs.enabled == True,
        )
        
        result = await self.session.execute(query)
        pairs = result.scalars().all()
        
        return [p.pair for p in pairs]
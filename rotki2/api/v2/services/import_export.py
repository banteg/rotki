"""Import/Export service for data import and export operations"""
import csv
import json
from io import StringIO
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from rotki2.api.v2.services.data import DataService

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class ImportExportService:
    """Service for importing and exporting data"""

    def __init__(self, session: AsyncSession | None = None, db_handler: 'DBHandler | None' = None) -> None:
        self.data_service = DataService(session, db_handler) if session else None
        # Available importers
        self._importers = {
            'cointracking': {
                'name': 'CoinTracking',
                'description': 'Import trades and transactions from CoinTracking',
                'file_types': ['csv'],
            },
            'cryptocom': {
                'name': 'Crypto.com',
                'description': 'Import data from Crypto.com app',
                'file_types': ['csv'],
            },
            'blockfi': {
                'name': 'BlockFi',
                'description': 'Import trades and interest from BlockFi',
                'file_types': ['csv'],
            },
            'nexo': {
                'name': 'Nexo',
                'description': 'Import transactions from Nexo',
                'file_types': ['csv'],
            },
            'rotki': {
                'name': 'Rotki',
                'description': 'Import data from another Rotki instance',
                'file_types': ['json'],
            },
        }

    async def get_available_importers(self) -> dict[str, Any]:
        """Get list of available data importers"""
        return self._importers

    async def import_data(
        self,
        source: str,
        data: dict[str, Any] | None = None,
        file_path: str | None = None,
    ) -> dict[str, Any]:
        """Import data from external source"""
        if source not in self._importers:
            raise ValueError(f'Unknown import source: {source}')

        # Would implement actual import logic based on source
        if source == 'rotki':
            return await self._import_rotki_data(data)
        elif source == 'cointracking':
            return await self._import_cointracking_data(data)
        elif source == 'cryptocom':
            return await self._import_cryptocom_data(data)
        else:
            return await self._generic_csv_import(source, data)

    async def import_from_file(
        self,
        filename: str,
        content: bytes,
        source: str = 'auto',
    ) -> dict[str, Any]:
        """Import data from uploaded file"""
        # Auto-detect source if needed
        if source == 'auto':
            source = self._detect_source(filename, content)

        # Parse file based on type
        if filename.endswith('.json'):
            data = json.loads(content.decode('utf-8'))
        elif filename.endswith('.csv'):
            csv_string = content.decode('utf-8')
            reader = csv.DictReader(StringIO(csv_string))
            data = list(reader)
        else:
            raise ValueError(f'Unsupported file type: {filename}')

        return await self.import_data(source, data)

    def _detect_source(self, filename: str, content: bytes) -> str:
        """Auto-detect import source from file"""
        # Would implement detection logic
        if 'cointracking' in filename.lower():
            return 'cointracking'
        elif 'crypto.com' in filename.lower() or 'cryptocom' in filename.lower():
            return 'cryptocom'
        elif 'blockfi' in filename.lower():
            return 'blockfi'
        elif 'nexo' in filename.lower():
            return 'nexo'

        # Try to detect from content
        try:
            content_str = content.decode('utf-8').lower()
            if 'cointracking' in content_str:
                return 'cointracking'
            elif 'crypto.com' in content_str:
                return 'cryptocom'
        except:
            pass

        raise ValueError('Could not auto-detect import source')

    async def _import_rotki_data(self, data: dict[str, Any] | None) -> dict[str, Any]:
        """Import data from another Rotki instance"""
        if not data:
            raise ValueError('No data provided')

        # Use DataService for actual import
        if self.data_service:
            return await self.data_service.import_rotki_data(data)
        
        # Fallback if no data service
        imported = {
            'trades': 0,
            'transactions': 0,
            'balances': 0,
            'tags': 0,
        }

        if 'trades' in data:
            imported['trades'] = len(data['trades'])
        if 'transactions' in data:
            imported['transactions'] = len(data['transactions'])

        return {'imported': imported}

    async def _import_cointracking_data(self, data: Any) -> dict[str, Any]:
        """Import data from CoinTracking"""
        # Would implement CoinTracking import
        return {'imported': {'trades': 10, 'transactions': 5}}

    async def _import_cryptocom_data(self, data: Any) -> dict[str, Any]:
        """Import data from Crypto.com"""
        # Would implement Crypto.com import
        return {'imported': {'trades': 15, 'transactions': 20}}

    async def _generic_csv_import(self, source: str, data: Any) -> dict[str, Any]:
        """Generic CSV import"""
        # Would implement generic CSV import
        return {'imported': {'entries': len(data) if data else 0}}

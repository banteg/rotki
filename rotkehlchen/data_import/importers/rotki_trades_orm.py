"""Rotki generic trades importer using ORM"""

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import AssetAmount, Fee, Location, Price, Timestamp, TradeID, TradeType

if TYPE_CHECKING:
    from rotkehlchen.db.orm.database import RotkehlchenDatabase

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkiGenericTradesImporter(BaseExchangeImporter):
    """Imports Rotki generic trades from CSV using ORM"""

    def __init__(self, db: 'RotkehlchenDatabase') -> None:
        self.db = db

    def _consume_rotki_trade(
            self,
            csv_row: dict[str, str],
    ) -> None:
        """Process a CSV row and add it as a trade using ORM"""
        try:
            # Parse required fields
            timestamp = Timestamp(int(csv_row['timestamp']))
            location = Location.deserialize(csv_row['location'])
            base_asset = Asset(csv_row['base_asset'])
            quote_asset = Asset(csv_row['quote_asset'])
            trade_type = TradeType.deserialize(csv_row['trade_type'])
            amount = AssetAmount(FVal(csv_row['amount']))
            rate = Price(FVal(csv_row['rate']))
            
            # Parse optional fields
            fee = Fee(FVal(csv_row.get('fee', '0')))
            fee_currency = Asset(csv_row.get('fee_currency', 'USD')) if csv_row.get('fee_currency') else A_USD
            link = csv_row.get('link', '')
            notes = csv_row.get('notes', '')
            
            # Create trade using ORM
            with self.db.repos.unit_of_work():
                self.db.repos.trades.add_trade(
                    timestamp=timestamp,
                    location=location.serialize_for_db(),
                    base_asset=base_asset.identifier,
                    quote_asset=quote_asset.identifier,
                    trade_type=trade_type.serialize(),
                    amount=str(amount),
                    rate=str(rate),
                    fee=str(fee) if fee else None,
                    fee_currency=fee_currency.identifier if fee else None,
                    link=link,
                    notes=notes,
                )
                
        except UnknownAsset as e:
            self.db.msg_aggregator.add_warning(
                f'During Rotki trades CSV import, found trade with unknown '
                f'asset {e.identifier}. Ignoring trade.',
            )
        except KeyError as e:
            raise UnsupportedCSVEntry(f'Missing required field: {e}') from e
        except (ValueError, InputError) as e:
            raise UnsupportedCSVEntry(f'Invalid value in CSV: {e}') from e

    def import_csv(self, filepath: Path, **kwargs: Any) -> tuple[bool, str]:
        """Import Rotki trades from CSV file using ORM"""
        try:
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Validate headers
                if reader.fieldnames is None:
                    return False, 'CSV file is empty or has no headers'
                
                required_fields = {
                    'timestamp', 'location', 'base_asset', 'quote_asset',
                    'trade_type', 'amount', 'rate'
                }
                if not required_fields.issubset(set(reader.fieldnames)):
                    missing = required_fields - set(reader.fieldnames)
                    return False, f'CSV file is missing required fields: {missing}'
                
                # Process each row
                imported_count = 0
                for idx, row in enumerate(reader):
                    try:
                        self._consume_rotki_trade(row)
                        imported_count += 1
                    except UnsupportedCSVEntry as e:
                        log.warning(f'Skipping row {idx + 1}: {e}')
                        continue
                
                return True, f'Successfully imported {imported_count} trades'
                
        except FileNotFoundError:
            return False, f'File {filepath} not found'
        except PermissionError:
            return False, f'Permission denied reading file {filepath}'
        except Exception as e:
            log.error(f'Unexpected error importing Rotki trades: {e}')
            return False, f'Failed to import file: {str(e)}'

    def get_import_preview(self, filepath: Path) -> dict[str, Any]:
        """Get a preview of what would be imported from the CSV file"""
        preview = {
            'total_rows': 0,
            'valid_rows': 0,
            'invalid_rows': 0,
            'sample_trades': [],
            'errors': [],
        }
        
        try:
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for idx, row in enumerate(reader):
                    preview['total_rows'] += 1
                    
                    try:
                        # Validate the row without importing
                        timestamp = Timestamp(int(row['timestamp']))
                        location = Location.deserialize(row['location'])
                        base_asset = Asset(row['base_asset'])
                        quote_asset = Asset(row['quote_asset'])
                        trade_type = TradeType.deserialize(row['trade_type'])
                        amount = FVal(row['amount'])
                        rate = FVal(row['rate'])
                        
                        preview['valid_rows'] += 1
                        
                        # Add first 5 valid rows as samples
                        if len(preview['sample_trades']) < 5:
                            preview['sample_trades'].append({
                                'timestamp': timestamp,
                                'location': location.serialize(),
                                'base_asset': base_asset.identifier,
                                'quote_asset': quote_asset.identifier,
                                'trade_type': trade_type.serialize(),
                                'amount': str(amount),
                                'rate': str(rate),
                            })
                            
                    except Exception as e:
                        preview['invalid_rows'] += 1
                        if len(preview['errors']) < 10:  # Limit error messages
                            preview['errors'].append(f'Row {idx + 1}: {str(e)}')
                
        except Exception as e:
            preview['errors'].append(f'Failed to read file: {str(e)}')
        
        return preview

    def validate_csv_format(self, filepath: Path) -> tuple[bool, str]:
        """Validate that the CSV file has the correct format for Rotki trades"""
        try:
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                if reader.fieldnames is None:
                    return False, 'CSV file is empty or has no headers'
                
                required_fields = {
                    'timestamp', 'location', 'base_asset', 'quote_asset',
                    'trade_type', 'amount', 'rate'
                }
                optional_fields = {'fee', 'fee_currency', 'link', 'notes'}
                all_valid_fields = required_fields | optional_fields
                
                # Check required fields
                missing = required_fields - set(reader.fieldnames)
                if missing:
                    return False, f'Missing required fields: {missing}'
                
                # Check for unknown fields
                unknown = set(reader.fieldnames) - all_valid_fields
                if unknown:
                    log.warning(f'CSV contains unknown fields that will be ignored: {unknown}')
                
                # Try to read first row to validate data format
                try:
                    first_row = next(reader)
                    Timestamp(int(first_row['timestamp']))
                    Location.deserialize(first_row['location'])
                    TradeType.deserialize(first_row['trade_type'])
                    FVal(first_row['amount'])
                    FVal(first_row['rate'])
                except StopIteration:
                    return False, 'CSV file has headers but no data'
                except Exception as e:
                    return False, f'Invalid data format in first row: {str(e)}'
                
                return True, 'CSV format is valid'
                
        except Exception as e:
            return False, f'Failed to validate CSV: {str(e)}'
"""Rotki generic events importer using ORM"""

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.orm.database import RotkehlchenDatabase

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkiGenericEventsImporter(BaseExchangeImporter):
    """Imports Rotki generic history events from CSV using ORM"""

    def __init__(self, db: 'RotkehlchenDatabase') -> None:
        self.db = db

    def _consume_rotki_event(
            self,
            csv_row: dict[str, str],
            sequence_index: int,
    ) -> None:
        """Process a CSV row and add it as a history event using ORM"""
        try:
            # Parse required fields
            event_identifier = csv_row.get('event_identifier', '')
            timestamp = Timestamp(int(csv_row['timestamp']))
            location = Location.deserialize(csv_row['location'])
            event_type = csv_row['event_type']
            event_subtype = csv_row.get('event_subtype', '')

            # Parse asset and amounts
            asset = Asset(csv_row['asset'])
            amount = FVal(csv_row.get('amount', '0'))
            usd_value = FVal(csv_row.get('usd_value', '0'))

            # Parse optional fields
            notes = csv_row.get('notes', '')
            location_label = csv_row.get('location_label', '')
            address = csv_row.get('address', '')
            transaction_hash = csv_row.get('transaction_hash', '')

            # Create history event using ORM
            with self.db.repos.unit_of_work():
                self.db.repos.history_events.add_event_from_dict({
                    'event_identifier': event_identifier,
                    'sequence_index': sequence_index,
                    'timestamp': timestamp,
                    'location': location.serialize_for_db(),
                    'event_type': event_type,
                    'event_subtype': event_subtype,
                    'asset': asset.identifier,
                    'amount': str(amount),
                    'usd_value': str(usd_value),
                    'notes': notes,
                    'location_label': location_label,
                    'address': address,
                    'transaction_hash': transaction_hash,
                })

        except UnknownAsset as e:
            self.db.msg_aggregator.add_warning(
                f'During Rotki events CSV import, found action with unknown '
                f'asset {e.identifier}. Ignoring entry.',
            )
        except KeyError as e:
            raise UnsupportedCSVEntry(f'Missing required field: {e}') from e
        except (ValueError, InputError) as e:
            raise UnsupportedCSVEntry(f'Invalid value in CSV: {e}') from e

    def import_csv(self, filepath: Path, **kwargs: Any) -> tuple[bool, str]:
        """Import Rotki events from CSV file using ORM"""
        try:
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                # Validate headers
                if reader.fieldnames is None:
                    return False, 'CSV file is empty or has no headers'

                required_fields = {'timestamp', 'location', 'event_type', 'asset'}
                if not required_fields.issubset(set(reader.fieldnames)):
                    missing = required_fields - set(reader.fieldnames)
                    return False, f'CSV file is missing required fields: {missing}'

                # Process each row
                imported_count = 0
                for idx, row in enumerate(reader):
                    try:
                        self._consume_rotki_event(row, idx)
                        imported_count += 1
                    except UnsupportedCSVEntry as e:
                        log.warning(f'Skipping row {idx + 1}: {e}')
                        continue

                return True, f'Successfully imported {imported_count} events'

        except FileNotFoundError:
            return False, f'File {filepath} not found'
        except PermissionError:
            return False, f'Permission denied reading file {filepath}'
        except Exception as e:
            log.error(f'Unexpected error importing Rotki events: {e}')
            return False, f'Failed to import file: {e!s}'

    def get_import_preview(self, filepath: Path) -> dict[str, Any]:
        """Get a preview of what would be imported from the CSV file"""
        preview = {
            'total_rows': 0,
            'valid_rows': 0,
            'invalid_rows': 0,
            'sample_events': [],
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
                        asset = Asset(row['asset'])

                        preview['valid_rows'] += 1

                        # Add first 5 valid rows as samples
                        if len(preview['sample_events']) < 5:
                            preview['sample_events'].append({
                                'timestamp': timestamp,
                                'location': location.serialize(),
                                'event_type': row.get('event_type', ''),
                                'asset': asset.identifier,
                                'amount': row.get('amount', '0'),
                            })

                    except Exception as e:
                        preview['invalid_rows'] += 1
                        if len(preview['errors']) < 10:  # Limit error messages
                            preview['errors'].append(f'Row {idx + 1}: {e!s}')

        except Exception as e:
            preview['errors'].append(f'Failed to read file: {e!s}')

        return preview

"""CSV data import manager using ORM"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.data_import.importers.rotki_events_orm import RotkiGenericEventsImporter
from rotkehlchen.data_import.importers.rotki_trades_orm import RotkiGenericTradesImporter
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

if TYPE_CHECKING:
    from rotkehlchen.data_import.utils import BaseExchangeImporter
    from rotkehlchen.db.orm.database import RotkehlchenDatabase


class DataImportSource(SerializableEnumNameMixin):
    COINTRACKING = 1
    CRYPTOCOM = 2
    BLOCKFI_TRANSACTIONS = 3
    BLOCKFI_TRADES = 4
    NEXO = 5
    SHAPESHIFT_TRADES = 6
    UPHOLD_TRANSACTIONS = 7
    BISQ_TRADES = 8
    BINANCE = 9
    ROTKI_TRADES = 10
    ROTKI_EVENTS = 11
    BITCOIN_TAX = 12
    BITMEX_WALLET_HISTORY = 13
    BITSTAMP = 14
    BITTREX = 15
    KUCOIN = 16
    BLOCKPIT = 17


class CSVDataImporter:
    """This class is responsible for importation of csv files using ORM."""

    def __init__(self, db: 'RotkehlchenDatabase'):
        self.db = db

    def import_csv(
            self,
            source: DataImportSource,
            filepath: Path,
            **kwargs: Any,
    ) -> tuple[bool, str]:
        """Imports csv data from `filepath`.`source` determines the format of the file.
        Returns (True, '') if imported successfully and (False, message) otherwise."""
        importer: BaseExchangeImporter

        # Create appropriate importer based on source
        # Note: Each importer needs to be updated to use ORM
        # For now, we'll implement the Rotki-specific importers
        if source == DataImportSource.COINTRACKING:
            # TODO: Update CointrackingImporter to use ORM
            return False, 'Cointracking importer needs ORM update'
        elif source == DataImportSource.CRYPTOCOM:
            # TODO: Update CryptocomImporter to use ORM
            return False, 'Crypto.com importer needs ORM update'
        elif source == DataImportSource.BLOCKFI_TRANSACTIONS:
            # TODO: Update BlockfiTransactionsImporter to use ORM
            return False, 'BlockFi transactions importer needs ORM update'
        elif source == DataImportSource.BLOCKFI_TRADES:
            # TODO: Update BlockfiTradesImporter to use ORM
            return False, 'BlockFi trades importer needs ORM update'
        elif source == DataImportSource.NEXO:
            # TODO: Update NexoImporter to use ORM
            return False, 'Nexo importer needs ORM update'
        elif source == DataImportSource.SHAPESHIFT_TRADES:
            # TODO: Update ShapeshiftTradesImporter to use ORM
            return False, 'ShapeShift trades importer needs ORM update'
        elif source == DataImportSource.UPHOLD_TRANSACTIONS:
            # TODO: Update UpholdTransactionsImporter to use ORM
            return False, 'Uphold transactions importer needs ORM update'
        elif source == DataImportSource.BISQ_TRADES:
            # TODO: Update BisqTradesImporter to use ORM
            return False, 'Bisq trades importer needs ORM update'
        elif source == DataImportSource.BINANCE:
            # TODO: Update BinanceImporter to use ORM
            return False, 'Binance importer needs ORM update'
        elif source == DataImportSource.ROTKI_TRADES:
            importer = RotkiGenericTradesImporter(db=self.db)
        elif source == DataImportSource.ROTKI_EVENTS:
            importer = RotkiGenericEventsImporter(db=self.db)
        elif source == DataImportSource.BITCOIN_TAX:
            # TODO: Update BitcoinTaxImporter to use ORM
            return False, 'Bitcoin Tax importer needs ORM update'
        elif source == DataImportSource.BITMEX_WALLET_HISTORY:
            # TODO: Update BitMEXImporter to use ORM
            return False, 'BitMEX importer needs ORM update'
        elif source == DataImportSource.BITSTAMP:
            # TODO: Update BitstampTransactionsImporter to use ORM
            return False, 'Bitstamp importer needs ORM update'
        elif source == DataImportSource.BITTREX:
            # TODO: Update BittrexImporter to use ORM
            return False, 'Bittrex importer needs ORM update'
        elif source == DataImportSource.KUCOIN:
            # TODO: Update KucoinImporter to use ORM
            return False, 'KuCoin importer needs ORM update'
        elif source == DataImportSource.BLOCKPIT:
            # TODO: Update BlockpitImporter to use ORM
            return False, 'Blockpit importer needs ORM update'
        else:
            raise AssertionError(f'Unknown DataImportSource value {source}')

        success, msg = importer.import_csv(filepath=filepath, **kwargs)
        return success, msg

    def get_import_summary(self) -> dict[str, Any]:
        """Get summary of imported data using ORM"""
        return {
            'trades': self.db.repos.trades.count_all_trades(),
            'history_events': self.db.repos.history_events.count_all_events(),
            'manual_balances': len(self.db.repos.manual_balances.get_all_balances()),
            'tags': len(self.db.repos.tags.get_all_tags()),
        }

    def export_data(
            self,
            directory: Path,
            from_timestamp: int | None = None,
            to_timestamp: int | None = None,
    ) -> tuple[bool, str]:
        """Export user data to CSV files using ORM"""
        try:
            # Create export directory if it doesn't exist
            directory.mkdir(parents=True, exist_ok=True)

            # Export trades
            trades_file = directory / 'rotki_trades.csv'
            self._export_trades_to_csv(trades_file, from_timestamp, to_timestamp)

            # Export history events
            events_file = directory / 'rotki_events.csv'
            self._export_events_to_csv(events_file, from_timestamp, to_timestamp)

            # Export manual balances
            balances_file = directory / 'rotki_manual_balances.csv'
            self._export_manual_balances_to_csv(balances_file)

            # Export tags
            tags_file = directory / 'rotki_tags.csv'
            self._export_tags_to_csv(tags_file)

            return True, f'Data exported successfully to {directory}'

        except Exception as e:
            return False, f'Failed to export data: {e!s}'

    def _export_trades_to_csv(
            self,
            filepath: Path,
            from_timestamp: int | None = None,
            to_timestamp: int | None = None,
    ) -> None:
        """Export trades to CSV using ORM"""
        import csv

        trades = self.db.repos.trades.get_trades(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'location', 'base_asset', 'quote_asset',
                'trade_type', 'amount', 'rate', 'fee', 'fee_currency',
                'link', 'notes',
            ])
            writer.writeheader()

            for trade in trades:
                writer.writerow({
                    'timestamp': trade.timestamp,
                    'location': trade.location,
                    'base_asset': trade.base_asset,
                    'quote_asset': trade.quote_asset,
                    'trade_type': trade.trade_type,
                    'amount': trade.amount,
                    'rate': trade.rate,
                    'fee': trade.fee,
                    'fee_currency': trade.fee_currency,
                    'link': trade.link,
                    'notes': trade.notes,
                })

    def _export_events_to_csv(
            self,
            filepath: Path,
            from_timestamp: int | None = None,
            to_timestamp: int | None = None,
    ) -> None:
        """Export history events to CSV using ORM"""
        import csv

        events = self.db.repos.history_events.get_events(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'event_identifier', 'sequence_index', 'timestamp',
                'location', 'event_type', 'event_subtype', 'asset',
                'amount', 'usd_value', 'notes', 'location_label',
                'address', 'transaction_hash',
            ])
            writer.writeheader()

            for event in events:
                writer.writerow({
                    'event_identifier': event.event_identifier,
                    'sequence_index': event.sequence_index,
                    'timestamp': event.timestamp,
                    'location': event.location,
                    'event_type': event.event_type,
                    'event_subtype': event.event_subtype,
                    'asset': event.asset,
                    'amount': event.amount,
                    'usd_value': event.usd_value,
                    'notes': event.notes,
                    'location_label': event.location_label,
                    'address': event.address,
                    'transaction_hash': event.transaction_hash,
                })

    def _export_manual_balances_to_csv(self, filepath: Path) -> None:
        """Export manual balances to CSV using ORM"""
        import csv

        balances = self.db.repos.manual_balances.get_all_balances()

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'asset', 'label', 'amount', 'location', 'tags',
            ])
            writer.writeheader()

            for balance in balances:
                tags = self.db.repos.manual_balances.get_balance_tags(balance.identifier)
                writer.writerow({
                    'asset': balance.asset,
                    'label': balance.label,
                    'amount': balance.amount,
                    'location': balance.location,
                    'tags': ','.join(tags) if tags else '',
                })

    def _export_tags_to_csv(self, filepath: Path) -> None:
        """Export tags to CSV using ORM"""
        import csv

        tags = self.db.repos.tags.get_all_tags()

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'name', 'description', 'background_color', 'foreground_color',
            ])
            writer.writeheader()

            for tag in tags:
                writer.writerow({
                    'name': tag.name,
                    'description': tag.description,
                    'background_color': tag.background_color,
                    'foreground_color': tag.foreground_color,
                })

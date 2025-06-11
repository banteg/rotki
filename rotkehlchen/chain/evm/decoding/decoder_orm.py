"""EVM transaction decoder using ORM"""

import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.structures import DecoderContext
from rotkehlchen.chain.evm.structures import EvmTxReceipt
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, Timestamp
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.orm.database import RotkehlchenDatabase
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EVMTransactionDecoder:
    """EVM transaction decoder using ORM for database operations"""

    def __init__(
            self,
            database: 'RotkehlchenDatabase',
            evm_inquirer: 'EvmNodeInquirer',
            msg_aggregator: 'MessagesAggregator',
            base_tools: 'BaseDecoderTools',
    ):
        self.database = database
        self.evm_inquirer = evm_inquirer
        self.msg_aggregator = msg_aggregator
        self.base = base_tools
        self.decoders: dict[ChecksumEvmAddress, Any] = {}

    def _get_or_create_transaction(
            self,
            tx_hash: str,
    ) -> tuple[EvmTransaction, EvmTxReceipt]:
        """Get or create a transaction and its receipt using ORM"""
        # Check if transaction exists in database
        tx_data = self.database.repos.evm_transactions.get_transaction_by_hash(
            tx_hash=tx_hash,
            chain_id=self.evm_inquirer.chain_id,
        )

        if tx_data:
            # Convert ORM model to EvmTransaction
            # TODO: Proper conversion based on actual model structure
            transaction = EvmTransaction(
                tx_hash=tx_data.tx_hash,
                chain_id=tx_data.chain_id,
                timestamp=Timestamp(tx_data.timestamp),
                block_number=tx_data.block_number,
                from_address=tx_data.from_address,
                to_address=tx_data.to_address,
                value=FVal(tx_data.value),
                gas=tx_data.gas,
                gas_price=FVal(tx_data.gas_price),
                gas_used=tx_data.gas_used,
                input_data=tx_data.input_data,
                nonce=tx_data.nonce,
            )

            # Get receipt
            receipt_data = self.database.repos.evm_transactions.get_receipt(
                tx_hash=tx_hash,
                chain_id=self.evm_inquirer.chain_id,
            )

            if receipt_data:
                receipt = EvmTxReceipt(
                    tx_hash=receipt_data.tx_hash,
                    chain_id=receipt_data.chain_id,
                    contract_address=receipt_data.contract_address,
                    status=receipt_data.status,
                    logs=receipt_data.logs,  # TODO: Deserialize logs
                )
            else:
                # Fetch receipt from node
                receipt = self._fetch_receipt_from_node(tx_hash)
                self._save_receipt_to_database(receipt)
        else:
            # Fetch transaction from node
            transaction = self._fetch_transaction_from_node(tx_hash)
            receipt = self._fetch_receipt_from_node(tx_hash)

            # Save to database
            self._save_transaction_to_database(transaction)
            self._save_receipt_to_database(receipt)

        return transaction, receipt

    def _fetch_transaction_from_node(self, tx_hash: str) -> EvmTransaction:
        """Fetch transaction from node"""
        try:
            tx_data = self.evm_inquirer.get_transaction_by_hash(tx_hash)
            return EvmTransaction(
                tx_hash=tx_hash,
                chain_id=self.evm_inquirer.chain_id,
                timestamp=self.evm_inquirer.get_transaction_timestamp(tx_hash),
                block_number=tx_data['blockNumber'],
                from_address=hex_or_bytes_to_address(tx_data['from']),
                to_address=hex_or_bytes_to_address(tx_data.get('to', '0x0')),
                value=from_wei(FVal(hex_or_bytes_to_int(tx_data['value']))),
                gas=hex_or_bytes_to_int(tx_data['gas']),
                gas_price=from_wei(FVal(hex_or_bytes_to_int(tx_data['gasPrice']))),
                gas_used=hex_or_bytes_to_int(tx_data.get('gasUsed', 0)),
                input_data=tx_data['input'],
                nonce=hex_or_bytes_to_int(tx_data['nonce']),
            )
        except RemoteError as e:
            log.error(f'Failed to fetch transaction {tx_hash}: {e}')
            raise

    def _fetch_receipt_from_node(self, tx_hash: str) -> EvmTxReceipt:
        """Fetch receipt from node"""
        try:
            receipt_data = self.evm_inquirer.get_transaction_receipt(tx_hash)
            return EvmTxReceipt(
                tx_hash=tx_hash,
                chain_id=self.evm_inquirer.chain_id,
                contract_address=hex_or_bytes_to_address(receipt_data.get('contractAddress', '0x0')),
                status=bool(hex_or_bytes_to_int(receipt_data.get('status', '0x1'))),
                logs=receipt_data.get('logs', []),
            )
        except RemoteError as e:
            log.error(f'Failed to fetch receipt for {tx_hash}: {e}')
            raise

    def _save_transaction_to_database(self, transaction: EvmTransaction) -> None:
        """Save transaction to database using ORM"""
        with self.database.repos.unit_of_work():
            self.database.repos.evm_transactions.add_transaction(
                tx_hash=transaction.tx_hash,
                chain_id=transaction.chain_id,
                timestamp=transaction.timestamp,
                block_number=transaction.block_number,
                from_address=transaction.from_address,
                to_address=transaction.to_address,
                value=str(transaction.value),
                gas=transaction.gas,
                gas_price=str(transaction.gas_price),
                gas_used=transaction.gas_used,
                input_data=transaction.input_data,
                nonce=transaction.nonce,
            )

    def _save_receipt_to_database(self, receipt: EvmTxReceipt) -> None:
        """Save receipt to database using ORM"""
        with self.database.repos.unit_of_work():
            self.database.repos.evm_transactions.add_receipt(
                tx_hash=receipt.tx_hash,
                chain_id=receipt.chain_id,
                contract_address=receipt.contract_address,
                status=receipt.status,
                logs=receipt.logs,  # TODO: Serialize logs
            )

    def decode_transaction(
            self,
            tx_hash: str,
            ignore_cache: bool = False,
    ) -> list[EvmEvent]:
        """Decode a transaction and return events using ORM"""
        # Check if already decoded
        if not ignore_cache:
            is_decoded = self.database.repos.evm_transactions.is_transaction_decoded(
                tx_hash=tx_hash,
                chain_id=self.evm_inquirer.chain_id,
            )
            if is_decoded:
                # Return existing events
                return self._get_decoded_events_from_database(tx_hash)

        # Get or create transaction
        transaction, receipt = self._get_or_create_transaction(tx_hash)

        # Decode transaction
        events = self._decode_transaction(transaction, receipt)

        # Save decoded events
        self._save_decoded_events(transaction, events)

        return events

    def _decode_transaction(
            self,
            transaction: EvmTransaction,
            receipt: EvmTxReceipt,
    ) -> list[EvmEvent]:
        """Decode a transaction into events"""
        events: list[EvmEvent] = []

        # Create base event for ETH transfer if value > 0
        if transaction.value > ZERO:
            base_event = EvmEvent(
                tx_hash=transaction.tx_hash,
                sequence_index=0,
                timestamp=transaction.timestamp,
                location=self.evm_inquirer.chain_name,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=self.evm_inquirer.native_token,
                balance=transaction.value,
                location_label=transaction.from_address,
                notes=f'Send {transaction.value} {self.evm_inquirer.native_token.symbol} '
                      f'to {transaction.to_address}',
                address=transaction.from_address,
            )
            events.append(base_event)

        # Decode logs
        for log_idx, log in enumerate(receipt.logs):
            decoded_events = self._decode_log(
                transaction=transaction,
                log=log,
                log_idx=log_idx + 1,  # Start from 1 after base event
            )
            events.extend(decoded_events)

        # Apply protocol-specific decoders
        context = DecoderContext(
            tx_hash=transaction.tx_hash,
            transaction=transaction,
            all_events=events,
        )

        for decoder_address, decoder in self.decoders.items():
            if self._should_use_decoder(transaction, receipt, decoder_address):
                decoding_output = decoder.decode(context)
                if decoding_output and decoding_output.matched_counterparty:
                    events = decoding_output.events
                    break

        return events

    def _decode_log(
            self,
            transaction: EvmTransaction,
            log: dict[str, Any],
            log_idx: int,
    ) -> list[EvmEvent]:
        """Decode a single log entry"""
        return []

        # TODO: Implement log decoding logic
        # This would parse the log topics and data to create appropriate events

    def _should_use_decoder(
            self,
            transaction: EvmTransaction,
            receipt: EvmTxReceipt,
            decoder_address: ChecksumEvmAddress,
    ) -> bool:
        """Check if a decoder should be used for this transaction"""
        # Check if transaction interacts with decoder's contract
        if transaction.to_address == decoder_address:
            return True

        # Check if any log is from decoder's contract
        for log in receipt.logs:
            if hex_or_bytes_to_address(log['address']) == decoder_address:
                return True

        return False

    def _save_decoded_events(
            self,
            transaction: EvmTransaction,
            events: list[EvmEvent],
    ) -> None:
        """Save decoded events to database using ORM"""
        with self.database.repos.unit_of_work():
            if len(events) > 0:
                # Add history events
                for event in events:
                    self.database.repos.history_events.add_evm_event(event)
            else:
                # Mark as ignored (likely spam)
                self.database.repos.evm_transactions.mark_as_ignored(
                    tx_hash=transaction.tx_hash,
                    chain_id=transaction.chain_id,
                )

            # Mark transaction as decoded
            self.database.repos.evm_transactions.mark_as_decoded(
                tx_hash=transaction.tx_hash,
                chain_id=transaction.chain_id,
            )

    def _get_decoded_events_from_database(self, tx_hash: str) -> list[EvmEvent]:
        """Get already decoded events from database using ORM"""
        event_models = self.database.repos.history_events.get_evm_events_by_tx_hash(
            tx_hash=tx_hash,
            chain_id=self.evm_inquirer.chain_id,
        )

        events = []
        for model in event_models:
            # TODO: Convert ORM model to EvmEvent
            # This needs proper implementation based on model structure
            event = EvmEvent(
                tx_hash=model.tx_hash,
                sequence_index=model.sequence_index,
                timestamp=Timestamp(model.timestamp),
                location=model.location,
                event_type=HistoryEventType.deserialize(model.event_type),
                event_subtype=HistoryEventSubType.deserialize(model.event_subtype),
                asset=model.asset,
                balance=FVal(model.amount),
                location_label=model.location_label,
                notes=model.notes,
                address=model.address,
            )
            events.append(event)

        return events

    def register_decoder(self, address: ChecksumEvmAddress, decoder: Any) -> None:
        """Register a protocol-specific decoder"""
        self.decoders[address] = decoder

    def decode_transaction_hashes(
            self,
            tx_hashes: list[str],
            ignore_cache: bool = False,
    ) -> dict[str, list[EvmEvent]]:
        """Decode multiple transactions using ORM"""
        results = {}

        for tx_hash in tx_hashes:
            try:
                events = self.decode_transaction(tx_hash, ignore_cache=ignore_cache)
                results[tx_hash] = events
            except Exception as e:
                log.error(f'Failed to decode transaction {tx_hash}: {e}')
                self.msg_aggregator.add_error(
                    f'Failed to decode transaction {tx_hash}: {e!s}',
                )
                results[tx_hash] = []

        return results

    def get_decoding_stats(self) -> dict[str, int]:
        """Get statistics about decoded transactions using ORM"""
        return {
            'total_transactions': self.database.repos.evm_transactions.count_all_transactions(
                chain_id=self.evm_inquirer.chain_id,
            ),
            'decoded_transactions': self.database.repos.evm_transactions.count_decoded_transactions(
                chain_id=self.evm_inquirer.chain_id,
            ),
            'ignored_transactions': self.database.repos.evm_transactions.count_ignored_transactions(
                chain_id=self.evm_inquirer.chain_id,
            ),
        }

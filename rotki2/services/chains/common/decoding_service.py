"""Transaction decoding service for EVM chains."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from rotki2.common.types import ChecksumEvmAddress, EVMTxHash
from rotki2.db.models.user.history import HistoryEvent

logger = logging.getLogger(__name__)


class DecodingStatus(Enum):
    """Status of a decoding operation."""
    DECODED = "decoded"
    NOT_DECODED = "not_decoded"
    FAILED = "failed"


@dataclass
class DecodedTransaction:
    """Result of decoding a transaction."""
    tx_hash: EVMTxHash
    status: DecodingStatus
    events: list[HistoryEvent]
    notes: str | None = None
    error: str | None = None


class ProtocolDecoder(ABC):
    """Base class for protocol-specific decoders."""
    
    @abstractmethod
    def can_decode(self, tx_data: dict[str, Any]) -> bool:
        """Check if this decoder can handle the transaction."""
        ...
    
    @abstractmethod
    async def decode(self, tx_data: dict[str, Any]) -> list[HistoryEvent]:
        """Decode the transaction into history events."""
        ...


class DecodingService:
    """
    Service for decoding blockchain transactions into history events.
    
    This replaces the old EVMTransactionDecoder logic with a stateless,
    async implementation that can be used across all EVM chains.
    """
    
    def __init__(self, chain_id: int, chain_name: str) -> None:
        """
        Initialize the decoding service.
        
        Args:
            chain_id: The chain ID for this EVM network
            chain_name: Human-readable name of the chain
        """
        self.chain_id = chain_id
        self.chain_name = chain_name
        self.protocol_decoders: list[ProtocolDecoder] = []
        self._decoder_registry: dict[str, ProtocolDecoder] = {}
        logger.info(f"Initializing decoding service for {chain_name}")
    
    def register_decoder(self, protocol_name: str, decoder: ProtocolDecoder) -> None:
        """
        Register a protocol-specific decoder.
        
        Args:
            protocol_name: Name of the protocol (e.g., "uniswap", "aave")
            decoder: The decoder instance
        """
        if protocol_name in self._decoder_registry:
            logger.warning(f"Overwriting existing decoder for {protocol_name}")
        
        self._decoder_registry[protocol_name] = decoder
        self.protocol_decoders.append(decoder)
        logger.debug(f"Registered decoder for {protocol_name}")
    
    def unregister_decoder(self, protocol_name: str) -> bool:
        """
        Unregister a protocol decoder.
        
        Args:
            protocol_name: Name of the protocol
            
        Returns:
            True if decoder was removed, False if not found
        """
        decoder = self._decoder_registry.pop(protocol_name, None)
        if decoder:
            self.protocol_decoders.remove(decoder)
            logger.debug(f"Unregistered decoder for {protocol_name}")
            return True
        return False
    
    async def decode_transaction(
        self,
        tx_data: dict[str, Any],
        receipt_data: dict[str, Any],
        logs: list[dict[str, Any]],
    ) -> DecodedTransaction:
        """
        Decode a transaction using registered decoders.
        
        Args:
            tx_data: Transaction data from the node
            receipt_data: Transaction receipt data
            logs: Transaction logs/events
            
        Returns:
            Decoded transaction with events
        """
        tx_hash = EVMTxHash(tx_data["hash"])
        
        # Combine all data for decoders
        full_tx_data = {
            "transaction": tx_data,
            "receipt": receipt_data,
            "logs": logs,
            "chain_id": self.chain_id,
        }
        
        all_events = []
        errors = []
        
        # Try each decoder
        for decoder in self.protocol_decoders:
            try:
                if decoder.can_decode(full_tx_data):
                    events = await decoder.decode(full_tx_data)
                    all_events.extend(events)
                    logger.debug(
                        f"Decoder {decoder.__class__.__name__} decoded {len(events)} events "
                        f"for tx {tx_hash}"
                    )
            except Exception as e:
                error_msg = f"Decoder {decoder.__class__.__name__} failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Determine status
        if errors and not all_events:
            status = DecodingStatus.FAILED
            error = "; ".join(errors)
        elif all_events:
            status = DecodingStatus.DECODED
            error = None
        else:
            status = DecodingStatus.NOT_DECODED
            error = None
        
        return DecodedTransaction(
            tx_hash=tx_hash,
            status=status,
            events=all_events,
            error=error,
        )
    
    async def decode_logs(
        self,
        logs: list[dict[str, Any]],
        tx_hash: EVMTxHash | None = None,
    ) -> list[HistoryEvent]:
        """
        Decode logs directly without full transaction context.
        
        Args:
            logs: List of log entries
            tx_hash: Optional transaction hash for context
            
        Returns:
            List of decoded history events
        """
        all_events = []
        
        # Create minimal tx data for log-only decoding
        full_tx_data = {
            "logs": logs,
            "chain_id": self.chain_id,
            "tx_hash": tx_hash,
        }
        
        for decoder in self.protocol_decoders:
            try:
                if hasattr(decoder, "can_decode_logs") and decoder.can_decode_logs(logs):
                    events = await decoder.decode_logs(logs)
                    all_events.extend(events)
            except Exception as e:
                logger.error(f"Log decoder {decoder.__class__.__name__} failed: {e}")
        
        return all_events
    
    def get_registered_protocols(self) -> list[str]:
        """Get list of registered protocol names."""
        return list(self._decoder_registry.keys())
    
    def __repr__(self) -> str:
        """String representation of the service."""
        return (
            f"<DecodingService("
            f"chain_name='{self.chain_name}', "
            f"protocols={len(self._decoder_registry)})"
            f">"
        )


class BaseEvmDecoder(ProtocolDecoder):
    """Base decoder for common EVM operations like transfers."""
    
    # Common event signatures
    TRANSFER_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    APPROVAL_SIGNATURE = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
    
    def __init__(self, chain_id: int) -> None:
        self.chain_id = chain_id
    
    def can_decode(self, tx_data: dict[str, Any]) -> bool:
        """Check if transaction has common EVM events."""
        logs = tx_data.get("logs", [])
        for log in logs:
            topics = log.get("topics", [])
            if topics and topics[0] in (self.TRANSFER_SIGNATURE, self.APPROVAL_SIGNATURE):
                return True
        return False
    
    async def decode(self, tx_data: dict[str, Any]) -> list[HistoryEvent]:
        """Decode basic EVM events."""
        events = []
        logs = tx_data.get("logs", [])
        
        for log in logs:
            topics = log.get("topics", [])
            if not topics:
                continue
            
            if topics[0] == self.TRANSFER_SIGNATURE:
                # Basic ERC20 transfer decoding
                # This is a simplified example - real implementation would be more complex
                pass
            elif topics[0] == self.APPROVAL_SIGNATURE:
                # Basic approval decoding
                pass
        
        return events
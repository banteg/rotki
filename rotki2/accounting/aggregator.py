"""Async EVM accounting aggregator for protocol-specific processing"""
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Iterator
    
    from rotkehlchen.accounting.mixins.event import AccountingEventMixin
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.user_messages import MessagesAggregator
    from rotki2.accounting.pot import AsyncAccountingPot
    from rotki2.api.v2.services.database import DatabaseService

logger = RotkehlchenLogsAdapter(__name__)

# Protocol handlers mapping
PROTOCOL_HANDLERS = {
    'uniswap': 'UniswapAccountingHandler',
    'compound': 'CompoundAccountingHandler',
    'aave': 'AaveAccountingHandler',
    'curve': 'CurveAccountingHandler',
    'balancer': 'BalancerAccountingHandler',
    'yearn': 'YearnAccountingHandler',
    '1inch': 'OneInchAccountingHandler',
    'makerdao': 'MakerDAOAccountingHandler',
    'liquity': 'LiquityAccountingHandler',
    'convex': 'ConvexAccountingHandler',
}


class AsyncEVMAccountingAggregator:
    """Async aggregator for EVM-specific accounting rules
    
    This class routes events to protocol-specific handlers for
    proper accounting treatment.
    """
    
    def __init__(
        self,
        database: 'DatabaseService',
        msg_aggregator: 'MessagesAggregator',
        chains_aggregator: 'ChainsAggregator',
        premium: 'Premium | None',
    ):
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.chains_aggregator = chains_aggregator
        self.premium = premium
        
        # Protocol handlers will be loaded dynamically
        self.handlers: dict[str, Any] = {}
    
    async def process_event(
        self,
        pot: 'AsyncAccountingPot',
        event: 'AccountingEventMixin',
        events_iterator: Iterator['AccountingEventMixin'],
    ) -> None:
        """Process an EVM event with protocol-specific logic"""
        if not isinstance(event, HistoryEvent):
            # Not an EVM event, process normally
            await event.process(
                accounting=pot,
                events_iterator=events_iterator,
            )
            return
        
        # Get counterparty (protocol)
        counterparty = getattr(event, 'counterparty', None)
        if not counterparty:
            # No specific protocol, process normally
            await self._process_generic_event(pot, event, events_iterator)
            return
        
        # Get protocol handler
        handler = await self._get_protocol_handler(counterparty)
        if handler:
            # Process with protocol-specific logic
            await handler.process_event(
                pot=pot,
                event=event,
                events_iterator=events_iterator,
            )
        else:
            # No specific handler, process generically
            await self._process_generic_event(pot, event, events_iterator)
    
    async def _get_protocol_handler(self, protocol: str) -> Any | None:
        """Get or create protocol-specific handler"""
        protocol_lower = protocol.lower()
        
        # Check cache
        if protocol_lower in self.handlers:
            return self.handlers[protocol_lower]
        
        # Check if handler exists
        if protocol_lower not in PROTOCOL_HANDLERS:
            return None
        
        # For now, return None - in full implementation would
        # dynamically load protocol handlers
        return None
    
    async def _process_generic_event(
        self,
        pot: 'AsyncAccountingPot',
        event: HistoryEvent,
        events_iterator: Iterator['AccountingEventMixin'],
    ) -> None:
        """Process a generic EVM event"""
        # Map event types to accounting actions
        event_type = event.event_type
        event_subtype = event.event_subtype
        
        # Determine action type
        if event_type == 'trade':
            if event_subtype == 'buy':
                await self._process_buy(pot, event)
            elif event_subtype == 'sell':
                await self._process_sell(pot, event)
            else:
                await self._process_swap(pot, event)
                
        elif event_type == 'receive':
            await self._process_receive(pot, event)
            
        elif event_type == 'send':
            await self._process_send(pot, event)
            
        elif event_type == 'fee':
            await self._process_fee(pot, event)
            
        elif event_type in ('deposit', 'withdrawal'):
            # These usually don't have tax implications
            await self._process_transfer(pot, event)
            
        else:
            # Unknown event type
            logger.warning(f'Unknown event type: {event_type}/{event_subtype}')
    
    async def _process_buy(
        self,
        pot: 'AsyncAccountingPot',
        event: HistoryEvent,
    ) -> None:
        """Process a buy event"""
        # In a buy, we acquire the asset
        await pot.add_in_event(
            event_type=ActionType.TRADE,
            asset=event.asset,
            amount=event.balance.amount,
            timestamp=event.timestamp,
            extra_data={'event_id': event.identifier},
        )
    
    async def _process_sell(
        self,
        pot: 'AsyncAccountingPot',
        event: HistoryEvent,
    ) -> None:
        """Process a sell event"""
        # In a sell, we dispose of the asset
        await pot.add_out_event(
            event_type=ActionType.TRADE,
            asset=event.asset,
            amount=event.balance.amount,
            timestamp=event.timestamp,
            taxable=True,
            extra_data={'event_id': event.identifier},
        )
    
    async def _process_swap(
        self,
        pot: 'AsyncAccountingPot',
        event: HistoryEvent,
    ) -> None:
        """Process a swap event"""
        # Swaps are more complex - need to look at paired events
        # For now, treat as a simple trade
        if event.balance.amount > 0:
            await self._process_buy(pot, event)
        else:
            await self._process_sell(pot, event)
    
    async def _process_receive(
        self,
        pot: 'AsyncAccountingPot',
        event: HistoryEvent,
    ) -> None:
        """Process a receive event"""
        # Determine if it's income or a transfer
        if event.event_subtype in ('reward', 'interest', 'airdrop'):
            # This is income
            await pot.add_asset_change_event(
                event_type=ActionType.INCOME,
                asset=event.asset,
                amount=event.balance.amount,
                timestamp=event.timestamp,
                extra_data={'event_id': event.identifier},
            )
        else:
            # Regular receive (transfer in)
            await pot.add_in_event(
                event_type=ActionType.TRANSFER,
                asset=event.asset,
                amount=event.balance.amount,
                timestamp=event.timestamp,
                extra_data={'event_id': event.identifier},
            )
    
    async def _process_send(
        self,
        pot: 'AsyncAccountingPot',
        event: HistoryEvent,
    ) -> None:
        """Process a send event"""
        # Sends are typically transfers out or expenses
        if event.event_subtype == 'fee':
            event_type = ActionType.FEE
            taxable = True
        else:
            event_type = ActionType.TRANSFER
            taxable = False
        
        await pot.add_out_event(
            event_type=event_type,
            asset=event.asset,
            amount=abs(event.balance.amount),
            timestamp=event.timestamp,
            taxable=taxable,
            extra_data={'event_id': event.identifier},
        )
    
    async def _process_fee(
        self,
        pot: 'AsyncAccountingPot',
        event: HistoryEvent,
    ) -> None:
        """Process a fee event"""
        await pot.add_out_event(
            event_type=ActionType.FEE,
            asset=event.asset,
            amount=abs(event.balance.amount),
            timestamp=event.timestamp,
            taxable=True,
            extra_data={'event_id': event.identifier},
        )
    
    async def _process_transfer(
        self,
        pot: 'AsyncAccountingPot',
        event: HistoryEvent,
    ) -> None:
        """Process a transfer (deposit/withdrawal) event"""
        # Transfers typically don't have tax implications
        # Just track them without affecting cost basis
        logger.debug(
            f'Processing transfer event {event.identifier} '
            f'of {event.balance.amount} {event.asset.identifier}'
        )
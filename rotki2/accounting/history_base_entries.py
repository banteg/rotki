"""Events accountant for processing history base entries"""
import logging
from typing import TYPE_CHECKING, Any, TypeVar, cast

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotki2.accounting.rules import AccountingRulesManager
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.constants import ONE
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import EventDirection, HistoryEventSubType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp

if TYPE_CHECKING:
    from collections.abc import Callable

    from more_itertools import peekable

    from rotki2.accounting.aggregator import EVMAccountingAggregator
    from rotki2.accounting.mixins import AccountingEventMixin
    from rotki2.accounting.pot import AccountingPot

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
T = TypeVar('T', bound=HistoryBaseEntry)


class EventsAccountant:
    """
    This class contains the different rules applied to history events during the accounting
    process. It applies special rules for evm events and also the default defined rules.
    """

    def __init__(
            self,
            evm_accounting_aggregators: 'EVMAccountingAggregator',
            pot: 'AccountingPot',
    ) -> None:
        self.evm_accounting_aggregators = evm_accounting_aggregators
        self.pot = pot
        self.rules_manager = AccountingRulesManager(
            database=self.pot.database,
            evm_aggregators=self.evm_accounting_aggregators,
            pot=self.pot,
        )

    async def reset(self) -> None:
        await self.rules_manager.reset()

    async def process(
            self,
            event: HistoryBaseEntry,
            events_iterator: "peekable['AccountingEventMixin']",
    ) -> int:
        """Process a history base entry and return number of actions consumed from the iterator"""
        event_direction = event.maybe_get_direction()
        if event_direction is None:
            log.error(
                f'Failed to retrieve direction for {event.event_type=} {event.event_subtype}. '
                f'Skipping...',
            )
            return 1

        if event_direction == EventDirection.NEUTRAL:
            log.debug(f'Skipping neutral event {event.identifier=}')
            return 1

        timestamp = event.get_timestamp_in_sec()
        event_settings, event_callback = self.rules_manager.get_event_settings(event)
        if event_settings is None:
            log.debug(
                f'During transaction accounting found history base entry {event} '
                f'with no mapped event settings. Skipping...',
            )
            return 1

        # if there is any module specific accountant functionality call it
        if isinstance(event, EvmEvent) and event_callback is not None:
            await event_callback(
                pot=self.pot,
                event=event,  # ignore is due to callbacks being only for evm events
                other_events=events_iterator,  # type: ignore
            )

        general_extra_data = {}
        if isinstance(event, EvmEvent):
            general_extra_data['tx_hash'] = event.tx_hash.hex()

        if event_settings.accounting_treatment == TxAccountingTreatment.SWAP:
            fee_event = None
            next_event = events_iterator.peek(None)
            if next_event is None:
                log.error(
                    f'Tried to process accounting swap but could not find the in '
                    f'event for {event}',
                )
                return 1

            if not isinstance(next_event, HistoryBaseEntry) or next_event.event_identifier != event.event_identifier:  # noqa: E501
                log.error(
                    f'Tried to process accounting swap but the in '
                    f'event for {event} is not there',
                )
                return 1

            in_event = cast('HistoryBaseEntry', next(events_iterator))  # guaranteed by the if check  # noqa: E501
            next_event = events_iterator.peek(None)
            if next_event and isinstance(next_event, HistoryBaseEntry) and next_event.event_identifier == event.event_identifier and next_event.event_subtype == HistoryEventSubType.FEE:  # noqa: E501
                fee_event = cast('HistoryBaseEntry', next(events_iterator))  # guaranteed by if check  # noqa: E501

            # Check if any assets are ignored
            ignored_asset_ids = await self.pot.database.get_ignored_asset_ids()
            if (
                    event.asset.identifier in ignored_asset_ids or
                    in_event.asset.identifier in ignored_asset_ids or
                    (fee_event is not None and fee_event.asset.identifier in ignored_asset_ids)
            ):
                # skip out_event and in_event, and maybe fee_event
                return 3 if fee_event is not None else 2

            return await self._process_swap(
                timestamp=timestamp,
                out_event=event,
                in_event=in_event,
                fee_event=fee_event,
                event_settings=event_settings,
                general_extra_data=general_extra_data,
            )

        await self.pot.add_asset_change_event(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            asset=event.asset,
            amount=event.amount if event_direction == EventDirection.IN else -event.amount,
            timestamp=timestamp,
            extra_data=general_extra_data | {
                'direction': event_direction.value,
                'notes': event.notes or '',
                'location': event.location,
                'taxable': event_settings.taxable,
                'count_entire_amount_spend': event_settings.count_entire_amount_spend,
                'count_cost_basis_pnl': event_settings.count_cost_basis_pnl,
            },
        )
        return 1

    async def _process_swap(
            self,
            timestamp: Timestamp,
            out_event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            fee_event: HistoryBaseEntry | None,
            event_settings: BaseEventSettings,
            general_extra_data: dict[str, Any],
    ) -> int:
        """
        Takes out_event (spend part), in_event (acquisition part), optionally fee part
        and generates corresponding accounting events prioritising the following order:
        1. out_event is always first
        2. fee_event comes just after the other event (in/out) with the same asset
        3. sequence of the in_event and fee_event is preserved
        """
        fee_info = None
        if fee_event is not None:
            fee_info = (fee_event.amount, fee_event.asset)

        prices = await self.pot.get_prices_for_swap(
            timestamp=timestamp,
            amount_in=in_event.amount,
            asset_in=in_event.asset,
            amount_out=out_event.amount,
            asset_out=out_event.asset,
            fee_info=fee_info,
        )
        if prices is None:
            log.debug(f'Skipping {self} at accounting for a swap due to inability to find a price')
            return 2

        group_id = out_event.event_identifier + str(out_event.sequence_index) + str(in_event.sequence_index)  # noqa: E501
        extra_data = general_extra_data | {'group_id': group_id}
        
        # Process the out event (spend)
        _, trade_taxable_amount = await self.pot.add_out_event(
            event_type=out_event.get_accounting_event_type(),
            asset=out_event.asset,
            amount=out_event.amount,
            timestamp=timestamp,
            price=prices[0],
            # Determine taxability for the out_event:
            # - Event is only taxable if explicitly allowed in event_settings
            # - AND either:
            #   - It's a crypto-to-fiat trade (receiving fiat), OR
            #   - It's a crypto-to-crypto trade and include_crypto2crypto is enabled
            taxable=(in_event.asset.is_fiat() or self.pot.settings.get('include_crypto2crypto', True)) and event_settings.taxable,  # noqa: E501
            extra_data=extra_data | {
                'originating_event_id': out_event.identifier,
                'notes': out_event.notes or '',
                'location': out_event.location,
                'count_entire_amount_spend': False,
            },
        )

        # Process the in event (acquisition)
        await self.pot.add_in_event(
            event_type=in_event.get_accounting_event_type(),
            asset=in_event.asset,
            amount=in_event.amount,
            timestamp=timestamp,
            price=prices[1],
            extra_data=extra_data | {
                'notes': in_event.notes or '',
                'location': in_event.location,
                'taxable': False,  # acquisitions in swaps are never taxable
            },
        )

        # Process fee if present
        if fee_event is not None:
            fee_price = None
            if fee_event.asset == self.pot.profit_currency:
                fee_price = Price(ONE)
            elif fee_event.asset == in_event.asset:
                fee_price = prices[1]
            elif fee_event.asset == out_event.asset:
                fee_price = prices[0]

            if self.pot.settings.get('include_fees_in_cost_basis', True):
                # If fee is included in cost basis, we just reduce the amount of fee asset owned
                fee_taxable = False
                fee_taxable_amount_ratio = ONE
            else:
                # Otherwise we make it a normal spend event
                fee_taxable = True
                fee_taxable_amount_ratio = trade_taxable_amount / out_event.amount

            await self.pot.add_out_event(
                event_type=AccountingEventType.FEE,
                asset=fee_event.asset,
                amount=fee_event.amount,
                timestamp=timestamp,
                price=fee_price,
                taxable=fee_taxable,
                extra_data=extra_data | {
                    'originating_event_id': fee_event.identifier,
                    'notes': fee_event.notes,
                    'location': fee_event.location,
                    # By setting the taxable amount ratio we determine how much of the fee
                    # spending should be a taxable spend and how much free.
                    'taxable_amount_ratio': fee_taxable_amount_ratio,
                    'count_cost_basis_pnl': True,
                    'count_entire_amount_spend': True,
                },
            )

        return 3 if fee_event is not None else 2
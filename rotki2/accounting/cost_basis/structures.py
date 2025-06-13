"""Cost basis data structures for accounting"""
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NamedTuple, Optional

from rotkehlchen.constants import ZERO
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import Location, Price, Timestamp

if TYPE_CHECKING:
    from rotki2.accounting.structures import ProcessedAccountingEvent


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class AssetAcquisitionEvent:
    amount: FVal
    remaining_amount: FVal = field(init=False)  # Same as amount but reduced during processing
    timestamp: Timestamp
    rate: Price
    index: int

    def __post_init__(self) -> None:
        self.remaining_amount = self.amount

    def __str__(self) -> str:
        return (
            f'AssetAcquisitionEvent @{self.timestamp}. amount: {self.amount} rate: {self.rate}'
        )

    @classmethod
    def from_processed_event(cls: type['AssetAcquisitionEvent'], event: 'ProcessedAccountingEvent') -> 'AssetAcquisitionEvent':  # noqa: E501
        return cls(
            amount=event.taxable_amount + event.free_amount,
            timestamp=event.timestamp,
            rate=event.price,
            index=event.index,
        )

    @classmethod
    def deserialize(cls: type['AssetAcquisitionEvent'], data: dict[str, Any]) -> 'AssetAcquisitionEvent':  # noqa: E501
        """May raise DeserializationError"""
        try:
            return cls(
                amount=data['full_amount'],
                timestamp=data['timestamp'],
                rate=data['rate'],
                index=data['index'],
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    def serialize(self) -> dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'full_amount': str(self.amount),
            'rate': str(self.rate),
            'index': self.index,
        }

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, AssetAcquisitionEvent):
            raise NotImplementedError

        return self.timestamp > other.timestamp

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, AssetAcquisitionEvent):
            raise NotImplementedError

        return self.timestamp < other.timestamp


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class AssetSpendEvent:
    timestamp: Timestamp
    location: Location
    amount: FVal  # Amount of the asset we sell
    rate: FVal  # Rate in 'profit_currency' for which we sell 1 unit of the sold asset

    def __str__(self) -> str:
        return (
            f'AssetSpendEvent in {self.location!s} @ {self.timestamp}.'
            f'amount: {self.amount} rate: {self.rate}'
        )


class MatchedAcquisition(NamedTuple):
    amount: FVal  # the amount used from the acquisition event
    event: AssetAcquisitionEvent  # the acquisition event
    taxable: bool  # whether it counts for taxable or non-taxable cost basis

    def serialize(self) -> dict[str, Any]:
        """Turn to a dict to be serialized into the DB"""
        return {
            'amount': str(self.amount),
            'event': self.event.serialize(),
            'taxable': self.taxable,
        }

    @classmethod
    def deserialize(cls: type['MatchedAcquisition'], data: dict[str, Any]) -> 'MatchedAcquisition':
        """May raise DeserializationError"""
        try:
            event = AssetAcquisitionEvent.deserialize(data['event'])
            amount = deserialize_fval(
                value=data['amount'],
                name='amount',
                location='cost_basis',
            )
            taxable = data['taxable']
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

        return MatchedAcquisition(amount=amount, event=event, taxable=taxable)

    def to_string(self, converter: Callable[[Timestamp], str]) -> str:
        """User readable string version of the acquisition"""
        return (
            f'{self.amount} / {self.event.amount}  acquired '
            f'at {converter(self.event.timestamp)} for price: {self.event.rate}'
        )


class CostBasisInfo(NamedTuple):
    """Information on the cost basis of a spend event

        - `taxable_amount`: The amount out of `spending_amount` that is taxable,
                            calculated from the free after given time period rule.
        - `taxable_bought_cost`: How much it cost in `profit_currency` to buy
                                 the `taxable_amount`
        - `taxfree_bought_cost`: How much it cost in `profit_currency` to buy
                                 the taxfree_amount (selling_amount - taxable_amount)
        - `matched_acquisitions`: The list of acquisitions and amount per acquisition
                                   used for this spend
        - `is_complete: Boolean denoting whether enough information was recovered for the spend
    """
    taxable_amount: FVal
    taxable_bought_cost: FVal
    taxfree_bought_cost: FVal
    matched_acquisitions: list[MatchedAcquisition]
    is_complete: bool

    def serialize(self) -> dict[str, Any]:
        """Turn to a dict to be exported into the DB"""
        return {
            'is_complete': self.is_complete,
            'matched_acquisitions': [x.serialize() for x in self.matched_acquisitions],
        }

    @classmethod
    def deserialize(cls: type['CostBasisInfo'], data: dict[str, Any]) -> Optional['CostBasisInfo']:
        """Creates a CostBasisInfo object from a json dict made from serialize()

        May raise:
        - DeserializationError
        """
        try:
            is_complete = data['is_complete']
            matched_acquisitions = [MatchedAcquisition.deserialize(x) for x in data['matched_acquisitions']]  # noqa: E501
        except KeyError as e:
            raise DeserializationError(f'Could not decode CostBasisInfo json from the DB due to missing key {e!s}') from e  # noqa: E501

        return CostBasisInfo(  # the 0 are not serialized and not used at recall so is okay to skip
            taxable_amount=ZERO,
            taxable_bought_cost=ZERO,
            taxfree_bought_cost=ZERO,
            is_complete=is_complete,
            matched_acquisitions=matched_acquisitions,
        )

    def to_string(self, converter: Callable[[Timestamp], str]) -> tuple[str, str]:
        """
        Turn to 2 strings to be shown in exported files such as CSV for taxable and free cost basis
        """
        taxable = ''
        free = ''
        if not self.is_complete:
            taxable += 'Incomplete cost basis information for spend.'
            free += 'Incomplete cost basis information for spend.'

        if len(self.matched_acquisitions) == 0:
            return taxable, free

        for entry in self.matched_acquisitions:
            stringified = entry.to_string(converter)
            if entry.taxable:
                if taxable != '':
                    taxable += ' '
                taxable += stringified
            else:
                if free != '':
                    free += ' '
                free += stringified

        return taxable, free
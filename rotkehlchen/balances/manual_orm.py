"""Manual balance tracking using ORM"""

import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.orm.database import RotkehlchenDatabase

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_manually_tracked_balances(
        db: 'RotkehlchenDatabase',
        balance_type: BalanceType = BalanceType.ASSET,
) -> dict[Location, dict[Asset, Balance]]:
    """Get manually tracked balances from database using ORM

    Returns a dictionary mapping locations to assets and their balances
    """
    balances_dict: dict[Location, dict[Asset, Balance]] = {}

    # Get all manual balances from repository
    all_balances = db.repos.manual_balances.get_all_balances()

    for balance_entry in all_balances:
        # Skip if not the requested balance type
        if (balance_type == BalanceType.ASSET and balance_entry.label.startswith('liability:')) or (balance_type == BalanceType.LIABILITY and not balance_entry.label.startswith('liability:')):
            continue

        # Parse location and asset
        location = Location.deserialize_from_db(balance_entry.location)
        asset = Asset(balance_entry.asset)
        amount = FVal(balance_entry.amount)

        # Initialize location dict if needed
        if location not in balances_dict:
            balances_dict[location] = {}

        # Create balance object
        balance = Balance(amount=amount)

        # Aggregate if asset already exists for this location
        if asset in balances_dict[location]:
            balances_dict[location][asset] += balance
        else:
            balances_dict[location][asset] = balance

    return balances_dict


def add_manually_tracked_balances(
        db: 'RotkehlchenDatabase',
        location: Location,
        balances: list[dict],
) -> None:
    """Add manually tracked balances using ORM

    Args:
        db: The ORM database instance
        location: The location for the balances
        balances: List of balance dictionaries with asset, amount, and optional tags
    """
    with db.repos.unit_of_work():
        for balance_data in balances:
            asset = balance_data['asset']
            amount = str(balance_data['amount'])
            label = balance_data.get('label', f'Manual balance for {asset}')
            tags = balance_data.get('tags', [])

            # Add the balance
            balance_obj = db.repos.manual_balances.add_balance(
                asset=asset,
                label=label,
                amount=amount,
                location=location.serialize_for_db(),
                tags=tags,
            )

            log.debug(
                f'Added manual balance {balance_obj.identifier} for '
                f'{asset} at {location} with amount {amount}',
            )


def edit_manually_tracked_balance(
        db: 'RotkehlchenDatabase',
        balance_id: int,
        amount: str | None = None,
        label: str | None = None,
        tags: list[str] | None = None,
) -> bool:
    """Edit a manually tracked balance using ORM

    Returns True if balance was found and edited, False otherwise
    """
    with db.repos.unit_of_work():
        updated = db.repos.manual_balances.update_balance(
            identifier=balance_id,
            amount=amount,
            label=label,
            tags=tags,
        )

        if updated:
            log.debug(f'Updated manual balance {balance_id}')
        else:
            log.warning(f'Manual balance {balance_id} not found for update')

        return updated


def remove_manually_tracked_balance(
        db: 'RotkehlchenDatabase',
        balance_id: int,
) -> bool:
    """Remove a manually tracked balance using ORM

    Returns True if balance was found and removed, False otherwise
    """
    with db.repos.unit_of_work():
        success = db.repos.manual_balances.delete_balance(balance_id)

        if success:
            log.debug(f'Removed manual balance {balance_id}')
        else:
            log.warning(f'Manual balance {balance_id} not found for removal')

        return success


def get_manual_balance_by_id(
        db: 'RotkehlchenDatabase',
        balance_id: int,
) -> dict | None:
    """Get a specific manual balance by ID using ORM"""
    balance = db.repos.manual_balances.get_balance(balance_id)

    if not balance:
        return None

    return {
        'id': balance.identifier,
        'asset': balance.asset,
        'label': balance.label,
        'amount': balance.amount,
        'location': balance.location,
        'tags': db.repos.manual_balances.get_balance_tags(balance.identifier),
    }


def account_for_manually_tracked_asset_balances(
        db: 'RotkehlchenDatabase',
        balances: dict[Location, dict[Asset, Balance]],
        balance_type: BalanceType = BalanceType.ASSET,
) -> dict[Location, dict[Asset, Balance]]:
    """Account for manually tracked asset balances using ORM

    Adds manually tracked balances to the provided balances dictionary
    """
    manually_tracked = get_manually_tracked_balances(db, balance_type)

    for location, location_balances in manually_tracked.items():
        if location not in balances:
            balances[location] = {}

        for asset, balance in location_balances.items():
            if asset in balances[location]:
                balances[location][asset] += balance
            else:
                balances[location][asset] = balance

    return balances


def get_manual_balances_with_details(
        db: 'RotkehlchenDatabase',
        location: Location | None = None,
        asset: Asset | None = None,
) -> list[dict]:
    """Get manual balances with full details using ORM

    Can filter by location and/or asset
    """
    all_balances = db.repos.manual_balances.get_all_balances()

    result = []
    for balance in all_balances:
        # Apply filters if provided
        if location and balance.location != location.serialize_for_db():
            continue
        if asset and balance.asset != asset.identifier:
            continue

        result.append({
            'id': balance.identifier,
            'asset': balance.asset,
            'label': balance.label,
            'amount': balance.amount,
            'location': balance.location,
            'tags': db.repos.manual_balances.get_balance_tags(balance.identifier),
        })

    return result


def get_manual_balances_sum(
        db: 'RotkehlchenDatabase',
        asset: Asset | None = None,
        balance_type: BalanceType = BalanceType.ASSET,
) -> dict[Asset, FVal]:
    """Get sum of manual balances per asset using ORM"""
    all_balances = db.repos.manual_balances.get_all_balances()

    sums: dict[Asset, FVal] = {}

    for balance in all_balances:
        # Skip if not the requested balance type
        if (balance_type == BalanceType.ASSET and balance.label.startswith('liability:')) or (balance_type == BalanceType.LIABILITY and not balance.label.startswith('liability:')):
            continue

        # Apply asset filter if provided
        balance_asset = Asset(balance.asset)
        if asset and balance_asset != asset:
            continue

        amount = FVal(balance.amount)

        if balance_asset in sums:
            sums[balance_asset] += amount
        else:
            sums[balance_asset] = amount

    return sums


def get_latest_manual_balance_timestamp(db: 'RotkehlchenDatabase') -> Timestamp:
    """Get the timestamp of the latest manual balance entry using ORM"""
    # TODO: This would need a timestamp field in manual_balances table
    # TODO: For now return current timestamp
    from rotkehlchen.utils.misc import ts_now
    return ts_now()


def validate_manual_balance_data(
        asset: str,
        amount: str,
        location: str,
) -> tuple[Asset, FVal, Location]:
    """Validate manual balance input data

    Returns validated (asset, amount, location) tuple
    Raises InputError on validation failure
    """
    from rotkehlchen.errors.misc import InputError

    # Validate asset
    try:
        validated_asset = Asset(asset)
    except Exception as e:
        raise InputError(f'Invalid asset: {asset}') from e

    # Validate amount
    try:
        validated_amount = FVal(amount)
        if validated_amount < ZERO:
            raise InputError('Amount cannot be negative')
    except Exception as e:
        raise InputError(f'Invalid amount: {amount}') from e

    # Validate location
    try:
        validated_location = Location.deserialize(location)
    except Exception as e:
        raise InputError(f'Invalid location: {location}') from e

    return validated_asset, validated_amount, validated_location

"""Asset spam detection and management using ORM"""

import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.orm.database import RotkehlchenDatabase

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SpamAssetsManager:
    """Manages spam asset detection and filtering using ORM"""

    def __init__(self, db: 'RotkehlchenDatabase'):
        self.db = db
        self._spam_cache: set[str] | None = None

    def _load_spam_cache(self) -> None:
        """Load spam assets into cache from database using ORM"""
        if self._spam_cache is None:
            spam_assets = self.db.repos.spam_assets.get_all_spam_assets()
            self._spam_cache = {asset.identifier for asset in spam_assets}

    def is_spam_asset(self, asset_identifier: str) -> bool:
        """Check if an asset is marked as spam using ORM"""
        self._load_spam_cache()
        return asset_identifier in self._spam_cache

    def mark_asset_as_spam(self, asset_identifier: str) -> bool:
        """Mark an asset as spam using ORM

        Returns True if successfully marked, False if already spam
        """
        with self.db.repos.unit_of_work():
            success = self.db.repos.spam_assets.add_spam_asset(asset_identifier)
            if success and self._spam_cache is not None:
                self._spam_cache.add(asset_identifier)
            return success

    def unmark_asset_as_spam(self, asset_identifier: str) -> bool:
        """Remove spam marking from an asset using ORM

        Returns True if successfully unmarked, False if not found
        """
        with self.db.repos.unit_of_work():
            success = self.db.repos.spam_assets.remove_spam_asset(asset_identifier)
            if success and self._spam_cache is not None:
                self._spam_cache.discard(asset_identifier)
            return success

    def get_all_spam_assets(self) -> list[str]:
        """Get all spam asset identifiers using ORM"""
        spam_assets = self.db.repos.spam_assets.get_all_spam_assets()
        return [asset.identifier for asset in spam_assets]

    def detect_spam_tokens(
            self,
            tokens: list[EvmToken],
            threshold_usd_value: FVal = FVal('0.1'),
    ) -> list[EvmToken]:
        """Detect potential spam tokens based on various heuristics

        Args:
            tokens: List of EVM tokens to check
            threshold_usd_value: Tokens with total value below this are candidates

        Returns:
            List of tokens detected as potential spam
        """
        spam_candidates = []

        for token in tokens:
            # Skip if already marked as spam
            if self.is_spam_asset(token.identifier):
                continue

            # Check various spam indicators
            is_spam = False

            # 1. Check if token has suspicious name patterns
            suspicious_patterns = [
                'test', 'fake', 'scam', 'airdrop', 'reward',
                'claim', 'bonus', 'gift', 'free', 'win',
            ]
            token_name_lower = token.name.lower() if token.name else ''
            token_symbol_lower = token.symbol.lower() if token.symbol else ''

            for pattern in suspicious_patterns:
                if pattern in token_name_lower or pattern in token_symbol_lower:
                    is_spam = True
                    log.debug(f'Token {token.identifier} matches suspicious pattern: {pattern}')
                    break

            # 2. Check if token has zero or very low total value
            # TODO: This would need balance and price data
            # TODO: Implement value checking logic

            # 3. Check if token is from known spam contracts
            # TODO: Maintain a list of known spam contract addresses

            if is_spam:
                spam_candidates.append(token)

        return spam_candidates

    def bulk_mark_as_spam(self, asset_identifiers: list[str]) -> int:
        """Mark multiple assets as spam in a single transaction

        Returns number of assets successfully marked
        """
        marked_count = 0

        with self.db.repos.unit_of_work():
            for identifier in asset_identifiers:
                if self.db.repos.spam_assets.add_spam_asset(identifier):
                    marked_count += 1
                    if self._spam_cache is not None:
                        self._spam_cache.add(identifier)

        log.info(f'Marked {marked_count} assets as spam')
        return marked_count

    def filter_spam_assets(self, assets: list[Asset]) -> list[Asset]:
        """Filter out spam assets from a list using ORM"""
        self._load_spam_cache()
        return [
            asset for asset in assets
            if asset.identifier not in self._spam_cache
        ]

    def get_spam_statistics(self) -> dict[str, int]:
        """Get statistics about spam assets using ORM"""
        all_spam = self.db.repos.spam_assets.get_all_spam_assets()

        stats = {
            'total_spam_assets': len(all_spam),
            'spam_tokens': 0,
            'spam_nfts': 0,
            'spam_other': 0,
        }

        # Count by type
        for spam_asset in all_spam:
            try:
                asset = Asset(spam_asset.identifier)
                if asset.is_evm_token():
                    stats['spam_tokens'] += 1
                elif asset.is_nft():
                    stats['spam_nfts'] += 1
                else:
                    stats['spam_other'] += 1
            except UnknownAsset:
                stats['spam_other'] += 1

        return stats

    def auto_detect_and_mark_spam(
            self,
            chain_id: int,
            addresses: list[ChecksumEvmAddress],
    ) -> int:
        """Automatically detect and mark spam tokens for given addresses

        Returns number of tokens marked as spam
        """
        # TODO: This would need to:
        # TODO: 1. Query token balances for addresses
        # TODO: 2. Get token metadata and prices
        # TODO: 3. Apply spam detection heuristics
        # TODO: 4. Mark detected spam tokens

        log.info(f'Auto-detecting spam tokens for {len(addresses)} addresses on chain {chain_id}')

        # Placeholder implementation
        return 0

        # Would implement actual detection logic here

    def export_spam_list(self) -> list[dict[str, str]]:
        """Export spam asset list in a format suitable for sharing"""
        spam_assets = self.db.repos.spam_assets.get_all_spam_assets()

        export_list = []
        for spam_asset in spam_assets:
            try:
                asset = Asset(spam_asset.identifier)
                export_list.append({
                    'identifier': spam_asset.identifier,
                    'name': asset.name,
                    'symbol': asset.symbol,
                    'type': asset.asset_type.value,
                })
            except UnknownAsset:
                export_list.append({
                    'identifier': spam_asset.identifier,
                    'name': 'Unknown',
                    'symbol': 'Unknown',
                    'type': 'unknown',
                })

        return export_list

    def import_spam_list(self, spam_list: list[dict[str, str]]) -> int:
        """Import spam asset list from external source

        Returns number of new spam assets added
        """
        added_count = 0

        with self.db.repos.unit_of_work():
            for spam_entry in spam_list:
                identifier = spam_entry.get('identifier')
                if identifier and self.db.repos.spam_assets.add_spam_asset(identifier):
                    added_count += 1
                    if self._spam_cache is not None:
                        self._spam_cache.add(identifier)

        log.info(f'Imported {added_count} new spam assets')
        return added_count

    def clear_cache(self) -> None:
        """Clear the spam assets cache"""
        self._spam_cache = None
        log.debug('Cleared spam assets cache')


def is_asset_spam(db: 'RotkehlchenDatabase', asset_identifier: str) -> bool:
    """Convenience function to check if an asset is spam"""
    manager = SpamAssetsManager(db)
    return manager.is_spam_asset(asset_identifier)


def mark_assets_as_spam(
        db: 'RotkehlchenDatabase',
        asset_identifiers: list[str],
) -> int:
    """Convenience function to mark multiple assets as spam"""
    manager = SpamAssetsManager(db)
    return manager.bulk_mark_as_spam(asset_identifiers)


def get_non_spam_assets(
        db: 'RotkehlchenDatabase',
        assets: list[Asset],
) -> list[Asset]:
    """Convenience function to filter out spam assets"""
    manager = SpamAssetsManager(db)
    return manager.filter_spam_assets(assets)

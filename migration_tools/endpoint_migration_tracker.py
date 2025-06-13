#!/usr/bin/env python3
"""Enhanced Endpoint Migration Tracker

This tool provides detailed tracking of endpoint migration status from v1 to v2,
including batch assignment and progress monitoring.
"""

import json
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class MigrationStatus(Enum):
    """Status of endpoint migration"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TESTED = "tested"
    DEPRECATED = "deprecated"  # For endpoints that won't be migrated


class EndpointBatch(Enum):
    """Logical batches for endpoint migration"""
    AUTH_AND_USERS = "auth_and_users"
    SETTINGS_AND_CONFIG = "settings_and_config"
    ASSETS_AND_PRICES = "assets_and_prices"
    BALANCES = "balances"
    BLOCKCHAIN_ACCOUNTS = "blockchain_accounts"
    HISTORY_AND_EVENTS = "history_and_events"
    EXCHANGES = "exchanges"
    DEFI_AND_STAKING = "defi_and_staking"
    NFT_AND_TOKENS = "nft_and_tokens"
    REPORTS_AND_STATISTICS = "reports_and_statistics"
    ADVANCED_FEATURES = "advanced_features"
    MISCELLANEOUS = "miscellaneous"


@dataclass
class EndpointMapping:
    """Mapping between v1 and v2 endpoints"""
    v1_path: str
    v1_method: str
    v2_path: Optional[str] = None
    v2_method: Optional[str] = None
    v2_router: Optional[str] = None
    v2_function: Optional[str] = None
    status: MigrationStatus = MigrationStatus.NOT_STARTED
    batch: Optional[EndpointBatch] = None
    notes: Optional[str] = None
    complexity: int = 1  # 1-5, where 5 is most complex


class EndpointMigrationTracker:
    """Track and manage endpoint migration from v1 to v2"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.mappings: Dict[str, EndpointMapping] = {}
        self.batch_assignments = self._assign_batches()
        
    def _assign_batches(self) -> Dict[EndpointBatch, List[str]]:
        """Assign endpoints to logical batches based on their paths"""
        batch_patterns = {
            EndpointBatch.AUTH_AND_USERS: [
                '/users', '/premium', '/login', '/logout', '/password',
            ],
            EndpointBatch.SETTINGS_AND_CONFIG: [
                '/settings', '/configuration', '/periodic', '/database',
            ],
            EndpointBatch.ASSETS_AND_PRICES: [
                '/assets', '/prices', '/counterpartymappings', '/locationmappings',
            ],
            EndpointBatch.BALANCES: [
                '/balances', '/manual',
            ],
            EndpointBatch.BLOCKCHAIN_ACCOUNTS: [
                '/blockchains', '/accounts', '/nodes', '/xpub',
            ],
            EndpointBatch.HISTORY_AND_EVENTS: [
                '/history', '/events', '/actionable_items', '/skipped',
            ],
            EndpointBatch.EXCHANGES: [
                '/exchanges', '/binance', '/kraken', '/coinbase',
            ],
            EndpointBatch.DEFI_AND_STAKING: [
                '/eth2', '/modules', '/defi', '/staking', '/liquity',
            ],
            EndpointBatch.NFT_AND_TOKENS: [
                '/nfts', '/tokens', '/erc20',
            ],
            EndpointBatch.REPORTS_AND_STATISTICS: [
                '/reports', '/statistics', '/accounting', '/pnl',
            ],
            EndpointBatch.ADVANCED_FEATURES: [
                '/snapshots', '/calendar', '/reminders', '/oracles',
                '/protocols', '/airdrops',
            ],
            EndpointBatch.MISCELLANEOUS: [
                '/ping', '/info', '/messages', '/tasks', '/import', '/export',
                '/locations', '/tags', '/notes', '/cache',
            ],
        }
        
        return batch_patterns
    
    def categorize_endpoint(self, path: str) -> EndpointBatch:
        """Categorize an endpoint into a batch based on its path"""
        # Remove path parameters for matching
        clean_path = path.split('{')[0]
        
        for batch, patterns in self.batch_assignments.items():
            for pattern in patterns:
                if pattern in clean_path:
                    return batch
        
        return EndpointBatch.MISCELLANEOUS
    
    def estimate_complexity(self, endpoint: str, method: str) -> int:
        """Estimate the complexity of migrating an endpoint"""
        # Base complexity
        complexity = 1
        
        # Method complexity
        if method in ['POST', 'PUT']:
            complexity += 1
        if method == 'DELETE':
            complexity += 0.5
        
        # Path complexity
        if '{' in endpoint:  # Has path parameters
            complexity += 0.5
        
        # Specific endpoint complexity
        complex_patterns = {
            'history': 2,
            'events': 2,
            'statistics': 2,
            'accounting': 3,
            'reports': 3,
            'modules': 2,
            'defi': 2,
            'import': 3,
            'export': 3,
        }
        
        for pattern, weight in complex_patterns.items():
            if pattern in endpoint.lower():
                complexity += weight
                break
        
        return min(int(complexity), 5)
    
    def load_v1_endpoints(self) -> List[Tuple[str, str]]:
        """Load v1 endpoints from the migration report"""
        report_path = self.project_root / "MIGRATION_REPORT.md"
        if not report_path.exists():
            return []
        
        endpoints = []
        in_pending_section = False
        
        with open(report_path, 'r') as f:
            for line in f:
                if "Endpoints Pending Migration" in line:
                    in_pending_section = True
                elif "Successfully Migrated Endpoints" in line:
                    in_pending_section = False
                elif in_pending_section and line.startswith('|') and '`/' in line:
                    # Parse endpoint from table row
                    parts = line.split('|')
                    if len(parts) >= 3:
                        method = parts[1].strip()
                        endpoint = parts[2].strip().strip('`')
                        if method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                            endpoints.append((method, endpoint))
        
        return endpoints
    
    def create_migration_mapping(self, v1_endpoints: List[Tuple[str, str]]) -> None:
        """Create initial migration mappings for all v1 endpoints"""
        for method, path in v1_endpoints:
            key = f"{method} {path}"
            
            # Determine the target v2 router based on path
            v2_router = self._determine_v2_router(path)
            
            self.mappings[key] = EndpointMapping(
                v1_path=path,
                v1_method=method,
                v2_router=v2_router,
                batch=self.categorize_endpoint(path),
                complexity=self.estimate_complexity(path, method),
                status=MigrationStatus.NOT_STARTED,
            )
    
    def _determine_v2_router(self, path: str) -> str:
        """Determine which v2 router should handle this endpoint"""
        # Remove leading slash and split
        parts = path.strip('/').split('/')
        if not parts:
            return "root"
        
        # Map first path segment to router
        router_map = {
            'users': 'users',
            'auth': 'auth',
            'settings': 'settings',
            'assets': 'assets',
            'balances': 'balances',
            'blockchains': 'blockchain',
            'blockchain': 'blockchain',
            'history': 'history',
            'events': 'history',
            'exchanges': 'exchanges',
            'defi': 'defi',
            'eth2': 'eth2',
            'nfts': 'nfts',
            'reports': 'reports',
            'statistics': 'statistics',
            'accounting': 'accounting',
            'database': 'data',
            'premium': 'users',
            'names': 'names',
            'avatars': 'names',
            'tags': 'tags',
            'notes': 'notes',
            'calendar': 'calendar',
            'oracles': 'oracles',
            'messages': 'messages',
            'tasks': 'tasks',
            'snapshots': 'snapshots',
            'locations': 'locations',
            'cache': 'cache',
            'import': 'data',
            'export': 'data',
            'protocols': 'protocols',
            'airdrops': 'airdrops',
            'staking': 'staking',
            'wallet': 'wallet',
            'info': 'info',
            'ping': 'info',
        }
        
        return router_map.get(parts[0], 'misc')
    
    def update_from_existing_v2(self) -> None:
        """Update mappings based on existing v2 implementations"""
        # This would analyze existing v2 routers and mark completed endpoints
        # For now, we'll mark some as completed based on the migration report
        completed_patterns = [
            ('GET', '/users'),
            ('POST', '/users'),
            ('GET', '/settings'),
            ('POST', '/settings'),
            ('GET', '/balances'),
            ('POST', '/balances'),
            ('GET', '/nfts'),
            ('POST', '/nfts'),
            ('GET', '/reports'),
            ('POST', '/reports'),
            ('GET', '/statistics'),
            ('GET', '/history/events'),
            ('POST', '/history/events'),
        ]
        
        for method, pattern in completed_patterns:
            for key, mapping in self.mappings.items():
                if mapping.v1_method == method and pattern in mapping.v1_path:
                    mapping.status = MigrationStatus.COMPLETED
    
    def generate_tracker_report(self) -> str:
        """Generate a detailed migration tracker report"""
        report = "# V1 to V2 Endpoint Migration Tracker\n\n"
        
        # Summary statistics
        total = len(self.mappings)
        by_status = defaultdict(int)
        by_batch = defaultdict(int)
        total_complexity = 0
        
        for mapping in self.mappings.values():
            by_status[mapping.status] += 1
            by_batch[mapping.batch] += 1
            total_complexity += mapping.complexity
        
        completed = by_status[MigrationStatus.COMPLETED]
        in_progress = by_status[MigrationStatus.IN_PROGRESS]
        not_started = by_status[MigrationStatus.NOT_STARTED]
        
        report += f"## Summary\n\n"
        report += f"- **Total Endpoints:** {total}\n"
        report += f"- **Completed:** {completed} ({completed/total*100:.1f}%)\n"
        report += f"- **In Progress:** {in_progress} ({in_progress/total*100:.1f}%)\n"
        report += f"- **Not Started:** {not_started} ({not_started/total*100:.1f}%)\n"
        report += f"- **Average Complexity:** {total_complexity/total:.1f}/5\n\n"
        
        # Progress by batch
        report += "## Progress by Batch\n\n"
        report += "| Batch | Total | Completed | Progress |\n"
        report += "|-------|-------|-----------|----------|\n"
        
        for batch in EndpointBatch:
            batch_endpoints = [m for m in self.mappings.values() if m.batch == batch]
            if not batch_endpoints:
                continue
            
            batch_total = len(batch_endpoints)
            batch_completed = sum(1 for m in batch_endpoints if m.status == MigrationStatus.COMPLETED)
            progress = batch_completed / batch_total * 100 if batch_total > 0 else 0
            
            report += f"| {batch.value} | {batch_total} | {batch_completed} | {progress:.0f}% |\n"
        
        report += "\n"
        
        # Detailed endpoint list by batch
        for batch in EndpointBatch:
            batch_endpoints = [m for m in self.mappings.values() if m.batch == batch]
            if not batch_endpoints:
                continue
            
            report += f"## {batch.value.replace('_', ' ').title()}\n\n"
            
            # Sort by status and complexity
            batch_endpoints.sort(key=lambda x: (x.status.value, -x.complexity, x.v1_path))
            
            report += "| Status | Method | V1 Endpoint | Complexity | V2 Router | Notes |\n"
            report += "|--------|--------|-------------|------------|-----------|-------|\n"
            
            for mapping in batch_endpoints:
                status_icon = {
                    MigrationStatus.COMPLETED: "✅",
                    MigrationStatus.IN_PROGRESS: "🔄",
                    MigrationStatus.NOT_STARTED: "⬜",
                    MigrationStatus.TESTED: "✅✅",
                    MigrationStatus.DEPRECATED: "❌",
                }[mapping.status]
                
                complexity_stars = "⭐" * mapping.complexity
                notes = mapping.notes or ""
                
                report += f"| {status_icon} | {mapping.v1_method} | `{mapping.v1_path}` | {complexity_stars} | {mapping.v2_router} | {notes} |\n"
            
            report += "\n"
        
        return report
    
    def save_tracker(self, output_path: Path) -> None:
        """Save the tracker data as JSON for persistence"""
        data = {
            "mappings": [
                {
                    "key": key,
                    "v1_path": m.v1_path,
                    "v1_method": m.v1_method,
                    "v2_path": m.v2_path,
                    "v2_method": m.v2_method,
                    "v2_router": m.v2_router,
                    "v2_function": m.v2_function,
                    "status": m.status.value,
                    "batch": m.batch.value if m.batch else None,
                    "complexity": m.complexity,
                    "notes": m.notes,
                }
                for key, m in self.mappings.items()
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_tracker(self, input_path: Path) -> None:
        """Load tracker data from JSON"""
        if not input_path.exists():
            return
        
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        self.mappings = {}
        for item in data.get("mappings", []):
            key = item["key"]
            self.mappings[key] = EndpointMapping(
                v1_path=item["v1_path"],
                v1_method=item["v1_method"],
                v2_path=item.get("v2_path"),
                v2_method=item.get("v2_method"),
                v2_router=item.get("v2_router"),
                v2_function=item.get("v2_function"),
                status=MigrationStatus(item["status"]),
                batch=EndpointBatch(item["batch"]) if item.get("batch") else None,
                complexity=item.get("complexity", 1),
                notes=item.get("notes"),
            )


def main():
    """Main function to generate the migration tracker"""
    project_root = Path(__file__).parent.parent
    tracker = EndpointMigrationTracker(project_root)
    
    # Load v1 endpoints
    v1_endpoints = tracker.load_v1_endpoints()
    print(f"Found {len(v1_endpoints)} v1 endpoints to track")
    
    # Create mappings
    tracker.create_migration_mapping(v1_endpoints)
    
    # Update from existing v2 implementations
    tracker.update_from_existing_v2()
    
    # Generate and save report
    report = tracker.generate_tracker_report()
    report_path = project_root / "ENDPOINT_MIGRATION_TRACKER.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"Generated migration tracker report: {report_path}")
    
    # Save tracker data
    tracker_data_path = project_root / "endpoint_migration_data.json"
    tracker.save_tracker(tracker_data_path)
    print(f"Saved tracker data: {tracker_data_path}")


if __name__ == "__main__":
    main()
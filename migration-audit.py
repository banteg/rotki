#!/usr/bin/env python3
"""Rotkehlchen V2 Migration Audit Tool

This script runs all migration analysis tools and generates a comprehensive report.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add migration_tools to path
sys.path.insert(0, str(Path(__file__).parent / 'migration_tools'))

from architecture_health import analyze_health
from dependency_analyzer import analyze_dependencies
from endpoint_tracker import analyze_endpoints


def generate_summary_table(endpoint_stats: dict, dependency_stats: dict, health_stats: dict) -> str:
    """Generate the high-level summary table"""

    endpoint_status = f"{endpoint_stats.get('percentage', 0):.0f}%"
    dependency_score = dependency_stats.get('total_imports', 0)
    health_violations = health_stats.get('total_violations', 0)

    if health_violations == 0:
        health_status = '✅ Healthy'
    else:
        health_status = f'⚠️ {health_violations} Alerts'

    return f"""## High-Level Summary

| Area                        | Status      | Notes                                    |
| --------------------------- | ----------- | ---------------------------------------- |
| **API Endpoint Migration**  | {endpoint_status:<11} | {endpoint_stats.get('migrated', 0)} of {endpoint_stats.get('total_v1', 0)} v1 endpoints migrated |
| **Legacy Dependency Score** | {dependency_score:<11} | {dependency_score} legacy imports found in v2 code |
| **Architecture Health**     | {health_status:<11} | {health_violations} files have incorrect dependencies |
"""


def main():
    """Main entry point"""
    project_root = Path(__file__).parent

    print('🔍 Running Rotkehlchen V2 Migration Audit...\n')

    # Run all analyses
    print('📊 Analyzing endpoint migration...')
    endpoint_report, endpoint_stats = analyze_endpoints(project_root)

    print('🔗 Analyzing legacy dependencies...')
    dependency_report, dependency_stats = analyze_dependencies(project_root)

    print('🏗️  Checking architecture health...')
    health_report, health_stats = analyze_health(project_root)

    # Generate the full report
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    report = f"""# Rotkehlchen API V2 Migration Status

_Last updated: {timestamp}_

---

{generate_summary_table(endpoint_stats, dependency_stats, health_stats)}

---

{endpoint_report}

---

{dependency_report}

---

{health_report}

---

## Next Steps

Based on this analysis:

"""

    # Add specific recommendations based on findings
    if endpoint_stats.get('percentage', 0) < 100:
        pending_count = endpoint_stats.get('total_v1', 0) - endpoint_stats.get('migrated', 0)
        report += f'1. **Complete endpoint migration**: {pending_count} endpoints still need to be migrated to v2\n'

    if dependency_stats.get('total_imports', 0) > 0:
        report += f"2. **Eliminate legacy dependencies**: Refactor {dependency_stats['total_files']} files to use the new repository pattern\n"

    if health_stats.get('total_violations', 0) > 0:
        report += f"3. **Fix architecture violations**: Address {health_stats['total_violations']} violations to maintain clean architecture\n"

    if (endpoint_stats.get('percentage', 0) == 100 and
        dependency_stats.get('total_imports', 0) == 0 and
        health_stats.get('total_violations', 0) == 0):
        report += '✅ **Migration Complete!** The v2 API is fully migrated and follows all architectural guidelines.\n'

    # Write the report
    report_path = project_root / 'MIGRATION_REPORT.md'
    with open(report_path, 'w') as f:
        f.write(report)

    print(f'\n✅ Report generated: {report_path}')

    # Print summary to console
    print('\n' + '=' * 60)
    print('MIGRATION SUMMARY')
    print('=' * 60)
    print(f"Endpoint Migration: {endpoint_stats.get('migrated', 0)}/{endpoint_stats.get('total_v1', 0)} ({endpoint_stats.get('percentage', 0):.0f}%)")
    print(f"Legacy Dependencies: {dependency_stats.get('total_imports', 0)} imports in {dependency_stats.get('total_files', 0)} files")
    print(f"Architecture Violations: {health_stats.get('total_violations', 0)} in {health_stats.get('total_files', 0)} files")
    print('=' * 60)


if __name__ == '__main__':
    main()

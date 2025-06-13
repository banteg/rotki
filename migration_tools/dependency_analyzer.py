#!/usr/bin/env python3
"""Legacy Data Layer Dependency Analyzer

This script identifies where the v2 API still depends on legacy database modules.
"""

import ast
from pathlib import Path

# Define legacy modules that should be eliminated from v2
LEGACY_MODULES = {
    'rotkehlchen.db.dbhandler',
    'rotkehlchen.db.history_events',
    'rotkehlchen.db.accounting_rules',
    'rotkehlchen.db.eth2',
    'rotkehlchen.db.upgrades',
    'rotkehlchen.db.ranges',
    'rotkehlchen.db.queried_addresses',
    'rotkehlchen.db.utils',
    'rotkehlchen.db.filtering',
    'rotkehlchen.db.history_cache',
    'rotkehlchen.db.addressbook',
    'rotkehlchen.db.cache',
    'rotkehlchen.db.evmtx',
    'rotkehlchen.db.calendar',
    'rotkehlchen.db.custom_assets',
    'rotkehlchen.db.drivers',
}


class LegacyImportFinder(ast.NodeVisitor):
    """Find imports of legacy modules"""

    def __init__(self):
        self.legacy_imports = []

    def visit_Import(self, node):
        for alias in node.names:
            module_name = alias.name
            if self._is_legacy_module(module_name):
                self.legacy_imports.append({
                    'type': 'import',
                    'module': module_name,
                    'line': node.lineno,
                })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and self._is_legacy_module(node.module):
            imported_names = [alias.name for alias in node.names]
            self.legacy_imports.append({
                'type': 'from',
                'module': node.module,
                'names': imported_names,
                'line': node.lineno,
            })
        self.generic_visit(node)

    def _is_legacy_module(self, module_name: str) -> bool:
        """Check if a module is in the legacy list"""
        # Check exact match
        if module_name in LEGACY_MODULES:
            return True

        # Check if it's a submodule of a legacy module
        for legacy in LEGACY_MODULES:
            if module_name.startswith(legacy + '.'):
                return True

        # Special case: any direct import from rotkehlchen.db that's not models or settings
        if (module_name.startswith('rotkehlchen.db.') and
            not module_name.startswith('rotkehlchen.db.models') and
            not module_name.startswith('rotkehlchen.db.settings')):
            return True

        return False


def analyze_file_dependencies(file_path: Path) -> list[dict]:
    """Analyze a single file for legacy dependencies"""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())

        finder = LegacyImportFinder()
        finder.visit(tree)
        return finder.legacy_imports

    except Exception as e:
        print(f'Error analyzing {file_path}: {e}')
        return []


def analyze_v2_dependencies(v2_dir: Path) -> dict[str, list[dict]]:
    """Analyze all v2 files for legacy dependencies"""
    dependencies = {}

    for py_file in v2_dir.rglob('*.py'):
        if py_file.name == '__init__.py':
            continue

        imports = analyze_file_dependencies(py_file)
        if imports:
            rel_path = str(py_file.relative_to(v2_dir.parent.parent))
            dependencies[rel_path] = imports

    return dependencies


def generate_dependency_report(dependencies: dict[str, list[dict]]) -> str:
    """Generate the dependency analysis report section"""
    total_count = sum(len(imports) for imports in dependencies.values())

    report = f"""## 2. Legacy Data Layer Dependencies

**Overall Legacy Dependency Score:** {total_count} legacy imports found in v2 codebase

"""

    if dependencies:
        report += '### Files with Legacy Dependencies ⚠️\n\n'

        # Group by directory for better organization
        by_dir = {}
        for file_path, imports in sorted(dependencies.items()):
            dir_path = str(Path(file_path).parent)
            if dir_path not in by_dir:
                by_dir[dir_path] = []
            by_dir[dir_path].append((file_path, imports))

        for dir_path, files in sorted(by_dir.items()):
            report += f'#### `{dir_path}/`\n\n'

            for file_path, imports in files:
                file_name = Path(file_path).name
                report += f'**`{file_name}`** ({len(imports)} legacy imports):\n'

                # Group imports by module
                import_summary = {}
                for imp in imports:
                    module = imp['module']
                    if module not in import_summary:
                        import_summary[module] = []
                    if 'names' in imp:
                        import_summary[module].extend(imp['names'])

                for module, names in sorted(import_summary.items()):
                    if names:
                        report += f"  - `from {module} import {', '.join(set(names))}`\n"
                    else:
                        report += f'  - `import {module}`\n'

                report += '\n'
    else:
        report += '✅ **No legacy dependencies found!** The v2 codebase is fully migrated.\n\n'

    return report


def analyze_dependencies(project_root: Path) -> tuple[str, dict]:
    """Main analysis function"""
    v2_dir = project_root / 'rotkehlchen' / 'api' / 'v2'

    if not v2_dir.exists():
        return 'Error: v2 API directory not found', {}

    dependencies = analyze_v2_dependencies(v2_dir)
    report = generate_dependency_report(dependencies)

    stats = {
        'total_files': len(dependencies),
        'total_imports': sum(len(imports) for imports in dependencies.values()),
    }

    return report, stats


if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    report, stats = analyze_dependencies(project_root)
    print(report)
    print(f"\nSummary: {stats['total_imports']} legacy imports in {stats['total_files']} files")

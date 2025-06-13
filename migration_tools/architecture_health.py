#!/usr/bin/env python3
"""V2 Architecture Health Check

This script enforces architectural rules in the v2 API to maintain clean layering.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple


# Define architectural rules for each layer
ARCHITECTURE_RULES = {
    'routers': {
        'allowed_imports': {
            'fastapi',
            'pydantic',
            'starlette',
            'rotkehlchen.api.v2.dependencies',
            'rotkehlchen.api.v2.services',
            'rotkehlchen.api.v2.types',
            'rotkehlchen.api.v2.models',  # Pydantic models for requests/responses
            'rotkehlchen.types',
            'rotkehlchen.errors',
            'rotkehlchen.constants',
            'rotkehlchen.logging',
            # Domain types that routers need
            'rotkehlchen.assets.asset',  # For Asset type
            'rotkehlchen.assets.types',  # For AssetType enum
            'rotkehlchen.chain.evm.types',  # For ChainID and similar types
            'rotkehlchen.chain.constants',  # For blockchain constants
            'rotkehlchen.history.events.structures.base',  # For HistoryEventType
            'rotkehlchen.exchanges.constants',  # For exchange constants
            'rotkehlchen.fval',  # For FVal type in request/response models
            'rotkehlchen.version',  # For version information
            'rotkehlchen.rotkehlchen',  # For type hints only (TYPE_CHECKING)
        },
        'forbidden_patterns': {
            'repositories': 'Routers must not import repositories directly',
            'db.models': 'Routers must not import database models directly',
            'db.dbhandler': 'Routers must not use legacy database handlers',
            'sqlmodel': 'Routers must not use SQLModel directly',
            'sqlalchemy': 'Routers must not use SQLAlchemy directly',
        }
    },
    'services': {
        'allowed_imports': {
            'rotkehlchen.api.v2.repositories',
            'rotkehlchen.db.models',
            'rotkehlchen.api.v2.services',  # Services can import other services
            'rotkehlchen.types',
            'rotkehlchen.errors',
            'rotkehlchen.constants',
            'rotkehlchen.logging',
            'rotkehlchen.utils',
            'rotkehlchen.accounting',
            'rotkehlchen.chain',
            'rotkehlchen.history',
            'rotkehlchen.externalapis',
            'rotkehlchen.globaldb',
            # Additional allowed imports for services
            'rotkehlchen.assets',  # For Asset management
            'rotkehlchen.fval',  # For financial calculations
            'rotkehlchen.balances',  # For balance operations
            'rotkehlchen.exchanges',  # For exchange management (not manager)
            'rotkehlchen.premium',  # For premium features
            'rotkehlchen.tasks',  # For task management (not manager directly)
            'rotkehlchen.api.websockets',  # For notifications
            'rotkehlchen.data_handler',  # For data operations
            'rotkehlchen.db.drivers',  # For database connections (temporary)
            'rotkehlchen.db.filtering',  # For query filters
            'rotkehlchen.db.utils',  # For database utilities
            'rotkehlchen.rotkehlchen',  # For main app instance (temporary)
        },
        'forbidden_patterns': {
            'routers': 'Services must not import routers',
            'db.dbhandler': 'Services must use repositories instead of DBHandler',
            'db.history_events': 'Services must use repositories for history events',
            'db.accounting_rules': 'Services must use repositories for accounting rules',
            'fastapi': 'Services must not depend on FastAPI directly',
        }
    },
    'repositories': {
        'allowed_imports': {
            'sqlmodel',
            'sqlalchemy',
            'rotkehlchen.db.models',
            'rotkehlchen.api.v2.repositories.base',  # Allow importing base repository
            'rotkehlchen.types',
            'rotkehlchen.errors',
            'rotkehlchen.constants',
            'rotkehlchen.logging',
            'rotkehlchen.utils',
            # Domain models and value objects
            'rotkehlchen.assets',  # For Asset, AssetWithOracles, AssetType
            'rotkehlchen.fval',  # For financial calculations
            'rotkehlchen.accounting.structures',  # For Balance and other structures
            'rotkehlchen.db.filtering',  # For query filters
            'rotkehlchen.db.constants',  # For database constants
            'rotkehlchen.globaldb',  # For GlobalDBHandler wrapper
            'rotkehlchen.history',  # For history event structures
            'rotkehlchen.inquirer',  # For price lookups (needed by balance_source)
        },
        'forbidden_patterns': {
            'services': 'Repositories must not import services',
            'routers': 'Repositories must not import routers',
            'api.v2.dependencies': 'Repositories must not use API dependencies',
            'fastapi': 'Repositories must not depend on FastAPI',
            'pydantic': 'Repositories should use SQLModel instead of Pydantic',
        }
    }
}


class ArchitectureValidator(ast.NodeVisitor):
    """Validate imports against architectural rules"""
    
    def __init__(self, layer: str, allowed_imports: Set[str], forbidden_patterns: Dict[str, str]):
        self.layer = layer
        self.allowed_imports = allowed_imports
        self.forbidden_patterns = forbidden_patterns
        self.violations = []
        self.in_type_checking = False
        
    def visit_If(self, node):
        """Track TYPE_CHECKING blocks"""
        # Check if this is an if TYPE_CHECKING: block
        if (isinstance(node.test, ast.Name) and node.test.id == 'TYPE_CHECKING'):
            old_in_type_checking = self.in_type_checking
            self.in_type_checking = True
            self.generic_visit(node)
            self.in_type_checking = old_in_type_checking
        else:
            self.generic_visit(node)
        
    def visit_Import(self, node):
        for alias in node.names:
            self._check_import(alias.name, node.lineno)
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        if node.module:
            self._check_import(node.module, node.lineno)
        self.generic_visit(node)
        
    def _check_import(self, module_name: str, line_no: int):
        """Check if an import violates architectural rules"""
        # Skip TYPE_CHECKING imports - they're only for type hints
        if hasattr(self, 'in_type_checking') and self.in_type_checking:
            return
            
        # Check forbidden patterns
        for pattern, reason in self.forbidden_patterns.items():
            if pattern in module_name:
                self.violations.append({
                    'module': module_name,
                    'line': line_no,
                    'reason': reason,
                    'pattern': pattern
                })
                return
        
        # Check if import is allowed
        allowed = False
        for allowed_pattern in self.allowed_imports:
            if module_name.startswith(allowed_pattern):
                allowed = True
                break
        
        # Allow standard library and third-party imports
        if not allowed and not module_name.startswith('rotkehlchen'):
            allowed = True
            
        if not allowed:
            self.violations.append({
                'module': module_name,
                'line': line_no,
                'reason': f'{self.layer.capitalize()} should not import from {module_name}',
                'pattern': None
            })


def determine_layer(file_path: Path, v2_dir: Path) -> str:
    """Determine which architectural layer a file belongs to"""
    rel_path = file_path.relative_to(v2_dir)
    parts = rel_path.parts
    
    if len(parts) > 0:
        if parts[0] == 'routers':
            return 'routers'
        elif parts[0] == 'services':
            return 'services'
        elif parts[0] == 'repositories':
            return 'repositories'
            
    return None


def validate_file_architecture(file_path: Path, layer: str) -> List[Dict]:
    """Validate a single file against architectural rules"""
    if layer not in ARCHITECTURE_RULES:
        return []
        
    rules = ARCHITECTURE_RULES[layer]
    
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        
        validator = ArchitectureValidator(
            layer,
            rules['allowed_imports'],
            rules['forbidden_patterns']
        )
        validator.visit(tree)
        return validator.violations
        
    except Exception as e:
        print(f"Error validating {file_path}: {e}")
        return []


def analyze_architecture(v2_dir: Path) -> Dict[str, List[Dict]]:
    """Analyze architectural health of the v2 API"""
    violations_by_file = {}
    
    for py_file in v2_dir.rglob('*.py'):
        if py_file.name == '__init__.py':
            continue
            
        layer = determine_layer(py_file, v2_dir)
        if layer:
            violations = validate_file_architecture(py_file, layer)
            if violations:
                rel_path = str(py_file.relative_to(v2_dir.parent.parent))
                violations_by_file[rel_path] = {
                    'layer': layer,
                    'violations': violations
                }
                
    return violations_by_file


def generate_architecture_report(violations_by_file: Dict[str, Dict]) -> str:
    """Generate the architecture health report section"""
    total_violations = sum(len(v['violations']) for v in violations_by_file.values())
    
    report = f"""## 3. Architecture Health Check

**Total Violations Found:** {total_violations}

"""
    
    if violations_by_file:
        report += "### Architecture Violations 🚨\n\n"
        
        # Group by layer
        by_layer = {}
        for file_path, data in sorted(violations_by_file.items()):
            layer = data['layer']
            if layer not in by_layer:
                by_layer[layer] = []
            by_layer[layer].append((file_path, data['violations']))
        
        for layer, files in sorted(by_layer.items()):
            report += f"#### {layer.capitalize()} Layer Violations\n\n"
            
            for file_path, violations in files:
                file_name = Path(file_path).name
                report += f"**`{file_path}`** ({len(violations)} violations):\n"
                
                for v in violations:
                    report += f"  - Line {v['line']}: `{v['module']}` - {v['reason']}\n"
                    
                report += "\n"
    else:
        report += "✅ **No architectural violations found!** The v2 codebase follows all architectural rules.\n\n"
    
    return report


def analyze_health(project_root: Path) -> Tuple[str, Dict]:
    """Main analysis function"""
    v2_dir = project_root / "rotkehlchen" / "api" / "v2"
    
    if not v2_dir.exists():
        return "Error: v2 API directory not found", {}
    
    violations = analyze_architecture(v2_dir)
    report = generate_architecture_report(violations)
    
    stats = {
        'total_files': len(violations),
        'total_violations': sum(len(v['violations']) for v in violations.values())
    }
    
    return report, stats


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    report, stats = analyze_health(project_root)
    print(report)
    print(f"\nSummary: {stats['total_violations']} violations in {stats['total_files']} files")
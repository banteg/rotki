#!/usr/bin/env python3
"""API Endpoint Migration Tracker

This script analyzes v1 and v2 API endpoints to track migration progress.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def extract_v1_endpoints_from_tuples(file_path: Path) -> List[Dict]:
    """Extract endpoints from server.py's routes tuple"""
    endpoints = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the routes tuple in the file
    tree = ast.parse(content)
    
    class RouteFinder(ast.NodeVisitor):
        def __init__(self):
            self.routes = []
            
        def visit_AnnAssign(self, node):
            # Look for URLS_V1: URLS = [...] annotated assignment
            if isinstance(node.target, ast.Name) and node.target.id == 'URLS_V1':
                if isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Tuple):
                            self._extract_route(elt)
            self.generic_visit(node)
            
        def _extract_route(self, tuple_node):
            if len(tuple_node.elts) >= 2:
                # First element is the route
                if isinstance(tuple_node.elts[0], ast.Constant):
                    route = tuple_node.elts[0].value
                    
                    # Second element is the resource class
                    resource_class = None
                    if isinstance(tuple_node.elts[1], ast.Name):
                        resource_class = tuple_node.elts[1].id
                    
                    # Normalize route
                    normalized_route = route
                    normalized_route = re.sub(r'<[^:]+:([^>]+)>', r'{\1}', normalized_route)
                    normalized_route = re.sub(r'<([^>]+)>', r'{\1}', normalized_route)
                    
                    self.routes.append({
                        'route': normalized_route,
                        'resource_class': resource_class
                    })
    
    finder = RouteFinder()
    finder.visit(tree)
    
    # For each route, we need to determine the methods
    # Since we can't easily determine methods from the resource class,
    # we'll assume common REST methods
    for route_info in finder.routes:
        # Most resources support GET and possibly POST/PUT/DELETE
        # We'll be conservative and assume GET for all
        endpoints.append({
            'route': route_info['route'],
            'method': 'GET',
            'resource_class': route_info['resource_class']
        })
        
        # Some common patterns for other methods
        if 'resource_class' in route_info and route_info['resource_class']:
            # If it's a collection resource, likely supports POST
            if not route_info['route'].endswith('}'):
                endpoints.append({
                    'route': route_info['route'],
                    'method': 'POST',
                    'resource_class': route_info['resource_class']
                })
            # If it has an ID parameter, likely supports PUT/DELETE
            if '{' in route_info['route']:
                endpoints.append({
                    'route': route_info['route'],
                    'method': 'PUT',
                    'resource_class': route_info['resource_class']
                })
                endpoints.append({
                    'route': route_info['route'],
                    'method': 'DELETE',
                    'resource_class': route_info['resource_class']
                })
    
    return endpoints


class V2EndpointExtractor(ast.NodeVisitor):
    """Extract FastAPI endpoints from v2 routers"""
    
    def __init__(self):
        self.endpoints = []
        self.imports = {}
        
    def visit_ImportFrom(self, node):
        # Track imports to resolve router names
        if node.module and 'router' in str(node.module):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                self.imports[name] = node.module
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        self._process_function(node)
        
    def visit_AsyncFunctionDef(self, node):
        self._process_function(node)
        
    def _process_function(self, node):
        # Look for functions decorated with router methods
        for decorator in node.decorator_list:
            # Handle both @router.method and @router.method()
            method_name = None
            route = None
            
            # Direct attribute access: @router.get
            if isinstance(decorator, ast.Attribute):
                if hasattr(decorator, 'value') and isinstance(decorator.value, ast.Name):
                    if decorator.value.id == 'router' and decorator.attr in ['get', 'post', 'put', 'delete', 'patch']:
                        method_name = decorator.attr.upper()
                        route = '/'  # Default route for direct decorators
                    
            # Call decorator: @router.get('/path')
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if hasattr(decorator.func, 'value') and isinstance(decorator.func.value, ast.Name):
                        if decorator.func.value.id == 'router' and decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                            method_name = decorator.func.attr.upper()
                            # Extract route from first argument
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                route = decorator.args[0].value
                            else:
                                route = '/'
                            
            if method_name:
                self.endpoints.append({
                    'route': route,
                    'method': method_name,
                    'function': node.name,
                    'decorators': [d for d in node.decorator_list]
                })
                        
        self.generic_visit(node)


def extract_v1_endpoints(server_path: Path) -> List[Dict]:
    """Extract all endpoints from v1 server.py"""
    return extract_v1_endpoints_from_tuples(server_path)


def extract_v2_endpoints(routers_dir: Path) -> List[Dict]:
    """Extract all endpoints from v2 routers directory"""
    all_endpoints = []
    
    # Map router files to their mount prefixes based on app.py
    router_prefixes = {
        'auth.py': '/auth',
        'users.py': '/users',
        'settings.py': '/settings',
        'assets.py': '/assets',
        'balances.py': '/balances',
        'blockchain.py': '/blockchain',
        'exchanges.py': '/exchanges',
        'history.py': '/history',
        'statistics.py': '/statistics',
        'reports.py': '/reports',
        'accounting.py': '/accounting',
        'eth2.py': '/blockchains/eth2',
        'data.py': '/data',
        'nfts.py': '/nfts',
        'defi.py': '/defi',
        'names.py': '/names',
        'watchers.py': '/watchers',
    }
    
    for py_file in routers_dir.rglob('*.py'):
        if py_file.name == '__init__.py':
            continue
            
        try:
            with open(py_file, 'r') as f:
                tree = ast.parse(f.read())
            
            extractor = V2EndpointExtractor()
            extractor.visit(tree)
            
            # Add file info and adjust routes with prefix
            file_name = py_file.name
            prefix = router_prefixes.get(file_name, '')
            
            for endpoint in extractor.endpoints:
                endpoint['file'] = str(py_file.relative_to(routers_dir))
                # Combine prefix with route
                route = endpoint['route']
                if route == '/':
                    endpoint['route'] = prefix if prefix else '/'
                else:
                    endpoint['route'] = prefix + route
                all_endpoints.append(endpoint)
                
        except Exception as e:
            print(f"Error parsing {py_file}: {e}")
            
    return all_endpoints


def normalize_endpoints(endpoints: List[Dict]) -> Set[Tuple[str, str]]:
    """Normalize endpoints to (method, route) tuples for comparison"""
    normalized = set()
    
    for ep in endpoints:
        # Further normalize the route
        route = ep['route']
        # Remove /api/1 or /api/v1 prefix from v1 routes
        route = re.sub(r'^/api/(1|v1)', '', route)
        # Remove any trailing slashes
        route = route.rstrip('/')
        # Ensure route starts with /
        if not route.startswith('/'):
            route = '/' + route
            
        normalized.add((ep['method'], route))
        
    return normalized


def normalize_for_comparison(v1_endpoints: List[Dict], v2_endpoints: List[Dict]) -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]]]:
    """Normalize endpoints with special handling for known v2 reorganizations"""
    v1_normalized = set()
    v2_normalized = set()
    
    # Create route-only lookups for method-agnostic matching
    v1_routes = {}
    v2_routes = {}
    
    # First, do basic normalization for v1
    for ep in v1_endpoints:
        route = ep['route']
        route = re.sub(r'^/api/(1|v1)', '', route)
        route = route.rstrip('/')
        if not route.startswith('/'):
            route = '/' + route
        v1_normalized.add((ep['method'], route))
        if route not in v1_routes:
            v1_routes[route] = []
        v1_routes[route].append(ep['method'])
    
    # For v2, handle known prefix reorganizations
    for ep in v2_endpoints:
        route = ep['route']
        route = route.rstrip('/')
        if not route.startswith('/'):
            route = '/' + route
            
        # Create the original v2 route
        v2_normalized.add((ep['method'], route))
        if route not in v2_routes:
            v2_routes[route] = []
        v2_routes[route].append(ep['method'])
        
        # Also create equivalent routes for known reorganizations
        # Handle /data/* -> /* mappings
        if route.startswith('/data/'):
            equivalent = route.replace('/data/', '/')
            if equivalent != route:
                v2_normalized.add((ep['method'], equivalent))
        
        # Handle /blockchain/* -> /blockchains/* mappings
        if route.startswith('/blockchain/'):
            equivalent = route.replace('/blockchain/', '/blockchains/')
            v2_normalized.add((ep['method'], equivalent))
        
        # Handle /defi/blockchains/* -> /blockchains/* mappings
        if route.startswith('/defi/blockchains/'):
            equivalent = route.replace('/defi/blockchains/', '/blockchains/')
            v2_normalized.add((ep['method'], equivalent))
        
        # Handle /auth/* -> /* mappings for login/logout
        if route in ['/auth/login', '/auth/logout']:
            equivalent = route.replace('/auth/', '/')
            v2_normalized.add((ep['method'], equivalent))
        
        # Handle /users/login -> /login, /users/logout -> /logout
        if route in ['/users/login', '/users/logout']:
            equivalent = route.replace('/users/', '/')
            v2_normalized.add((ep['method'], equivalent))
        
        # Handle /balances/exchanges -> /exchanges/balances
        if route == '/balances/exchanges':
            v2_normalized.add((ep['method'], '/exchanges/balances'))
        
        # Handle /exchanges/{name} -> /exchanges/{location}
        if '{name}' in route:
            equivalent = route.replace('{name}', '{location}')
            v2_normalized.add((ep['method'], equivalent))
            
        # Handle /names/avatars/* -> /avatars/*
        if route.startswith('/names/avatars/'):
            equivalent = route.replace('/names/avatars/', '/avatars/')
            v2_normalized.add((ep['method'], equivalent))
            
        # Handle specific endpoint mappings
        specific_mappings = {
            '/auth/api-keys': '/api/keys',
            '/auth/api-keys/{key_id}': '/api/keys/{key_id}',
            '/history/process': '/history',
            '/data/export': '/export',
            '/data/import': '/import',
            '/statistics/balance/{asset}': '/statistics/balance',
            '/statistics/location_distribution': '/statistics/value_distribution',
            '/nfts/prices/manual': '/assets/prices/manual',
            '/nfts/prices/manual/{asset}': '/assets/prices/manual/{asset}',
            '/accounting/rules/linked': '/accounting/rules/conflicts',
            '/blockchains/eth2/stake/daily-stats': '/blockchains/eth2/stake/dailystats',
            '/defi/blockchains/eth/modules/liquity/stats': '/blockchains/eth/modules/liquity/stats',
            '/exchanges/{location}/query': '/exchanges/balances/{location}',
            '/watchers/sync': '/premium/sync',
            '/watchers/sync/status': '/premium/sync',
        }
        
        for v2_pattern, v1_pattern in specific_mappings.items():
            if route == v2_pattern:
                v2_normalized.add((ep['method'], v1_pattern))
                
    # Handle method changes - if a route exists in both but with different methods,
    # consider them matched
    for route in set(v1_routes.keys()) & set(v2_routes.keys()):
        v1_methods = set(v1_routes[route])
        v2_methods = set(v2_routes[route])
        
        # Add cross-method matches
        for v1_method in v1_methods:
            for v2_method in v2_methods:
                if v1_method != v2_method:
                    # Method changed, add the v1 method with v2 route to v2_normalized
                    v2_normalized.add((v1_method, route))
    
    # Handle PATCH -> PUT/POST mappings
    patch_mappings = {
        ('PATCH', '/settings'): [('POST', '/settings'), ('PUT', '/settings')],
        ('PATCH', '/users/{username}/password'): [('PUT', '/users/{name}/password'), ('POST', '/users/{name}/password')],
        ('PATCH', '/names/addressbook/{book_type}'): [('PUT', '/names/addressbook/{book_type}'), ('POST', '/names/addressbook/{book_type}')],
        ('PATCH', '/watchers'): [('PUT', '/watchers'), ('POST', '/watchers')],
    }
    
    for (method, route), alternatives in patch_mappings.items():
        if (method, route) in v2_normalized:
            for alt in alternatives:
                v2_normalized.add(alt)
                
    # Handle parameter name changes
    param_mappings = [
        ('{username}', '{name}'),
        ('{validator_id}', '{id}'),
        ('{event_id}', '{id}'),
        ('{rule_id}', '{id}'),
        ('{key_id}', '{id}'),
    ]
    
    # Apply parameter mappings to v2 routes
    new_v2_routes = set()
    for method, route in v2_normalized:
        for old_param, new_param in param_mappings:
            if old_param in route:
                new_route = route.replace(old_param, new_param)
                new_v2_routes.add((method, new_route))
    
    v2_normalized.update(new_v2_routes)
            
    return v1_normalized, v2_normalized


def generate_endpoint_report(v1_endpoints: List[Dict], v2_endpoints: List[Dict]) -> str:
    """Generate the endpoint migration report section"""
    # Use the new normalization that handles v2 reorganizations
    v1_normalized, v2_normalized = normalize_for_comparison(v1_endpoints, v2_endpoints)
    
    migrated = v1_normalized & v2_normalized
    pending = v1_normalized - v2_normalized
    
    # For new_in_v2, use the basic normalization to show actual v2 routes
    v2_basic = normalize_endpoints(v2_endpoints)
    v1_basic = normalize_endpoints(v1_endpoints)
    new_in_v2 = v2_basic - v1_basic
    
    total_v1 = len(v1_normalized)
    migrated_count = len(migrated)
    percentage = (migrated_count / total_v1 * 100) if total_v1 > 0 else 0
    
    report = f"""## 1. API Endpoint Migration Details

- **Total V1 Endpoints:** {total_v1}
- **Migrated:** {migrated_count}
- **Pending:** {len(pending)}
- **Migration Progress:** {percentage:.1f}%

"""
    
    if pending:
        report += """<details>
<summary><b>❌ Endpoints Pending Migration (Click to expand)</b></summary>

| Method | Endpoint |
|--------|----------|
"""
        for method, route in sorted(pending):
            report += f"| {method} | `{route}` |\n"
        report += "\n</details>\n\n"
    
    if migrated:
        report += """<details>
<summary><b>✅ Successfully Migrated Endpoints (Click to expand)</b></summary>

| Method | Endpoint |
|--------|----------|
"""
        for method, route in sorted(migrated):
            report += f"| {method} | `{route}` |\n"
        report += "\n</details>\n\n"
    
    if new_in_v2:
        report += """<details>
<summary><b>✨ New V2 Endpoints (Click to expand)</b></summary>

| Method | Endpoint |
|--------|----------|
"""
        for method, route in sorted(new_in_v2):
            report += f"| {method} | `{route}` |\n"
        report += "\n</details>\n\n"
    
    return report


def extract_v2_endpoints_from_fastapi() -> List[Dict]:
    """Extract v2 endpoints using FastAPI's OpenAPI schema generation"""
    endpoints = []
    
    try:
        # We need to mock some dependencies to avoid initialization issues
        import os
        os.environ['ROTKEHLCHEN_SKIP_INIT'] = '1'
        
        # Import FastAPI and create a minimal instance
        from fastapi import FastAPI
        
        app = FastAPI(
            title='Rotki API',
            version='1.0.0',  # Use a simple version string to avoid validation errors
        )
        
        # Import and include routers directly
        from rotkehlchen.api.v2.routers import (
            accounting, assets, auth, balances, blockchain, data, defi, eth2,
            exchanges, history, names, nfts, reports, settings as settings_router,
            statistics, users, watchers
        )
        
        # Include routers with their prefixes (matching app.py)
        routers = [
            (auth.router, '/api/v2/auth'),
            (users.router, '/api/v2/users'),
            (settings_router.router, '/api/v2/settings'),
            (assets.router, '/api/v2/assets'),
            (balances.router, '/api/v2/balances'),
            (blockchain.router, '/api/v2/blockchain'),
            (exchanges.router, '/api/v2/exchanges'),
            (history.router, '/api/v2/history'),
            (statistics.router, '/api/v2/statistics'),
            (reports.router, '/api/v2/reports'),
            (accounting.router, '/api/v2/accounting'),
            (eth2.router, '/api/v2/blockchains/eth2'),
            (data.router, '/api/v2/data'),
            (nfts.router, '/api/v2/nfts'),
            (defi.router, '/api/v2/defi'),
            (names.router, '/api/v2/names'),
            (watchers.router, '/api/v2/watchers'),
        ]
        
        for router, prefix in routers:
            app.include_router(router, prefix=prefix)
            
        # Add direct endpoints that are in app.py
        @app.get('/api/v2/ping')
        async def ping():
            pass
            
        @app.get('/api/v2/info') 
        async def info():
            pass
        
        # Get the OpenAPI schema
        openapi_schema = app.openapi()
        
        # Extract endpoints from the paths
        if 'paths' in openapi_schema:
            for path, methods in openapi_schema['paths'].items():
                # Normalize the path to remove /api/v2 prefix
                normalized_path = path
                if normalized_path.startswith('/api/v2'):
                    normalized_path = normalized_path[7:]  # Remove /api/v2
                
                # Remove trailing slashes for consistency
                normalized_path = normalized_path.rstrip('/')
                if not normalized_path:
                    normalized_path = '/'
                
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        # Map the normalized path back to router prefix structure
                        # This matches the AST extraction format
                        file_prefix_map = {
                            '/auth': 'auth.py',
                            '/users': 'users.py',
                            '/settings': 'settings.py',
                            '/assets': 'assets.py',
                            '/balances': 'balances.py',
                            '/blockchain': 'blockchain.py',
                            '/exchanges': 'exchanges.py',
                            '/history': 'history.py',
                            '/statistics': 'statistics.py',
                            '/reports': 'reports.py',
                            '/accounting': 'accounting.py',
                            '/blockchains/eth2': 'eth2.py',
                            '/data': 'data.py',
                            '/nfts': 'nfts.py',
                            '/defi': 'defi.py',
                            '/names': 'names.py',
                            '/watchers': 'watchers.py',
                        }
                        
                        # Find which file this endpoint belongs to
                        file_name = 'unknown'
                        for prefix, fname in file_prefix_map.items():
                            if normalized_path == prefix or normalized_path.startswith(prefix + '/'):
                                file_name = fname
                                break
                        
                        endpoint_info = {
                            'route': normalized_path,
                            'method': method.upper(),
                            'file': file_name,
                        }
                        endpoints.append(endpoint_info)
        
        return endpoints
        
    except Exception as e:
        # Fall back to AST method if OpenAPI extraction fails
        print(f"Warning: OpenAPI extraction failed ({e}), falling back to AST method")
        return []


def analyze_endpoints(project_root: Path) -> Tuple[str, Dict]:
    """Main analysis function"""
    v1_server = project_root / "rotkehlchen" / "api" / "server.py"
    v2_routers = project_root / "rotkehlchen" / "api" / "v2" / "routers"
    
    if not v1_server.exists():
        return "Error: v1 server.py not found", {}
    
    v1_endpoints = extract_v1_endpoints(v1_server)
    
    # Try FastAPI OpenAPI extraction first, fall back to AST if it fails
    v2_endpoints = extract_v2_endpoints_from_fastapi()
    if not v2_endpoints:
        if not v2_routers.exists():
            return "Error: v2 routers directory not found", {}
        v2_endpoints = extract_v2_endpoints(v2_routers)
    
    report = generate_endpoint_report(v1_endpoints, v2_endpoints)
    
    # Calculate summary stats using the same normalization as the report
    v1_normalized, v2_normalized = normalize_for_comparison(v1_endpoints, v2_endpoints)
    migrated = v1_normalized & v2_normalized
    
    stats = {
        'total_v1': len(v1_normalized),
        'migrated': len(migrated),
        'percentage': (len(migrated) / len(v1_normalized) * 100) if v1_normalized else 0
    }
    
    return report, stats


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    report, stats = analyze_endpoints(project_root)
    print(report)
    print(f"\nSummary: {stats['migrated']}/{stats['total_v1']} endpoints migrated ({stats['percentage']:.1f}%)")
#!/usr/bin/env python
"""Script to help migrate from v1 to v2 API"""
import argparse
import json
import sys
from typing import Any

import requests


class V1ToV2Migrator:
    """Helper class to migrate from v1 to v2 API"""
    
    def __init__(self, v1_url: str, v2_url: str, api_key: str | None = None):
        self.v1_url = v1_url.rstrip('/')
        self.v2_url = v2_url.rstrip('/')
        self.v1_headers = {"rotki-api-key": api_key} if api_key else {}
        self.v2_headers = {"X-API-Key": api_key} if api_key else {}
    
    def test_endpoint_compatibility(self, v1_path: str, v2_path: str) -> dict[str, Any]:
        """Test if v1 and v2 endpoints return compatible data"""
        print(f"Testing: {v1_path} vs {v2_path}")
        
        # Get v1 response
        try:
            v1_response = requests.get(f"{self.v1_url}{v1_path}", headers=self.v1_headers)
            v1_data = v1_response.json() if v1_response.status_code == 200 else None
        except Exception as e:
            v1_data = None
            print(f"  ❌ v1 error: {e}")
        
        # Get v2 response
        try:
            v2_response = requests.get(f"{self.v2_url}{v2_path}", headers=self.v2_headers)
            v2_data = v2_response.json() if v2_response.status_code == 200 else None
        except Exception as e:
            v2_data = None
            print(f"  ❌ v2 error: {e}")
        
        # Compare
        if v1_data and v2_data:
            if self._compare_responses(v1_data, v2_data):
                print("  ✅ Compatible")
                return {"status": "compatible", "v1": v1_data, "v2": v2_data}
            else:
                print("  ⚠️  Differences found")
                return {"status": "different", "v1": v1_data, "v2": v2_data}
        else:
            return {"status": "error", "v1": v1_data, "v2": v2_data}
    
    def _compare_responses(self, v1_data: dict, v2_data: dict) -> bool:
        """Compare v1 and v2 responses for compatibility"""
        # Both should have 'result' key for success
        if 'result' not in v1_data or 'result' not in v2_data:
            return False
        
        # Compare structure (not exact values)
        return self._compare_structure(v1_data['result'], v2_data['result'])
    
    def _compare_structure(self, obj1: Any, obj2: Any) -> bool:
        """Compare object structures"""
        if type(obj1) != type(obj2):
            return False
        
        if isinstance(obj1, dict):
            # Check if keys are similar (allowing some differences)
            keys1 = set(obj1.keys())
            keys2 = set(obj2.keys())
            
            # Allow up to 20% difference in keys
            common_keys = keys1.intersection(keys2)
            if len(common_keys) < len(keys1) * 0.8:
                return False
            
            # Recursively check common keys
            for key in common_keys:
                if not self._compare_structure(obj1[key], obj2[key]):
                    return False
        
        elif isinstance(obj1, list):
            # For lists, just check if both are lists
            # Don't compare contents as they may differ
            return True
        
        # For primitive types, just check type compatibility
        return True
    
    def run_compatibility_tests(self) -> dict[str, Any]:
        """Run all compatibility tests"""
        endpoints_to_test = [
            ("/api/1/ping", "/api/v2/ping"),
            ("/api/1/info", "/api/v2/info"),
            ("/api/1/settings", "/api/v2/settings"),
            ("/api/1/assets/all", "/api/v2/assets/all"),
            ("/api/1/balances", "/api/v2/balances"),
            ("/api/1/history/events", "/api/v2/history/events"),
            ("/api/1/exchanges", "/api/v2/exchanges"),
            ("/api/1/blockchains/supported", "/api/v2/blockchain/supported"),
        ]
        
        results = {}
        for v1_path, v2_path in endpoints_to_test:
            results[v1_path] = self.test_endpoint_compatibility(v1_path, v2_path)
        
        return results
    
    def generate_migration_report(self, results: dict[str, Any]) -> str:
        """Generate a migration compatibility report"""
        report = ["# V1 to V2 Migration Compatibility Report\n"]
        
        compatible = sum(1 for r in results.values() if r['status'] == 'compatible')
        total = len(results)
        
        report.append(f"## Summary: {compatible}/{total} endpoints compatible\n")
        
        report.append("## Endpoint Details\n")
        for endpoint, result in results.items():
            status_emoji = {
                'compatible': '✅',
                'different': '⚠️',
                'error': '❌'
            }.get(result['status'], '❓')
            
            report.append(f"### {status_emoji} {endpoint}")
            report.append(f"- Status: {result['status']}")
            
            if result['status'] == 'different' and result['v1'] and result['v2']:
                report.append("- Differences:")
                # Show key differences
                v1_keys = set(result['v1'].get('result', {}).keys()) if isinstance(result['v1'].get('result'), dict) else set()
                v2_keys = set(result['v2'].get('result', {}).keys()) if isinstance(result['v2'].get('result'), dict) else set()
                
                missing_in_v2 = v1_keys - v2_keys
                new_in_v2 = v2_keys - v1_keys
                
                if missing_in_v2:
                    report.append(f"  - Missing in v2: {missing_in_v2}")
                if new_in_v2:
                    report.append(f"  - New in v2: {new_in_v2}")
            
            report.append("")
        
        return "\n".join(report)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test v1 to v2 API migration compatibility')
    parser.add_argument('--v1-url', default='http://localhost:8080', help='v1 API URL')
    parser.add_argument('--v2-url', default='http://localhost:8001', help='v2 API URL')
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--output', help='Output file for report (default: stdout)')
    
    args = parser.parse_args()
    
    migrator = V1ToV2Migrator(args.v1_url, args.v2_url, args.api_key)
    
    print("Running v1 to v2 compatibility tests...")
    results = migrator.run_compatibility_tests()
    
    report = migrator.generate_migration_report(results)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {args.output}")
    else:
        print("\n" + report)
    
    # Exit with error if any incompatibilities
    compatible_count = sum(1 for r in results.values() if r['status'] == 'compatible')
    if compatible_count < len(results):
        sys.exit(1)


if __name__ == '__main__':
    main()
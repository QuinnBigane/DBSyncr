#!/usr/bin/env python3
"""
Simple API validation - runs without interfering with server
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
import json
import time

def validate_api_endpoints():
    """Simple validation of API endpoints"""
    
    base_url = "http://localhost:8001"
    api_prefix = "/api/v1"
    
    print("🔍 API Endpoint Validation")
    print("=" * 50)
    print(f"Server: {base_url}")
    print()
    
    # Test data to track
    results = []
    
    endpoints = [
        ("Health Check", "GET", f"{base_url}/health", None, "Status should be healthy"),
        ("Data Summary", "GET", f"{base_url}{api_prefix}/data/summary", None, "Should show loaded data counts"),
        ("Field Mappings", "GET", f"{base_url}{api_prefix}/mappings", None, "Should return mapping configuration"),
        ("DB1 Data (Small)", "GET", f"{base_url}{api_prefix}/data/db1?page=1&limit=3", None, "Should return NetSuite test data"),
        ("DB2 Data (Small)", "GET", f"{base_url}{api_prefix}/data/db2?page=1&limit=3", None, "Should return Shopify test data"),
        ("Combined Data (Small)", "GET", f"{base_url}{api_prefix}/data/combined?page=1&limit=3", None, "Should return merged data"),
        ("Unmatched Analysis", "GET", f"{base_url}{api_prefix}/analysis/unmatched", None, "Should show matching statistics"),
    ]
    
    passed = 0
    total = len(endpoints)
    
    for name, method, url, payload, description in endpoints:
        print(f"⚡ Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Expected: {description}")
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS (200 OK)")
                data = response.json()
                
                # Show some key data based on endpoint
                if name == "Health Check":
                    print(f"      Status: {data.get('status', 'unknown')}")
                    print(f"      Version: {data.get('version', 'unknown')}")
                    
                elif name == "Data Summary":
                    if data.get('success'):
                        summary = data['data']
                        db1_count = summary.get('db1', {}).get('records', 0)
                        db2_count = summary.get('db2', {}).get('records', 0)
                        combined_count = summary.get('combined', {}).get('records', 0)
                        print(f"      DB1 Records: {db1_count}")
                        print(f"      DB2 Records: {db2_count}")
                        print(f"      Combined Records: {combined_count}")
                        
                elif name == "Field Mappings":
                    if data.get('success'):
                        mappings = data['data'].get('field_mappings', {})
                        print(f"      Field Mappings: {len(mappings)}")
                        for field_name in list(mappings.keys())[:2]:
                            print(f"        • {field_name}")
                            
                elif "Data" in name and data.get('success'):
                    records = len(data.get('data', []))
                    total_records = data.get('pagination', {}).get('total_records', 0)
                    print(f"      Records in page: {records}")
                    print(f"      Total records: {total_records}")
                    
                elif name == "Unmatched Analysis":
                    matched = data.get('matched_items', 0)
                    db1_only = data.get('db1_only_items', 0)
                    db2_only = data.get('db2_only_items', 0)
                    print(f"      Matched items: {matched}")
                    print(f"      DB1 only: {db1_only}")
                    print(f"      DB2 only: {db2_only}")
                
                passed += 1
            else:
                print(f"   ❌ FAILED ({response.status_code})")
                print(f"      Error: {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ REQUEST FAILED: {str(e)}")
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
        
        print()
        time.sleep(0.1)  # Small delay between requests
    
    print("📊 VALIDATION RESULTS")
    print("=" * 50)
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All API endpoints are working correctly!")
        return True
    else:
        print("⚠️  Some endpoints need attention")
        return False

if __name__ == "__main__":
    success = validate_api_endpoints()
    sys.exit(0 if success else 1)
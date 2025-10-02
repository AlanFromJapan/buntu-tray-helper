#!/usr/bin/env python3
"""
Test script for the HTTP health check plugin
"""
import sys
import os

# Add the plugins directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'plugins'))

from plugin_http_health import http_get

def test_http_check():
    print("Testing HTTP health check functionality...")
    
    # Test with Google
    result = http_get("https://www.google.com", timeout=10, expected_text="Google")
    print(f"Google test result: {result}")
    
    # Test with httpbin
    result = http_get("https://httpbin.org/status/200", timeout=10, expected_status=200)
    print(f"HTTPBin test result: {result}")
    
    # Test with invalid URL
    result = http_get("https://nonexistent-domain-test-12345.com", timeout=5)
    print(f"Invalid URL test result: {result}")

if __name__ == "__main__":
    test_http_check()
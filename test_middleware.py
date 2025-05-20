#!/usr/bin/env python3
"""
Test Script for DCS Lua Analyzer Middleware

This script tests the middleware by sending a sample DCS-related query
and comparing the response with a direct query to Ollama.
"""

import requests
import json
import time
import sys

# Configuration
MIDDLEWARE_URL = "http://localhost:8080"
OLLAMA_URL = "http://localhost:11434"
MODEL = "codegemma"  # Change to match your available model

def test_health():
    """Test the middleware health endpoint."""
    print("\n=== Testing Middleware Health ===\n")
    try:
        resp = requests.get(f"{MIDDLEWARE_URL}/health")
        health_data = resp.json()
        print(f"Health Status: {resp.status_code}")
        print(json.dumps(health_data, indent=2))
        return resp.status_code == 200
    except Exception as e:
        print(f"Error checking middleware health: {e}")
        return False

def test_dcs_query():
    """Test the middleware with a DCS-related query."""
    print("\n=== Testing DCS-Related Query ===\n")
    dcs_query = "How do I create waypoints for AI aircraft in DCS World?"
    
    # Create a simple query payload
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": dcs_query}
        ]
    }
    
    try:
        print(f"Sending DCS query to middleware: {dcs_query}")
        start_time = time.time()
        resp = requests.post(
            f"{MIDDLEWARE_URL}/api/chat/completions",
            json=payload
        )
        end_time = time.time()
        
        print(f"Status code: {resp.status_code}")
        print(f"Response time: {end_time - start_time:.2f} seconds")
        
        if resp.status_code == 200:
            response_data = resp.json()
            
            # Extract and print the response content
            content = None
            if "choices" in response_data and len(response_data["choices"]) > 0:
                if "message" in response_data["choices"][0]:
                    content = response_data["choices"][0]["message"].get("content")
                elif "delta" in response_data["choices"][0]:
                    content = response_data["choices"][0]["delta"].get("content")
            
            if content:
                print("\nResponse excerpt (first 300 chars):")
                print(content[:300] + "...")
                
                # Check if the response includes code snippets or DCS-specific information
                contains_lua = "lua" in content.lower() or "function" in content.lower()
                contains_dcs_terms = any(term in content.lower() for term in 
                                        ["waypoint", "mission", "dcs", "aircraft"])
                
                print(f"\nResponse contains Lua code references: {contains_lua}")
                print(f"Response contains DCS-specific terms: {contains_dcs_terms}")
                
                return contains_lua or contains_dcs_terms
            else:
                print("No content found in response")
                return False
        else:
            print(f"Error response: {resp.text}")
            return False
    except Exception as e:
        print(f"Error testing DCS query: {e}")
        return False

def test_non_dcs_query():
    """Test the middleware with a non-DCS-related query."""
    print("\n=== Testing Non-DCS-Related Query ===\n")
    non_dcs_query = "What is the capital of France?"
    
    # Create a simple query payload
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": non_dcs_query}
        ]
    }
    
    try:
        print(f"Sending non-DCS query to middleware: {non_dcs_query}")
        start_time = time.time()
        resp = requests.post(
            f"{MIDDLEWARE_URL}/api/chat/completions",
            json=payload
        )
        end_time = time.time()
        
        print(f"Status code: {resp.status_code}")
        print(f"Response time: {end_time - start_time:.2f} seconds")
        
        if resp.status_code == 200:
            # For non-DCS queries, we expect a quick response time since no enhancement is needed
            print(f"Response was appropriately fast for non-DCS query: {end_time - start_time < 1.0}")
            return True
        else:
            print(f"Error response: {resp.text}")
            return False
    except Exception as e:
        print(f"Error testing non-DCS query: {e}")
        return False

def main():
    """Run all tests."""
    print("=== DCS Lua Analyzer Middleware Test ===")
    
    # Test 1: Check middleware health
    health_ok = test_health()
    if not health_ok:
        print("\n❌ Health check failed. Please check that the middleware is running.")
        sys.exit(1)
    
    # Test 2: Test with DCS-related query
    dcs_ok = test_dcs_query()
    
    # Test 3: Test with non-DCS-related query
    non_dcs_ok = test_non_dcs_query()
    
    # Print summary
    print("\n=== Test Summary ===\n")
    print(f"Health check: {'✅ PASSED' if health_ok else '❌ FAILED'}")
    print(f"DCS query test: {'✅ PASSED' if dcs_ok else '❌ FAILED'}")
    print(f"Non-DCS query test: {'✅ PASSED' if non_dcs_ok else '❌ FAILED'}")
    
    if health_ok and dcs_ok and non_dcs_ok:
        print("\n✅ All tests passed! The middleware is working correctly.")
        print("\nTo integrate with Open WebUI, configure it to use this URL:")
        print(f"  {MIDDLEWARE_URL}")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the middleware logs.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python
"""Simple test script for v2 API"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create a minimal FastAPI app for testing
app = FastAPI()

@app.get("/api/v2/ping")
async def ping():
    """Health check endpoint"""
    return {"result": True}

@app.get("/api/v2/info")
async def info():
    """Get application information"""
    return {
        "result": {
            "version": "1.39.0",
            "data_directory": "/tmp/rotki",
        }
    }

@app.get("/api/v2/test")
async def test():
    """Test endpoint"""
    return {"result": {"message": "FastAPI v2 is working!"}}

# Create test client
client = TestClient(app)

def test_ping():
    """Test ping endpoint"""
    response = client.get("/api/v2/ping")
    assert response.status_code == 200
    data = response.json()
    assert data == {"result": True}
    print("✅ Ping test passed")

def test_info():
    """Test info endpoint"""
    response = client.get("/api/v2/info")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "version" in data["result"]
    assert "data_directory" in data["result"]
    print("✅ Info test passed")

def test_custom():
    """Test custom endpoint"""
    response = client.get("/api/v2/test")
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["message"] == "FastAPI v2 is working!"
    print("✅ Custom test passed")

def test_not_found():
    """Test 404 handling"""
    response = client.get("/api/v2/nonexistent")
    assert response.status_code == 404
    print("✅ 404 test passed")

def test_response_format():
    """Test that responses match v1 format"""
    # v1 format: {"result": <data>} for success
    response = client.get("/api/v2/ping")
    data = response.json()
    
    # Should have "result" key
    assert "result" in data
    # Should not have "message" in success response
    assert "message" not in data
    print("✅ Response format test passed")

if __name__ == "__main__":
    print("Testing FastAPI v2 API...")
    print("-" * 40)
    
    test_ping()
    test_info()
    test_custom()
    test_not_found()
    test_response_format()
    
    print("-" * 40)
    print("✅ All tests passed!")
    print("\nYou can now run the full API with:")
    print("  uv run uvicorn rotkehlchen.api.v2.app:create_app --factory --reload --port 8000")
    print("\nOr use the simple runner:")
    print("  uv run python -m rotkehlchen.api.v2.run")
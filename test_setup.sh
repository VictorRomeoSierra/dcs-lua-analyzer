#!/bin/bash

# Test script for DCS Lua Analyzer setup

echo "=== DCS Lua Analyzer Integration Test ==="
echo

# Check if the API server is running
echo "Checking API server..."
curl -s "http://localhost:8000/health" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ API server is running"
else
    echo "❌ API server is not running"
    echo "Starting API server..."
    docker-compose -f docker-compose-bridge.yml up -d
    sleep 5
    curl -s "http://localhost:8000/health" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ API server started successfully"
    else
        echo "❌ Failed to start API server"
        exit 1
    fi
fi

# Check if the middleware is running
echo
echo "Checking middleware..."
curl -s "http://localhost:8080/health" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Middleware is running"
else
    echo "❌ Middleware is not running"
    echo "Starting middleware..."
    docker-compose -f docker-compose-middleware.yml up -d
    sleep 5
    curl -s "http://localhost:8080/health" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Middleware started successfully"
    else
        echo "❌ Failed to start middleware"
        exit 1
    fi
fi

# Check Ollama connection
echo
echo "Checking Ollama connection..."
curl -s "http://localhost:11434/api/tags" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Ollama is running"
else
    echo "❌ Ollama is not running"
    echo "Please start Ollama before continuing"
    exit 1
fi

# Get list of available models from Ollama
echo
echo "Available Ollama models:"
curl -s "http://localhost:11434/api/tags" | grep "name" | sed 's/"name": "//g' | sed 's/",//g' | sed 's/^/  - /'

# Run the Python test script
echo
echo "Running middleware tests..."
chmod +x test_middleware.py
python3 test_middleware.py

# If all tests pass, show instructions for integrating with Open WebUI
if [ $? -eq 0 ]; then
    echo
    echo "=== Instructions for Open WebUI Integration ==="
    echo
    echo "Method 1: Use a custom configuration in Open WebUI"
    echo "  1. Go to Settings > Models > Configure API Endpoints"
    echo "  2. Change the Ollama API URL to: http://localhost:8080"
    echo "  3. Save the settings"
    echo
    echo "Method 2: Use curl to test directly"
    echo "  Run this command to test:"
    echo "  curl -X POST http://localhost:8080/api/chat/completions \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d '{\"model\":\"codegemma\",\"messages\":[{\"role\":\"user\",\"content\":\"How do I create waypoints in DCS?\"}]}'"
    echo
    echo "Method 3: Use a browser extension"
    echo "  1. Install a browser extension like 'ModHeader' for Chrome"
    echo "  2. Set it to redirect requests from http://localhost:11434 to http://localhost:8080"
    echo "  3. Use Open WebUI normally"
fi
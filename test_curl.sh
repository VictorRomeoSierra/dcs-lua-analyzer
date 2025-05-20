#!/bin/bash
# Simple curl test for the middleware

echo "=== Testing middleware with a DCS-related query ==="
curl -X POST http://localhost:8080/api/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "codegemma",
    "messages": [
      {"role": "user", "content": "How do I create waypoints for AI aircraft in DCS?"}
    ]
  }'

echo -e "\n\n=== Testing direct connection to the DCS API ==="
curl -X POST http://localhost:8000/rag_prompt \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I create waypoints for AI aircraft in DCS?",
    "limit": 3
  }'
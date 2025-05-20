# DCS Lua Analyzer Middleware for Open WebUI

This middleware acts as a bridge between Open WebUI and Ollama, enhancing DCS-related queries with code snippets from the DCS Lua Analyzer API.

## How It Works

1. The middleware exposes an endpoint that mimics Ollama's `/api/chat/completions` API
2. When a query is sent from Open WebUI:
   - The middleware checks if the query is related to DCS
   - If yes, it fetches relevant code snippets from the DCS Lua Analyzer API
   - It enhances the prompt with these code snippets
   - Then forwards the enhanced prompt to Ollama
3. Ollama processes the enhanced prompt and returns a more knowledgeable response

## Setup Instructions

### 1. Start the API Server

First, make sure the DCS Lua Analyzer API server is running:

```bash
docker-compose -f docker-compose-bridge.yml up -d
```

### 2. Start the Middleware

```bash
docker-compose -f docker-compose-middleware.yml up -d
```

### 3. Configure Open WebUI

1. In Open WebUI, go to Settings
2. Under "Endpoints" or "Models":
   - Add a new Ollama endpoint or modify the existing one
   - Change the Ollama API URL to: `http://localhost:8080` (pointing to the middleware instead of directly to Ollama)
   - Save the settings

### 4. Test the Integration

1. Start a new chat in Open WebUI
2. Ask a question about DCS, for example:
   - "How do I create waypoints for AI aircraft in DCS?"
   - "How can I spawn specific aircraft types programmatically?"
   - "What's the function to detect when aircraft enter a specific zone?"

The middleware will detect these DCS-related questions, retrieve relevant code snippets, and enhance the prompt before sending it to Ollama, resulting in more accurate and code-rich responses.

## Troubleshooting

If you encounter issues:

1. Check middleware logs:
   ```bash
   docker logs dcs-lua-middleware
   ```

2. Verify connections:
   ```bash
   # Check if middleware can reach DCS API
   curl http://localhost:8080/health
   ```

3. Test the middleware directly:
   ```bash
   curl -X POST http://localhost:8080/api/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "codegemma",
       "messages": [{"role": "user", "content": "How do I create waypoints in DCS?"}]
     }'
   ```

4. Check that Open WebUI is correctly configured to use the middleware URL rather than accessing Ollama directly
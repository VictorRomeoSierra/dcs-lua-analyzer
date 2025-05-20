# Integrating DCS Lua Analyzer API with Open WebUI

This guide explains how to integrate the DCS Lua Analyzer API server with Open WebUI to enhance DCS World Lua scripting assistance.

## Setup Instructions

### 1. Start the Docker Containers

First, make sure both Open WebUI and DCS Lua Analyzer API server are running:

```bash
# Start the DCS Lua Analyzer API server
cd /path/to/dcs-lua-analyzer
docker-compose up -d

# Check that the services are running
docker-compose ps
```

The API server will be available at `http://localhost:8000`.

### 2. Configure Open WebUI

#### Option 1: Using Open WebUI "Custom Assistants"

1. Open the Open WebUI interface and log in
2. Navigate to Assistants > Create Assistant
3. Set up a new assistant with the following configuration:
   - Name: DCS Lua Scripter
   - Description: Expert in DCS World Lua scripting
   - Instructions:
     ```
     You are an expert DCS World Lua programming assistant.
     Your task is to answer questions about DCS scripting by analyzing the relevant code snippets provided in the context.
     Always focus on providing practical, working code examples when possible.
     ```
   - Enable the "API" option
   - Set API Endpoint URL: `http://api-server:8000/rag_prompt` (if using Docker network) or `http://localhost:8000/rag_prompt` (if accessing externally)
   - Set Model: Any model that works well with code (e.g., codegemma, llama3, etc.)

#### Option 2: Using Custom API Integration

You can integrate the DCS Lua Analyzer API directly into your workflow by creating a custom middleware script:

```python
import requests
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat_proxy(request: Request):
    # Get the original request data
    data = await request.json()
    
    # Extract the user's question from the request
    messages = data.get("messages", [])
    if not messages:
        return {"error": "No messages provided"}
    
    user_message = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content")
            break
    
    if not user_message:
        return {"error": "No user message found"}
    
    # Send request to DCS Lua Analyzer API
    api_response = requests.post(
        "http://api-server:8000/rag_prompt",
        json={"query": user_message, "limit": 5}
    )
    
    if api_response.status_code != 200:
        return {"error": f"API error: {api_response.text}"}
    
    # Extract the enhanced prompt
    rag_data = api_response.json()
    enhanced_prompt = rag_data["prompt"]
    
    # Replace the original prompt with the enhanced one
    new_data = data.copy()
    
    # Create a new message array with the enhanced prompt
    new_data["messages"] = [{"role": "user", "content": enhanced_prompt}]
    
    # Forward to Open WebUI's original endpoint
    webui_response = requests.post(
        "http://open-webui:3000/api/chat/completions",
        headers=request.headers,
        json=new_data
    )
    
    # Return the LLM response
    return Response(
        content=webui_response.content,
        status_code=webui_response.status_code,
        headers=dict(webui_response.headers)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### 3. Testing the Integration

To test if the integration is working properly:

1. Start a chat in Open WebUI with your configured DCS Lua Scripter assistant
2. Ask a question about DCS scripting, for example:
   - "How do I create waypoints for AI aircraft in DCS?"
   - "How can I spawn specific aircraft types programmatically?"
   - "What's the function to detect when aircraft enter a specific zone?"

3. The system should:
   - Retrieve relevant code snippets from the DCS Lua Analyzer API
   - Format them in a context that helps the LLM understand the question
   - Generate a response that includes practical code examples

## Troubleshooting

If you encounter issues with the integration:

1. Check that both services are running: `docker-compose ps`
2. Verify the API server is accessible: `curl http://localhost:8000/health`
3. Check the API server logs: `docker-compose logs api-server`
4. Ensure the network configuration is correct and the containers can communicate
5. Verify that your database has been populated with DCS Lua code snippets

## Advanced: Direct API Usage

You can directly use the DCS Lua Analyzer API endpoints in your applications:

```javascript
// Example: Fetch RAG prompt
async function getDcsLuaPrompt(query) {
  const response = await fetch('http://localhost:8000/rag_prompt', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      limit: 5
    }),
  });
  
  return await response.json();
}

// Example usage
getDcsLuaPrompt("How do I create waypoints?").then(data => {
  console.log(data.prompt);  // Use this enhanced prompt with your LLM
});
```

## API Endpoints

- `GET /health`: Check if API is running and database is connected
- `POST /search`: Search for code snippets (returns raw results)
- `POST /context`: Get formatted context for RAG
- `POST /rag_prompt`: Get complete prompt for Open WebUI (most useful endpoint)
- `GET /stats`: Get database statistics
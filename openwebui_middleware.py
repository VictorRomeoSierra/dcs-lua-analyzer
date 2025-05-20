#!/usr/bin/env python3
"""
Open WebUI Middleware for DCS Lua Analyzer

This script creates a simple FastAPI service that sits between Open WebUI and Ollama,
enhancing queries about DCS with relevant code snippets from the DCS Lua Analyzer API.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
DCS_API_URL = os.getenv("DCS_API_URL", "http://localhost:8000")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
MIDDLEWARE_PORT = int(os.getenv("MIDDLEWARE_PORT", "8080"))

# Create FastAPI app
app = FastAPI(
    title="DCS Lua Analyzer Middleware",
    description="Middleware to enhance DCS-related queries with code snippets for Open WebUI",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def is_dcs_related(text: str) -> bool:
    """Check if a question is likely about DCS World."""
    dcs_keywords = [
        "dcs", "digital combat simulator", "eagle dynamics", 
        "lua", "script", "mission editor", "waypoint", "aircraft", 
        "helicopter", "trigger", "event", "flag", "moose", "miz", 
        "mission", "map", "world", "spawn", "flight", "route"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in dcs_keywords)

def extract_user_query(messages: List[Dict[str, Any]]) -> Optional[str]:
    """Extract the most recent user query from a list of messages."""
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content")
    return None

@app.post("/api/chat/completions")
async def chat_completions_proxy(request: Request):
    """Proxy for OpenAI-compatible chat completions API."""
    try:
        # Get request data
        data = await request.json()
        
        # Extract headers to pass through
        headers = dict(request.headers)
        # Remove headers that might cause issues
        headers.pop("host", None)
        headers.pop("content-length", None)
        
        messages = data.get("messages", [])
        user_query = extract_user_query(messages)
        
        # If there's a user query and it's DCS-related, enhance it with code snippets
        if user_query and is_dcs_related(user_query):
            logger.info(f"Enhancing DCS-related query: {user_query}")
            
            try:
                # Get code context from DCS Lua Analyzer API
                rag_response = requests.post(
                    f"{DCS_API_URL}/rag_prompt",
                    json={"query": user_query, "limit": 5},
                    timeout=10
                )
                
                if rag_response.status_code == 200:
                    rag_data = rag_response.json()
                    enhanced_prompt = rag_data["prompt"]
                    
                    # Replace the last user message with the enhanced prompt
                    new_messages = []
                    for message in messages:
                        if message.get("role") == "user" and message.get("content") == user_query:
                            new_messages.append({"role": "user", "content": enhanced_prompt})
                        else:
                            new_messages.append(message)
                    
                    # Update the request data
                    data["messages"] = new_messages
                    logger.info("Successfully enhanced query with DCS code context")
                else:
                    logger.warning(f"Failed to get RAG context: {rag_response.status_code}")
            except Exception as e:
                logger.error(f"Error enhancing query: {e}")
        
        # Forward the request to Ollama
        ollama_response = requests.post(
            f"{OLLAMA_API_URL}/api/chat/completions",
            headers={"Content-Type": "application/json"},
            json=data
        )
        
        # Return the response from Ollama
        return Response(
            content=ollama_response.content,
            status_code=ollama_response.status_code,
            headers=dict(ollama_response.headers)
        )
    
    except Exception as e:
        logger.error(f"Error in chat completions proxy: {e}")
        return {"error": str(e)}, 500

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    dcs_api_healthy = False
    ollama_healthy = False
    
    try:
        dcs_resp = requests.get(f"{DCS_API_URL}/health", timeout=5)
        dcs_api_healthy = dcs_resp.status_code == 200
    except:
        pass
    
    try:
        ollama_resp = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=5)
        ollama_healthy = ollama_resp.status_code == 200
    except:
        pass
    
    return {
        "status": "healthy" if dcs_api_healthy and ollama_healthy else "unhealthy",
        "dcs_api": "connected" if dcs_api_healthy else "disconnected",
        "ollama": "connected" if ollama_healthy else "disconnected"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting DCS Lua Analyzer Middleware on port {MIDDLEWARE_PORT}")
    logger.info(f"DCS API URL: {DCS_API_URL}")
    logger.info(f"Ollama API URL: {OLLAMA_API_URL}")
    uvicorn.run(app, host="0.0.0.0", port=MIDDLEWARE_PORT)
#!/usr/bin/env python3
"""
DCS Lua Analyzer API Server

This script creates a FastAPI server that provides an API for the DCS Lua Analyzer,
allowing integration with Open WebUI or other frontends.
"""

import os
import logging
import json
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dcs_user:secure_password@SkyEye-Server:5433/vectordb")

# Create FastAPI app
app = FastAPI(
    title="DCS Lua Analyzer API",
    description="API for retrieving DCS Lua code snippets and context for RAG applications",
    version="0.1.0",
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can restrict this in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    limit: int = 5
    detailed: bool = False

class LuaSnippet(BaseModel):
    id: int
    file_path: str
    chunk_type: str
    content: str
    line_start: int
    line_end: int
    metadata: Optional[Dict[str, Any]] = None

def connect_to_database():
    """Connect to the database."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

def text_search(conn, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for content using text search."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Create a list of keywords from the query
        keywords = query_text.lower().split()
        # Filter out common words
        keywords = [word for word in keywords if len(word) > 3]
        
        # Build a query that matches any of the keywords
        like_conditions = []
        params = []
        for word in keywords:
            like_conditions.append("content ILIKE %s")
            params.append(f"%{word}%")
        
        # Combine the conditions with OR
        if like_conditions:
            where_clause = " OR ".join(like_conditions)
            query = f"""
            SELECT id, file_path, chunk_type, content, meta_data, line_start, line_end
            FROM lua_chunks
            WHERE {where_clause}
            LIMIT %s
            """
            params.append(limit)
        else:
            # Fallback if no keywords are found
            query = """
            SELECT id, file_path, chunk_type, content, meta_data, line_start, line_end
            FROM lua_chunks
            LIMIT %s
            """
            params = [limit]
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Convert results to list of dictionaries
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error searching with text: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

def generate_context_from_results(results: List[Dict[str, Any]]) -> str:
    """Format the search results into context for the LLM."""
    if not results:
        return "No relevant DCS Lua code found in the database."
    
    context_parts = []
    
    for i, result in enumerate(results, 1):
        file_info = f"File: {result['file_path']} (Lines {result['line_start']}-{result['line_end']})"
        metadata = result.get('meta_data', {})
        if metadata and metadata.get('name'):
            file_info += f" - {metadata['name']}"
        
        context_parts.append(f"# Code Snippet {i} ({result['chunk_type']})\n{file_info}\n```lua\n{result['content']}\n```\n")
    
    return "\n".join(context_parts)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "DCS Lua Analyzer API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        conn = connect_to_database()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/search")
async def search(request: QueryRequest):
    """Search for Lua code snippets."""
    try:
        conn = connect_to_database()
        results = text_search(conn, request.query, request.limit)
        conn.close()
        
        # Convert metadata from JSON if needed
        for result in results:
            if 'meta_data' in result and result['meta_data']:
                if isinstance(result['meta_data'], str):
                    try:
                        result['meta_data'] = json.loads(result['meta_data'])
                    except:
                        pass
        
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/context")
async def get_context(request: QueryRequest):
    """Get formatted context for RAG."""
    try:
        conn = connect_to_database()
        results = text_search(conn, request.query, request.limit)
        conn.close()
        
        context = generate_context_from_results(results)
        return {"context": context, "snippet_count": len(results)}
    except Exception as e:
        logger.error(f"Error in context endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Context generation failed: {str(e)}")

@app.post("/rag_prompt")
async def get_rag_prompt(
    request: dict = Body(..., example={"query": "How do I create waypoints for AI aircraft?", "limit": 5})
):
    """Get a complete RAG prompt for Open WebUI."""
    try:
        query = request.get("query", "")
        limit = request.get("limit", 5)
        
        conn = connect_to_database()
        results = text_search(conn, query, limit)
        conn.close()
        
        context = generate_context_from_results(results)
        
        system_prompt = """You are an expert DCS World Lua programming assistant. 
Your task is to answer questions about DCS scripting by analyzing the relevant code snippets provided.
Always focus on providing practical, working code examples when possible.
If the provided context doesn't fully address the question, say so and provide your best guess based on general Lua and DCS knowledge.
For code examples, always use proper Lua syntax and follow DCS scripting conventions."""

        full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        
        return {
            "prompt": full_prompt,
            "context": context,
            "system_prompt": system_prompt,
            "snippet_count": len(results)
        }
    except Exception as e:
        logger.error(f"Error in rag_prompt endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"RAG prompt generation failed: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get database statistics."""
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        
        # Get total count of snippets
        cursor.execute("SELECT COUNT(*) FROM lua_chunks")
        total_count = cursor.fetchone()[0]
        
        # Get counts by chunk type
        cursor.execute("SELECT chunk_type, COUNT(*) FROM lua_chunks GROUP BY chunk_type")
        type_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get file count
        cursor.execute("SELECT COUNT(DISTINCT file_path) FROM lua_chunks")
        file_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_snippets": total_count,
            "file_count": file_count,
            "by_chunk_type": type_counts
        }
    except Exception as e:
        logger.error(f"Error in stats endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Run the application
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=True)
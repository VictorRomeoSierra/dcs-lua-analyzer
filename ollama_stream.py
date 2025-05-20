#!/usr/bin/env python3
"""
Simple Ollama Streaming for DCS Lua Database

This script uses text search to find relevant code and streams the response from Ollama.
"""

import os
import argparse
import logging
import psycopg2
import psycopg2.extras
import json
import requests
import sys
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://SkyEye-Server:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "codegemma")

def connect_to_database(conn_string):
    """Connect to the database directly using psycopg2."""
    try:
        conn = psycopg2.connect(conn_string)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def text_search(conn, query_text, limit=5):
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
        
        return results
    except Exception as e:
        logger.error(f"Error searching with text: {e}")
        return []

def generate_context_from_results(results):
    """Format the search results into context for the LLM."""
    if not results:
        return "No relevant DCS Lua code found in the database."
    
    context_parts = []
    
    for i, result in enumerate(results, 1):
        file_info = f"File: {result['file_path']} (Lines {result['line_start']}-{result['line_end']})"
        if result['meta_data'] and result['meta_data'].get('name'):
            file_info += f" - {result['meta_data']['name']}"
        
        context_parts.append(f"# Code Snippet {i} ({result['chunk_type']})\n{file_info}\n```lua\n{result['content']}\n```\n")
    
    return "\n".join(context_parts)

def query_ollama_stream(prompt, context, temperature=0.1):
    """Query Ollama with the context and prompt, streaming the response."""
    try:
        system_prompt = """You are an expert DCS World Lua programming assistant. 
Your task is to answer questions about DCS scripting by analyzing the relevant code snippets provided.
Always focus on providing practical, working code examples when possible.
If the provided context doesn't fully address the question, say so and provide your best guess based on general Lua and DCS knowledge.
For code examples, always use proper Lua syntax and follow DCS scripting conventions."""

        combined_prompt = f"System: {system_prompt}\n\nContext:\n{context}\n\nUser Question: {prompt}\n\nAnswer:"
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_LLM_MODEL,
                "prompt": combined_prompt,
                "temperature": temperature,
                "stream": True
            },
            stream=True
        )
        
        # Handle the streaming response
        if response.status_code == 200:
            print("\n# Response\n")
            for line in response.iter_lines():
                if line:
                    try:
                        json_line = json.loads(line.decode('utf-8'))
                        if 'response' in json_line:
                            chunk = json_line['response']
                            print(chunk, end='', flush=True)
                    except json.JSONDecodeError:
                        logger.error(f"Error decoding JSON: {line}")
            print("\n")
        else:
            logger.error(f"Error from Ollama API: {response.text}")
            return f"Error: Failed to get response from the model. Status code: {response.status_code}"
        
        return True
    
    except Exception as e:
        logger.error(f"Error querying Ollama: {e}")
        return f"Error: {str(e)}"

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Simple Ollama Streaming for DCS Lua Database")
    parser.add_argument("query", type=str, help="The search query")
    parser.add_argument("--db-url", type=str, 
                        default=os.getenv("DATABASE_URL", "postgresql://dcs_user:secure_password@SkyEye-Server:5433/vectordb"), 
                        help="PostgreSQL connection string")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of results to return")
    parser.add_argument("--show-context", action="store_true", help="Show detailed context provided to the LLM")
    parser.add_argument("--temperature", type=float, default=0.1, help="Temperature for the LLM generation")
    
    args = parser.parse_args()
    
    # Connect to the database
    conn = connect_to_database(args.db_url)
    if not conn:
        logger.error("Failed to connect to the database.")
        return
    
    try:
        # Search using text search
        print(f"🔍 Searching for relevant code using text search: {args.query}")
        results = text_search(conn, args.query, args.limit)
        
        if not results:
            print("No relevant code found in the database.")
            return
            
        print(f"✅ Found {len(results)} relevant code snippets")
        
        # Generate context from results
        context = generate_context_from_results(results)
        
        # Show context if requested
        if args.show_context:
            print("\n# Context Used for Query\n")
            print(context)
            print("\n" + "=" * 80 + "\n")
        
        # Query the LLM with streaming
        print(f"💬 Querying {OLLAMA_LLM_MODEL} with your question...")
        query_ollama_stream(args.query, context, args.temperature)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
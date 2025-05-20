#!/usr/bin/env python3
"""
Simple Ollama RAG for DCS Lua Database

This script uses direct SQL for search and a simplified approach for Ollama.
"""

import os
import argparse
import logging
import psycopg2
import psycopg2.extras
import json
import requests
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://SkyEye-Server:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
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
        
        # Use text search with ILIKE
        query = """
        SELECT id, file_path, chunk_type, content, meta_data, line_start, line_end
        FROM lua_chunks
        WHERE content ILIKE %s
        LIMIT %s
        """
        
        cursor.execute(query, (f'%{query_text}%', limit))
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
        if result['meta_data'] and 'name' in result['meta_data'] and result['meta_data']['name']:
            file_info += f" - {result['meta_data']['name']}"
        
        context_parts.append(f"# Code Snippet {i} ({result['chunk_type']})\n{file_info}\n```lua\n{result['content']}\n```\n")
    
    return "\n".join(context_parts)

def query_ollama(prompt, context, temperature=0.1):
    """Query Ollama with the context and prompt."""
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
        
        # Handle streaming response
        if response.status_code == 200:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        json_line = json.loads(line.decode('utf-8'))
                        if 'response' in json_line:
                            full_response += json_line['response']
                    except json.JSONDecodeError:
                        logger.error(f"Error decoding JSON: {line}")
            return full_response
        else:
            logger.error(f"Error from Ollama API: {response.text}")
            return f"Error: Failed to get response from the model. Status code: {response.status_code}"
    
    except Exception as e:
        logger.error(f"Error querying Ollama: {e}")
        return f"Error: {str(e)}"

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Simple Ollama RAG for DCS Lua Database")
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
        
        # Query the LLM
        print(f"💬 Querying {OLLAMA_LLM_MODEL} with your question...")
        llm_response = query_ollama(args.query, context, args.temperature)
        
        # Format and display the output
        if args.show_context:
            print("\n# Context Used for Query\n")
            print(context)
            print("\n" + "=" * 80 + "\n")
            
        print("\n# Response\n")
        print(llm_response)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
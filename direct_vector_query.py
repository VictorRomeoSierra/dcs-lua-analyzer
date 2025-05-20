#!/usr/bin/env python3
"""
Direct Vector Query for DCS Lua Database

This script uses direct SQL with vector operations to find relevant code.
"""

import os
import argparse
import logging
import psycopg2
import psycopg2.extras
import json
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://SkyEye-Server:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

def connect_to_database(conn_string):
    """Connect to the database directly using psycopg2."""
    try:
        conn = psycopg2.connect(conn_string)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def generate_embedding(text):
    """Generate an embedding using Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": OLLAMA_EMBEDDING_MODEL, "prompt": text}
        )
        return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise

def vector_search(conn, query_text, limit=10):
    """Search for similar content using vector embeddings."""
    try:
        # Generate embedding for the query
        query_embedding = generate_embedding(query_text)
        
        # Convert the embedding to a string format for PG
        vector_str = str(query_embedding).replace('[', '[').replace(']', ']')
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Use direct SQL with the vector cast
        query = f"""
        SELECT id, file_path, chunk_type, content, meta_data, line_start, line_end, 
               embedding <-> '{vector_str}'::vector AS distance
        FROM lua_chunks
        ORDER BY distance
        LIMIT {limit}
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        return results
    except Exception as e:
        logger.error(f"Error searching with vector: {e}")
        return []

def print_results(results, detailed=False):
    """Print search results."""
    if not results:
        print("No results found.")
        return
    
    print(f"Found {len(results)} results:")
    print("-" * 80)
    
    for i, result in enumerate(results, 1):
        print(f"[{i}] {result['file_path']}:{result['line_start']}-{result['line_end']} "
              f"({result['chunk_type']}) - Distance: {result['distance']:.4f}")
        
        # Print metadata if available
        if result['meta_data'] and detailed:
            print(f"    Metadata: {result['meta_data']}")
        
        if detailed:
            print("\n" + result['content'] + "\n")
        else:
            lines = result['content'].split('\n')
            if lines:
                print("    " + lines[0][:100] + ("..." if len(lines[0]) > 100 else ""))
        
        print("-" * 80)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Direct Vector Query for DCS Lua Database")
    parser.add_argument("query", type=str, help="The search query")
    parser.add_argument("--db-url", type=str, 
                        default=os.getenv("DATABASE_URL", "postgresql://dcs_user:secure_password@SkyEye-Server:5433/vectordb"), 
                        help="PostgreSQL connection string")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results to return")
    parser.add_argument("--detailed", action="store_true", help="Show detailed results including full code content")
    
    args = parser.parse_args()
    
    # Connect to the database
    conn = connect_to_database(args.db_url)
    if not conn:
        logger.error("Failed to connect to the database.")
        return
    
    try:
        # Search using vector embeddings
        print(f"Searching for: {args.query}")
        print("Generating embedding...")
        results = vector_search(conn, args.query, args.limit)
        print_results(results, args.detailed)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Simple Query for DCS Lua Database

This script performs a basic text search against the Lua chunks database.
"""

import os
import argparse
import logging
import psycopg2
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def connect_to_database(conn_string):
    """Connect to the database directly using psycopg2."""
    try:
        conn = psycopg2.connect(conn_string)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def search_by_content(conn, search_term, limit=10):
    """Search for text in the content field."""
    try:
        cursor = conn.cursor()
        
        # Basic text search using ILIKE for case-insensitive matching
        query = """
        SELECT id, file_path, chunk_type, content, line_start, line_end
        FROM lua_chunks
        WHERE content ILIKE %s
        ORDER BY id
        LIMIT %s
        """
        
        cursor.execute(query, (f'%{search_term}%', limit))
        results = cursor.fetchall()
        
        return results
    except Exception as e:
        logger.error(f"Error searching database: {e}")
        return []

def print_results(results, detailed=False):
    """Print search results."""
    if not results:
        print("No results found.")
        return
    
    print(f"Found {len(results)} results:")
    print("-" * 80)
    
    for i, (id, file_path, chunk_type, content, line_start, line_end) in enumerate(results, 1):
        print(f"[{i}] {file_path}:{line_start}-{line_end} ({chunk_type})")
        
        if detailed:
            print("\n" + content + "\n")
        else:
            lines = content.split('\n')
            if lines:
                print("    " + lines[0][:100] + ("..." if len(lines[0]) > 100 else ""))
        
        print("-" * 80)

def get_table_info(conn):
    """Get information about the lua_chunks table."""
    try:
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'lua_chunks'
        );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            return "Table lua_chunks does not exist."
        
        # Get column info
        cursor.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'lua_chunks';
        """)
        
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute("SELECT COUNT(*) FROM lua_chunks;")
        row_count = cursor.fetchone()[0]
        
        result = f"Table lua_chunks exists with {row_count} rows.\nColumns:\n"
        for col in columns:
            result += f"- {col[0]}: {col[1]} (nullable: {col[2]})\n"
            
        return result
    
    except Exception as e:
        logger.error(f"Error getting table info: {e}")
        return f"Error: {str(e)}"

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Simple Query for DCS Lua Database")
    parser.add_argument("query", type=str, nargs="?", help="The search query")
    parser.add_argument("--db-url", type=str, 
                        default=os.getenv("DATABASE_URL", "postgresql://dcs_user:secure_password@SkyEye-Server:5433/vectordb"), 
                        help="PostgreSQL connection string")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results to return")
    parser.add_argument("--detailed", action="store_true", help="Show detailed results including full code content")
    parser.add_argument("--info", action="store_true", help="Show database table information")
    
    args = parser.parse_args()
    
    # Connect to the database
    conn = connect_to_database(args.db_url)
    if not conn:
        logger.error("Failed to connect to the database.")
        return
    
    try:
        # Show table info if requested
        if args.info:
            info = get_table_info(conn)
            print(info)
            return
        
        # Check for query
        if not args.query:
            parser.print_help()
            return
        
        # Search and display results
        results = search_by_content(conn, args.query, args.limit)
        print_results(results, args.detailed)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
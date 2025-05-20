#!/usr/bin/env python3
"""
Docker-friendly utility for loading DCS Lua code into the database.

This script is designed to be run inside the Docker container to process
DCS Lua files and load them into the database.
"""

import os
import argparse
import logging
from lua_embedder import parse_and_store_lua_file
import psycopg2
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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dcs_user:secure_password@db:5432/vectordb")

def process_directory(directory_path, conn, limit=None):
    """Process all Lua files in the specified directory."""
    if not os.path.exists(directory_path):
        logger.error(f"Directory not found: {directory_path}")
        return

    count = 0
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.lua'):
                file_path = os.path.join(root, file)
                try:
                    logger.info(f"Processing file: {file_path}")
                    parse_and_store_lua_file(file_path, conn)
                    count += 1
                    if limit and count >= limit:
                        logger.info(f"Reached file limit ({limit})")
                        return
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")

def process_single_file(file_path, conn):
    """Process a single Lua file."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    if not file_path.endswith('.lua'):
        logger.error(f"Not a Lua file: {file_path}")
        return

    try:
        logger.info(f"Processing file: {file_path}")
        parse_and_store_lua_file(file_path, conn)
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Process DCS Lua files for Docker environment')
    parser.add_argument('--dir', help='Directory containing Lua files to process')
    parser.add_argument('--single-file', help='Process a single Lua file')
    parser.add_argument('--limit', type=int, help='Limit the number of files to process')
    parser.add_argument('--db-url', help='Database connection string')
    
    args = parser.parse_args()
    
    if not (args.dir or args.single_file):
        parser.error("You must specify either --dir or --single-file")
    
    # Use provided database URL or default
    db_url = args.db_url or DATABASE_URL
    
    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        logger.info("Connected to the database")
        
        if args.dir:
            process_directory(args.dir, conn, args.limit)
        elif args.single_file:
            process_single_file(args.single_file, conn)
        
        conn.close()
        logger.info("Processing completed")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()
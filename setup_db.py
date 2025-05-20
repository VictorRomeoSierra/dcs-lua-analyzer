#!/usr/bin/env python3
"""
Database Setup Script - Creates the PostgreSQL database and sets up pgvector

This script creates the database and installs the pgvector extension
if it's not already installed.
"""

import os
import argparse
import logging
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def setup_existing_database(conn_params):
    """Set up pgvector extension on the existing database."""
    try:
        # Connect to the existing database
        conn = psycopg2.connect(conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            # Check if pgvector extension is already installed
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            if cursor.fetchone():
                logger.info("pgvector extension already installed")
            else:
                cursor.execute("CREATE EXTENSION vector")
                logger.info("pgvector extension installed successfully")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Setup PostgreSQL database for DCS Lua Analyzer")
    parser.add_argument("--db-url", type=str, 
                        default=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@SkyEye-Server:5433/vectordb"), 
                        help="PostgreSQL connection string")
    
    args = parser.parse_args()
    
    if setup_existing_database(args.db_url):
        logger.info("Database setup completed successfully")
    else:
        logger.error("Database setup failed")

if __name__ == "__main__":
    main()
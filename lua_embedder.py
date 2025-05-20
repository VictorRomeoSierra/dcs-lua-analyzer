#!/usr/bin/env python3
"""
DCS Lua Embedder - Process Lua files into vector embeddings for RAG applications

This script parses Lua files from DCS World, chunks them intelligently using tree-sitter,
and stores them in a PostgreSQL database with pgvector for efficient retrieval.
"""

import os
import argparse
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
from tqdm import tqdm
import json
from dotenv import load_dotenv

# Tree-sitter for Lua parsing
from tree_sitter import Language, Parser
import tree_sitter_languages

# Database
import psycopg2
from psycopg2.extras import execute_values
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

# For embedding generation
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Ollama (default)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://SkyEye-Server:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "codegemma")
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"

# Configure OpenAI (alternative)
openai.api_key = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "text-embedding-3-small")

# Setup SQLAlchemy
from sqlalchemy.orm import declarative_base
Base = declarative_base()

class LuaChunk(Base):
    __tablename__ = 'lua_chunks'
    
    id = sa.Column(sa.Integer, primary_key=True)
    file_path = sa.Column(sa.String, nullable=False)
    chunk_type = sa.Column(sa.String, nullable=False)  # 'function', 'table', 'comment', etc.
    content = sa.Column(sa.Text, nullable=False)
    meta_data = sa.Column(JSONB, nullable=True)  # Renamed from metadata to avoid conflict
    embedding = sa.Column(Vector(768), nullable=True)  # 768 for nomic-embed-text
    line_start = sa.Column(sa.Integer, nullable=False)
    line_end = sa.Column(sa.Integer, nullable=False)
    parent_id = sa.Column(sa.Integer, sa.ForeignKey('lua_chunks.id'), nullable=True)

def setup_database(conn_string: str) -> sa.engine.Engine:
    """Create database engine and tables if they don't exist."""
    engine = sa.create_engine(conn_string)
    Base.metadata.create_all(engine)
    return engine

def get_lua_parser():
    """Set up tree-sitter parser for Lua."""
    try:
        # Use the get_parser function which returns a pre-configured parser
        parser = tree_sitter_languages.get_parser('lua')
        return parser
    except Exception as e:
        logger.error(f"Error getting Lua parser: {str(e)}")
        return None

def extract_node_text(node, source_bytes: bytes) -> str:
    """Extract text from a tree-sitter node."""
    return source_bytes[node.start_byte:node.end_byte].decode('utf-8')

def get_node_line_range(node) -> Tuple[int, int]:
    """Get the start and end line numbers for a node."""
    return (node.start_point[0] + 1, node.end_point[0] + 1)

def get_node_metadata(node, source_bytes: bytes) -> Dict[str, Any]:
    """Extract metadata from a tree-sitter node."""
    metadata = {
        "node_type": node.type,
    }
    
    # Extract names for functions and tables where possible
    if node.type == "function_definition":
        for child in node.children:
            if child.type == "name":
                metadata["name"] = extract_node_text(child, source_bytes)
                break
    elif node.type == "variable_declaration":
        names = []
        for child in node.children:
            if child.type == "variable_list":
                for name_node in child.children:
                    if name_node.type == "identifier":
                        names.append(extract_node_text(name_node, source_bytes))
        if names:
            metadata["names"] = names
    
    return metadata

def chunk_lua_file(file_path: str, parser: Parser) -> List[Dict[str, Any]]:
    """Parse a Lua file and chunk it into semantic parts using tree-sitter."""
    with open(file_path, 'rb') as f:
        source_bytes = f.read()
    
    tree = parser.parse(source_bytes)
    root_node = tree.root_node
    
    chunks = []
    
    # Process nodes of interest
    interesting_node_types = [
        "function_definition",
        "table_constructor",
        "variable_declaration",
        "assignment_statement",
        "comment",
        "if_statement",
        "for_statement",
        "while_statement",
        "repeat_statement",
        "do_statement",
        "local_function"
    ]
    
    def process_node(node, parent_id=None):
        if node.type in interesting_node_types:
            text = extract_node_text(node, source_bytes)
            line_start, line_end = get_node_line_range(node)
            
            # Skip empty or very small chunks
            if len(text.strip()) < 5:
                return None
                
            chunk_id = len(chunks) + 1
            chunks.append({
                "id": chunk_id,
                "file_path": file_path,
                "chunk_type": node.type,
                "content": text,
                "metadata": get_node_metadata(node, source_bytes),
                "line_start": line_start,
                "line_end": line_end,
                "parent_id": parent_id
            })
            return chunk_id
        return None
    
    # First pass to extract top-level chunks
    for child in root_node.children:
        process_node(child)
    
    # If we couldn't extract meaningful chunks, fallback to file-level chunking
    if not chunks:
        chunks.append({
            "id": 1,
            "file_path": file_path,
            "chunk_type": "file",
            "content": source_bytes.decode('utf-8', errors='replace'),
            "metadata": {"node_type": "file"},
            "line_start": 1,
            "line_end": root_node.end_point[0] + 1,
            "parent_id": None
        })
    
    return chunks

def generate_embedding(text: str) -> List[float]:
    """Generate an embedding for the given text."""
    if USE_OLLAMA:
        import requests
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": OLLAMA_EMBEDDING_MODEL, "prompt": text}
        )
        return response.json()["embedding"]
    else:
        # Fallback to OpenAI if Ollama is not enabled
        if not openai.api_key:
            raise ValueError("OpenAI API key not set and Ollama is disabled")
        response = openai.Embedding.create(
            model=OPENAI_MODEL,
            input=text
        )
        return response.data[0].embedding

def store_chunks(chunks: List[Dict[str, Any]], engine: sa.engine.Engine):
    """Store chunks and their embeddings in the database."""
    with engine.connect() as conn:
        for chunk in tqdm(chunks, desc="Storing chunks"):
            # Generate embedding
            try:
                embedding = generate_embedding(chunk["content"])
                chunk["embedding"] = embedding
            except Exception as e:
                logger.error(f"Error generating embedding for chunk: {e}")
                continue
            
            # Insert into database
            stmt = sa.insert(LuaChunk).values(
                file_path=chunk["file_path"],
                chunk_type=chunk["chunk_type"],
                content=chunk["content"],
                meta_data=chunk["metadata"],
                embedding=embedding,
                line_start=chunk["line_start"],
                line_end=chunk["line_end"],
                parent_id=chunk["parent_id"]
            )
            conn.execute(stmt)
            conn.commit()

def process_lua_files(directory: str, db_engine: sa.engine.Engine):
    """Process all Lua files in a directory and its subdirectories."""
    try:
        lua_files = glob.glob(f"{directory}/**/*.lua", recursive=True)
        
        if not lua_files:
            logger.warning(f"No Lua files found in {directory}")
            return
        
        logger.info(f"Found {len(lua_files)} Lua files to process")
        
        # Get the Lua parser
        parser = get_lua_parser()
        if not parser:
            logger.error("Failed to initialize Lua parser. Unable to continue.")
            return
            
        logger.info("Lua parser initialized successfully")
        
        for file_path in tqdm(lua_files, desc="Processing files"):
            try:
                logger.info(f"Processing {file_path}")
                chunks = chunk_lua_file(file_path, parser)
                if chunks and len(chunks) > 0:
                    logger.info(f"Extracted {len(chunks)} chunks from {file_path}")
                    store_chunks(chunks, db_engine)
                else:
                    logger.warning(f"No chunks extracted from {file_path}")
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue
    except Exception as e:
        logger.error(f"Error in process_lua_files: {str(e)}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process DCS Lua files into vector embeddings for RAG")
    parser.add_argument("--dir", type=str, required=True, help="Directory containing Lua files")
    parser.add_argument("--db-url", type=str, default=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@SkyEye-Server:5433/vectordb"), 
                        help="PostgreSQL connection string")
    parser.add_argument("--no-ollama", action="store_true", help="Use OpenAI instead of Ollama for embeddings")
    parser.add_argument("--limit", type=int, help="Limit the number of files to process (for testing)")
    parser.add_argument("--single-file", type=str, help="Process only this specific file")
    
    args = parser.parse_args()
    
    global USE_OLLAMA
    USE_OLLAMA = not args.no_ollama
    
    if not os.path.isdir(args.dir):
        logger.error(f"Directory not found: {args.dir}")
        return
    
    try:
        engine = setup_database(args.db_url)
        
        # Process a single file if specified
        if args.single_file:
            if not os.path.isfile(args.single_file):
                logger.error(f"File not found: {args.single_file}")
                return
                
            logger.info(f"Processing single file: {args.single_file}")
            try:
                parser = get_lua_parser()
                if parser:
                    chunks = chunk_lua_file(args.single_file, parser)
                    if chunks and len(chunks) > 0:
                        logger.info(f"Extracted {len(chunks)} chunks from {args.single_file}")
                        store_chunks(chunks, engine)
                    else:
                        logger.warning(f"No chunks extracted from {args.single_file}")
            except Exception as e:
                logger.error(f"Error processing file {args.single_file}: {str(e)}")
                raise
        # Process multiple files with a limit
        elif args.limit:
            lua_files = glob.glob(f"{args.dir}/**/*.lua", recursive=True)[:args.limit]
            logger.info(f"Limited to processing {len(lua_files)} Lua files")
            for file_path in tqdm(lua_files, desc="Processing files"):
                try:
                    logger.info(f"Processing {file_path}")
                    parser = get_lua_parser()
                    if parser:
                        chunks = chunk_lua_file(file_path, parser)
                        if chunks and len(chunks) > 0:
                            logger.info(f"Extracted {len(chunks)} chunks from {file_path}")
                            store_chunks(chunks, engine)
                        else:
                            logger.warning(f"No chunks extracted from {file_path}")
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
        # Process all files in the directory
        else:
            process_lua_files(args.dir, engine)
        
        logger.info("Processing complete")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
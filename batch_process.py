#!/usr/bin/env python3
"""
Batch DCS Lua Embedder - Process Lua files in batches to avoid memory issues

This script processes Lua files from DCS World in smaller batches to prevent memory issues.
"""

import os
import argparse
import glob
import sys
import time
from pathlib import Path
import logging
import json
from dotenv import load_dotenv
import subprocess
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_process.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_all_lua_files(directory, exclude_patterns=None):
    """Get all Lua files in a directory and its subdirectories, excluding specified patterns."""
    try:
        lua_files = glob.glob(f"{directory}/**/*.lua", recursive=True)
        
        # Apply exclusion patterns if provided
        if exclude_patterns:
            filtered_files = []
            for file_path in lua_files:
                excluded = False
                for pattern in exclude_patterns:
                    if pattern in file_path:
                        excluded = True
                        break
                if not excluded:
                    filtered_files.append(file_path)
            logger.info(f"Found {len(lua_files)} total Lua files, filtered to {len(filtered_files)} after exclusions")
            return filtered_files
        
        return lua_files
    except Exception as e:
        logger.error(f"Error finding Lua files in {directory}: {str(e)}")
        return []

def process_batch(files, batch_size=5, db_url=None):
    """Process a batch of files using the lua_embedder.py script."""
    # Create a progress bar for batches
    batch_pbar = tqdm(total=len(files)//batch_size + 1, desc="Processing batches")
    
    for i in range(0, len(files), batch_size):
        batch = files[i:i+batch_size]
        batch_dir = os.path.dirname(batch[0])
        
        logger.info(f"Processing batch {i//batch_size + 1}/{len(files)//batch_size + 1} ({len(batch)} files)")
        batch_pbar.set_description(f"Batch {i//batch_size + 1}/{len(files)//batch_size + 1}")
        
        # Create a progress bar for files within the batch
        file_pbar = tqdm(batch, desc="Files in batch", leave=False)
        
        for file_path in file_pbar:
            try:
                file_pbar.set_description(f"Processing {os.path.basename(file_path)}")
                cmd = ["python", "lua_embedder.py", "--dir", os.path.dirname(file_path), "--limit", "1", "--single-file", file_path]
                if db_url:
                    cmd.extend(["--db-url", db_url])
                
                logger.info(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, 
                                      text=True)
                
                if result.returncode != 0:
                    logger.error(f"Error processing file {file_path}")
                    logger.error(f"STDOUT: {result.stdout}")
                    logger.error(f"STDERR: {result.stderr}")
                    file_pbar.set_description(f"❌ Error: {os.path.basename(file_path)}")
                else:
                    logger.info(f"Successfully processed {file_path}")
                    file_pbar.set_description(f"✅ {os.path.basename(file_path)}")
                
                # Small delay to allow system to recover
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Exception processing {file_path}: {str(e)}")
                file_pbar.set_description(f"❌ Exception: {os.path.basename(file_path)}")
        
        # Update batch progress
        batch_pbar.update(1)
        
        # Larger delay between batches
        logger.info(f"Batch {i//batch_size + 1} complete. Sleeping...")
        time.sleep(2)  # Allow system to recover between batches
    
    batch_pbar.close()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process DCS Lua files in batches")
    parser.add_argument("--dir", type=str, required=True, help="Directory containing Lua files")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of files to process in each batch")
    parser.add_argument("--db-url", type=str, default=os.getenv("DATABASE_URL"), 
                        help="PostgreSQL connection string")
    parser.add_argument("--continue-from", type=str, help="Continue from this file path")
    parser.add_argument("--exclude", type=str, nargs="*", default=["XSAF.DB"], 
                        help="Exclude files containing these patterns (default: XSAF.DB)")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.dir):
        logger.error(f"Directory not found: {args.dir}")
        return
    
    try:
        # Get all Lua files excluding specified patterns
        all_files = get_all_lua_files(args.dir, args.exclude)
        logger.info(f"Found {len(all_files)} Lua files in {args.dir} after applying exclusions")
        
        # If continuing from a specific file
        if args.continue_from:
            try:
                start_index = all_files.index(args.continue_from)
                all_files = all_files[start_index:]
                logger.info(f"Continuing from {args.continue_from} ({len(all_files)} files remaining)")
            except ValueError:
                logger.warning(f"File {args.continue_from} not found. Starting from the beginning.")
        
        # Process files in batches
        process_batch(all_files, args.batch_size, args.db_url)
        
        logger.info("All batches completed successfully")
        
    except Exception as e:
        logger.error(f"Error in batch process: {str(e)}")

if __name__ == "__main__":
    main()
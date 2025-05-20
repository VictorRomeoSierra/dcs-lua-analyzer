# DCS Lua Analyzer

A tool for analyzing and working with DCS World Lua scripts using RAG (Retrieval Augmented Generation) to help with scripting questions for Digital Combat Simulator (DCS).

## Features

- Parse DCS Lua scripts using tree-sitter for intelligent code chunking
- Store code chunks in PostgreSQL database for efficient retrieval
- Text-based search for finding relevant code examples
- Vector embeddings using Ollama with nomic-embed-text (optional)
- RAG capabilities with CodeGemma to get accurate answers about DCS scripting
- Support for batch processing large codebases

## Prerequisites

- Python 3.8+
- PostgreSQL database (with pgvector extension for vector search)
- Ollama running with nomic-embed-text and codegemma models

## Installation

1. Clone this repository
2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set up PostgreSQL with pgvector extension:
   ```sql
   \c vectordb
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
5. Copy the `.env.template` file to `.env` and update the settings:
   ```
   cp .env.template .env
   ```

## Scripts Overview

This repository includes several scripts for different purposes:

### 1. lua_embedder.py

Core script for processing Lua files and storing them in the database.

```bash
python lua_embedder.py --dir /path/to/dcs/lua/files
```

Options:
- `--dir`: Directory containing Lua files (required)
- `--limit`: Limit the number of files to process
- `--single-file`: Process only a specific file
- `--db-url`: PostgreSQL connection string (optional, defaults to env var)

### 2. batch_process.py

Process large numbers of Lua files in batches to prevent memory issues.

```bash
python batch_process.py --dir /path/to/dcs/lua/files --batch-size 5 --exclude "XSAF.DB"
```

Options:
- `--dir`: Directory containing Lua files (required)
- `--batch-size`: Number of files to process in each batch (default: 5)
- `--exclude`: Patterns to exclude from processing (default: "XSAF.DB")
- `--continue-from`: Continue processing from a specific file path
- `--db-url`: PostgreSQL connection string (optional, defaults to env var)

### 3. simple_query.py

Basic text search for finding relevant code snippets.

```bash
python simple_query.py "spawn aircraft" --detailed
```

Options:
- `query`: Your search query (required)
- `--limit`: Maximum number of results to return (default: 10)
- `--detailed`: Show detailed results including full code content
- `--info`: Show database table information
- `--db-url`: PostgreSQL connection string (optional, defaults to env var)

### 4. simple_ollama_rag.py

Text search with RAG using collected response (non-streaming).

```bash
python simple_ollama_rag.py "How do I create waypoints for AI aircraft in DCS?" --show-context
```

Options:
- `query`: Your question about DCS Lua scripting (required)
- `--limit`: Number of code snippets to retrieve (default: 5)
- `--show-context`: Show the context sent to the LLM
- `--temperature`: Temperature for the LLM (default: 0.1)
- `--db-url`: PostgreSQL connection string (optional, defaults to env var)

### 5. ollama_stream.py

Text search with RAG using streaming response (live output).

```bash
python ollama_stream.py "How do I control AI helicopters in DCS?" --show-context
```

Options:
- `query`: Your question about DCS Lua scripting (required)
- `--limit`: Number of code snippets to retrieve (default: 5)
- `--show-context`: Show the context sent to the LLM
- `--temperature`: Temperature for the LLM (default: 0.1)
- `--db-url`: PostgreSQL connection string (optional, defaults to env var)

### 6. direct_vector_query.py

Experimental vector search for finding semantically similar code.

```bash
python direct_vector_query.py "spawn aircraft" --detailed
```

Options:
- `query`: Your search query (required)
- `--limit`: Maximum number of results to return (default: 10)
- `--detailed`: Show detailed results including full code content
- `--db-url`: PostgreSQL connection string (optional, defaults to env var)

## Workflow Example

```bash
# Set up the database
python setup_db.py

# Process the XSAF Lua files in batches
python batch_process.py --dir /home/flamernz/Dev/XSAF --batch-size 5 --exclude "XSAF.DB"

# Search for code related to aircraft spawning
python simple_query.py "spawn aircraft" --detailed

# Ask a question using RAG with streaming output
python ollama_stream.py "How do I create waypoints for AI aircraft in DCS?" --show-context
```

## Troubleshooting

- **Memory Issues**: If you encounter memory errors during processing, use the batch_process.py script with a small batch size.
- **Connection Issues**: Ensure Ollama is running and accessible on the configured URL.
- **Database Issues**: Verify PostgreSQL is running and the pgvector extension is installed.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

MIT
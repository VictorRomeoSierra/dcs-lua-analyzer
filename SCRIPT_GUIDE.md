# DCS Lua Analyzer - Quick Script Guide

## Data Processing Scripts

### Process a directory of Lua files
```bash
python lua_embedder.py --dir /path/to/dcs/lua/files
```

### Process files in batches (for large directories)
```bash
python batch_process.py --dir /path/to/dcs/lua/files --batch-size 5 --exclude "XSAF.DB"
```

### Process a single file
```bash
python lua_embedder.py --single-file /path/to/file.lua --dir /path/to
```

## Search and Query Scripts

### Simple text search
```bash
python simple_query.py "spawn aircraft" --detailed
```

### Check database info
```bash
python simple_query.py --info
```

### Ask a question (non-streaming)
```bash
python simple_ollama_rag.py "How do I create waypoints for AI aircraft?" --show-context
```

### Ask a question (live streaming)
```bash
python ollama_stream.py "How do I create waypoints for AI aircraft?" --show-context
```

### Experimental vector search
```bash
python direct_vector_query.py "spawn aircraft" --detailed
```

## Typical Workflow

1. **Setup Database**
   ```bash
   python setup_db.py
   ```

2. **Process Files**
   ```bash
   python batch_process.py --dir /home/flamernz/Dev/XSAF --batch-size 5 --exclude "XSAF.DB"
   ```

3. **Check Data**
   ```bash
   python simple_query.py --info
   ```

4. **Search for Code**
   ```bash
   python simple_query.py "function spawn" --detailed
   ```

5. **Ask Questions**
   ```bash
   python ollama_stream.py "How do I create waypoints for AI aircraft?" --show-context
   ```
# DCS Lua Analyzer Docker Deployment

This guide covers how to deploy the DCS Lua Analyzer API server using Docker and Docker Compose, and how to integrate it with Open WebUI.

## Prerequisites

- Docker and Docker Compose installed
- DCS Lua files you want to analyze
- Open WebUI running in Docker (optional, for integration)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/dcs-lua-analyzer.git
   cd dcs-lua-analyzer
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

   This will start:
   - PostgreSQL database with pgvector extension
   - DCS Lua Analyzer API server

3. Check that both services are running:
   ```bash
   docker-compose ps
   ```

4. Load DCS Lua files into the database:
   ```bash
   # Mount your DCS Lua files directory and run the loader
   docker run --rm \
     --network dcs-lua-analyzer_dcs-network \
     -v /path/to/your/dcs/files:/data \
     dcs-lua-analyzer-api:latest \
     python docker-load-data.py --dir /data
   ```

5. Test the API:
   ```bash
   curl http://localhost:8000/health
   ```

## Configuration

You can customize the deployment by modifying the environment variables in the `docker-compose.yml` file:

- `DATABASE_URL`: PostgreSQL connection string
- `PORT`: Port for the API server (default: 8000)
- `OLLAMA_BASE_URL`: URL for Ollama API (if using Ollama)
- `OLLAMA_EMBEDDING_MODEL`: Embedding model name
- `OLLAMA_LLM_MODEL`: Language model name
- `USE_OLLAMA`: Whether to use Ollama (true/false)

## Database Management

The PostgreSQL database is configured with:
- User: dcs_user
- Password: secure_password (change this for production)
- Database: vectordb
- Port: 5433 (mapped to host)

### Backing Up the Database

```bash
docker-compose exec db pg_dump -U dcs_user vectordb > backup.sql
```

### Restoring the Database

```bash
cat backup.sql | docker-compose exec -T db psql -U dcs_user -d vectordb
```

## Connecting with Open WebUI

To integrate with Open WebUI:

1. Ensure the `api-server` service is configured to connect to the same network as Open WebUI (see the `networks` section in `docker-compose.yml`).

2. Use one of the following methods:
   - Custom Assistant in Open WebUI (recommended)
   - API integration using the `/rag_prompt` endpoint

Refer to `OPEN_WEBUI_INTEGRATION.md` for detailed instructions.

## Production Deployment

For production deployment, consider:

1. Changing the default passwords in `docker-compose.yml` and `init-db.sql`
2. Setting up proper SSL/TLS for the API server
3. Implementing authentication for the API endpoints
4. Limiting CORS to only allow specific origins
5. Using Docker volumes with proper backup strategies
6. Setting up monitoring and logging

## Troubleshooting

If you encounter issues:

- Check container logs: `docker-compose logs api-server`
- Verify database connection: `docker-compose exec db psql -U dcs_user -d vectordb -c "\dt"`
- Ensure network connectivity between containers: `docker-compose exec api-server ping db`
- Validate the API is responding: `curl http://localhost:8000/health`

## Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f api-server

# Rebuild containers
docker-compose build

# Enter container shell
docker-compose exec api-server bash

# Check database tables
docker-compose exec db psql -U dcs_user -d vectordb -c "SELECT COUNT(*) FROM lua_chunks;"
```
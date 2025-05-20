# Database Migration Guide

This guide covers how to use your existing PostgreSQL database with the Docker setup, avoiding the need to redo embeddings.

## Option 1: Connect API Server directly to your existing database

This is the simplest approach if your database is already running and accessible.

### Using Docker network with Open WebUI

1. Use the `docker-compose-api-only.yml` file which only runs the API server:

```bash
docker-compose -f docker-compose-api-only.yml up -d
```

2. Ensure the `DATABASE_URL` in this file points to your existing database.
   - The default configuration uses `host.docker.internal:5433` which allows Docker containers to access services running on your host machine
   - Adjust the connection details (username, password, host, port) as needed

### Using Bridge network mode

If your existing containers (including Open WebUI) use the default bridge network:

1. Use the `docker-compose-bridge.yml` file:

```bash
docker-compose -f docker-compose-bridge.yml up -d
```

2. Communication between containers:
   - In bridge mode, containers communicate using their internal IPs or container names with Docker DNS
   - To access host services (like your database), the file uses `host.docker.internal`
   - For Linux hosts, the `extra_hosts` configuration enables this special DNS name

3. To connect to Open WebUI in bridge mode:
   - Open WebUI will access the API server via the exposed port (8000)
   - Configure Open WebUI to use `http://localhost:8000` or `http://<your-host-ip>:8000` 

## Option 2: Export and import your database

If you want to maintain the complete Docker setup with a containerized database:

### Step 1: Export your existing database

```bash
# Replace these values with your actual database connection details
DB_USER=dcs_user
DB_NAME=vectordb
DB_HOST=localhost
DB_PORT=5433

# Export the database schema and data
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F c -f dcs_lua_analyzer_backup.dump
```

### Step 2: Start the database container only

```bash
# Start just the database container
docker-compose up -d db

# Wait a few seconds for the database to initialize
sleep 10
```

### Step 3: Import data into the containerized database

```bash
# Get the container ID
DB_CONTAINER=$(docker-compose ps -q db)

# Copy the dump file to the container
docker cp dcs_lua_analyzer_backup.dump $DB_CONTAINER:/tmp/

# Restore the database
docker exec -it $DB_CONTAINER pg_restore -U dcs_user -d vectordb -c /tmp/dcs_lua_analyzer_backup.dump

# Clean up
docker exec -it $DB_CONTAINER rm /tmp/dcs_lua_analyzer_backup.dump
```

### Step 4: Start the API server

```bash
# Start the API server
docker-compose up -d api-server
```

## Option 3: Use a Docker volume that points to your existing data

If your PostgreSQL data directory is accessible, you can mount it directly:

1. Modify the `docker-compose.yml` file to mount your existing PostgreSQL data directory:

```yaml
volumes:
  - /path/to/your/existing/postgres/data:/var/lib/postgresql/data
```

2. Ensure the PostgreSQL versions match to avoid compatibility issues.

## Verifying the migration

After migrating, verify that your data is accessible:

```bash
# Check the number of records in the lua_chunks table
docker-compose exec db psql -U dcs_user -d vectordb -c "SELECT COUNT(*) FROM lua_chunks;"

# Test the API server
curl http://localhost:8000/health
curl -X POST http://localhost:8000/search -H "Content-Type: application/json" -d '{"query": "aircraft", "limit": 2}'
```

## Troubleshooting

- **Connection issues**: If the API server can't connect to your database, check firewall settings and ensure the database is configured to accept remote connections.
  
- **Version compatibility**: Ensure your PostgreSQL version is compatible with the pgvector extension version.

- **Permission issues**: Make sure the database user has appropriate permissions on all tables and sequences.

- **Network issues**: 
  - When using bridge mode, you may need to use the host's actual IP address instead of `host.docker.internal`
  - On Mac and Windows, `host.docker.internal` should work by default
  - On Linux, the `extra_hosts` configuration is needed for `host.docker.internal` to work
  
- **Finding container IPs**: If you need to find the IP of a container in bridge mode:
  ```bash
  docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' container_name
  ```
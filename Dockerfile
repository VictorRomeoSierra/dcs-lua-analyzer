FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    curl \
    iputils-ping \
    net-tools \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Verify uvicorn is installed
RUN pip list | grep uvicorn || pip install uvicorn

# Copy application code
COPY . .

# Create an entrypoint script for better error handling
RUN echo '#!/bin/bash\n\
echo "Starting DCS Lua Analyzer API Server..."\n\
echo "Python version: $(python --version)"\n\
echo "Installed packages:"\n\
pip list | grep -E "uvicorn|fastapi|pydantic"\n\
\n\
echo "Checking network connectivity..."\n\
if [[ -n "$DATABASE_URL" ]]; then\n\
  DB_HOST=$(echo $DATABASE_URL | sed -n "s/.*@\\([^:]*\\).*/\\1/p")\n\
  echo "Testing connection to database host: $DB_HOST"\n\
  ping -c 1 $DB_HOST || echo "WARNING: Cannot ping database host"\n\
fi\n\
\n\
if [[ -n "$OLLAMA_BASE_URL" ]]; then\n\
  OLLAMA_HOST=$(echo $OLLAMA_BASE_URL | sed -n "s/http:\\/\\/\\([^:]*\\).*/\\1/p")\n\
  OLLAMA_PORT=$(echo $OLLAMA_BASE_URL | sed -n "s/.*:\\([0-9]*\\).*/\\1/p")\n\
  echo "Testing connection to Ollama at $OLLAMA_HOST:$OLLAMA_PORT"\n\
  if [[ "$OLLAMA_HOST" == "host.docker.internal" ]]; then\n\
    echo "Ollama is configured to use host.docker.internal"\n\
    ping -c 1 host.docker.internal || echo "WARNING: Cannot ping host.docker.internal"\n\
  fi\n\
  curl -s -o /dev/null -w "%{http_code}" $OLLAMA_BASE_URL/api/tags 2>/dev/null || echo "WARNING: Cannot connect to Ollama API"\n\
fi\n\
\n\
echo "Environment variables:"\n\
env | grep -E "DATABASE_URL|OLLAMA|PORT"\n\
\n\
echo "Starting uvicorn server..."\n\
exec uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000} --reload\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
ENTRYPOINT ["/app/entrypoint.sh"]
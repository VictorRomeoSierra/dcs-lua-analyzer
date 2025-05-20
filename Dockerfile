FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    curl \
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
echo "Starting uvicorn server..."\n\
exec uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000} --reload\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
ENTRYPOINT ["/app/entrypoint.sh"]
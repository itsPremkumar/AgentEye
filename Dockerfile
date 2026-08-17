# Agent Search Lite — Docker Image
# Includes SearXNG for self-hosted meta-search

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[all]"

# Copy source
COPY agent_search/ agent_search/

# Install SearXNG
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# SearXNG config
COPY docker/searxng-config.yml /etc/searxng/settings.yml

# Expose ports
EXPOSE 8000 8080

# Start script
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]

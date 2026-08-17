#!/bin/bash
# Agent Search Lite — SearXNG Docker Setup
# One-command setup for self-hosted meta-search

set -e

echo "=== Agent Search Lite — SearXNG Setup ==="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker found"

# Pull and run SearXNG
echo ""
echo "Pulling SearXNG image..."
docker pull searxng/searxng:latest

echo ""
echo "Starting SearXNG on port 8080..."
docker run -d \
    --name searxng-agent-search \
    -p 8080:8080 \
    -v searxng-data:/etc/searxng \
    --restart unless-stopped \
    searxng/searxng:latest

echo ""
echo "Waiting for SearXNG to start..."
sleep 3

# Check health
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ SearXNG is running at http://localhost:8080"
else
    echo "⚠️  SearXNG may still be starting. Wait a few seconds and try:"
    echo "   curl http://localhost:8080/health"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To use SearXNG with Agent Search Lite:"
echo "   The default config already points to http://localhost:8080"
echo ""
echo "To customize settings:"
echo "   docker exec -it searxng-agent-search bash"
echo "   # Edit /etc/searxng/settings.yml"
echo ""
echo "To stop:"
echo "   docker stop searxng-agent-search"
echo ""
echo "To restart:"
echo "   docker start searxng-agent-search"
echo ""
echo "To remove:"
echo "   docker rm -f searxng-agent-search"
echo "   docker volume rm searxng-data"

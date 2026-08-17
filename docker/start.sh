#!/bin/bash
# Start script for Docker container
# Runs both SearXNG and Agent Search Lite MCP server

set -e

echo "=== Agent Search Lite + SearXNG ==="

# Start SearXNG in background
echo "Starting SearXNG..."
dockerd-entrypoint.sh &
sleep 5

# Start MCP server
echo "Starting Agent Search Lite MCP server..."
exec python -m agent_search.mcp_server

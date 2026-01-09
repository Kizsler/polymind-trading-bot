#!/bin/bash
# Wait for PostgreSQL and Redis to be ready

set -e

echo "Waiting for PostgreSQL..."
until docker exec polymind-postgres pg_isready -U postgres > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready!"

echo "Waiting for Redis..."
until docker exec polymind-redis redis-cli ping > /dev/null 2>&1; do
    sleep 1
done
echo "Redis is ready!"

echo "All services are ready!"

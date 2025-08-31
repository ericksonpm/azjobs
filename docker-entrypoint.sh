#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! pg_isready -h db -p 5432 -U azjobs_user; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is up - executing command"

# Start the application
exec "$@"
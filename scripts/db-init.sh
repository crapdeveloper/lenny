#!/bin/sh
set -ex
echo "Initializing database..."
echo ""
echo "Running migrations..."
pdm run alembic -c backend/alembic.ini upgrade head
echo ""
echo "Loading SDE data and queueing market data fetch..."
pdm run python backend/init_database.py
echo ""
echo "✅ Database initialized!"
echo "Market data will be fetched by the worker in the background."

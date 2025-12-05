#!/bin/sh
set -ex
echo "Initializing database..."
echo ""
echo "Running migrations..."
cd backend && alembic upgrade head
echo ""
echo "Loading SDE data and queueing market data fetch..."
cd backend && python init_database.py
echo ""
echo "✅ Database initialized!"
echo "Market data will be fetched by the worker in the background."

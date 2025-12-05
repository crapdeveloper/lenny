#!/bin/sh
set -ex
echo "Running database migrations..."
cd backend && alembic upgrade head

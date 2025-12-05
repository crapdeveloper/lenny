#!/bin/sh
set -ex
echo "Running database migrations..."
pdm run alembic -c backend/alembic.ini upgrade head

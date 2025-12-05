#!/bin/sh
set -ex
echo "Stamping database to head (use after manual schema changes)..."
pdm run alembic -c backend/alembic.ini stamp head

#!/bin/sh
set -ex
echo "Creating new migration revision..."
pdm run alembic -c backend/alembic.ini revision --autogenerate -m "$1"

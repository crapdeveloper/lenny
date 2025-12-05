#!/bin/sh
set -ex
echo "Creating new migration revision..."
cd backend && alembic revision --autogenerate -m "$1"

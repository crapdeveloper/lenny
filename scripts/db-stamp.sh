#!/bin/sh
set -ex
echo "Stamping database to head (use after manual schema changes)..."
cd backend && alembic stamp head

#!/bin/sh
set -ex
echo "Linting backend and frontend..."
pdm run ruff check backend
cd frontend && npm run lint || true

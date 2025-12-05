#!/bin/sh
set -ex
echo "Formatting backend and frontend..."
pdm run black backend
pdm run isort backend
cd frontend && npm run format || true

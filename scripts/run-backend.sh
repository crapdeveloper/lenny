#!/bin/sh
set -ex
echo "Starting backend dev server..."
pdm run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

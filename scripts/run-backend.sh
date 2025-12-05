#!/bin/sh
set -ex
echo "Starting backend dev server..."
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

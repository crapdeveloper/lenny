#!/bin/sh
set -ex
echo "Starting Celery worker (without beat)..."
cd backend && celery -A worker.celery_app worker --loglevel=info

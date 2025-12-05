#!/bin/sh
set -ex
echo "Starting Celery worker with beat scheduler..."
cd backend && celery -A worker.celery_app worker --loglevel=info -B

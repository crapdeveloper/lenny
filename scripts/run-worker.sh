#!/bin/sh
set -ex
echo "Starting Celery worker with beat scheduler..."
pdm run celery -A backend.worker.celery_app worker --loglevel=info -B

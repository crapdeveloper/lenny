#!/bin/sh
set -ex
echo "Starting Celery worker (without beat)..."
pdm run celery -A backend.worker.celery_app worker --loglevel=info

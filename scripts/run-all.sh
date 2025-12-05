#!/bin/sh
set -ex
echo "Starting all services..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
pdm run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
(cd frontend && npm run dev -- --host) &
pdm run celery -A backend.worker.celery_app worker --loglevel=info -B &
wait

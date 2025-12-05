#!/bin/sh
set -ex
echo "Starting all services..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
(cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000) &
(cd frontend && npm run dev -- --host) &
(cd backend && celery -A worker.celery_app worker --loglevel=info -B) &
wait

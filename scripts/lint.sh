#!/bin/sh
set -ex
echo "Linting backend and frontend..."
make -C backend lint || true
cd frontend && npm run lint || true

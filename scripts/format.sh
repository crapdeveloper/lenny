#!/bin/sh
set -ex
echo "Formatting backend and frontend..."
make -C backend format || true
cd frontend && npm run format || true

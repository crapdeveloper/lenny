#!/bin/sh
set -ex
echo "Starting frontend dev server..."
cd frontend && npm run dev -- --host

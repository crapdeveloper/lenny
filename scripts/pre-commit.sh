#!/bin/sh
set -ex
echo "Running pre-commit hooks (all files)..."
pre-commit run --all-files || true
echo "Running frontend lint-staged over staged files (if present)"
cd frontend && npx --no-install lint-staged || true

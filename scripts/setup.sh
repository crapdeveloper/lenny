#!/bin/sh
set -ex
./scripts/frontend-install.sh
./scripts/frontend-prepare.sh
./scripts/backend-install.sh
echo "Setup complete. Run 'pre-commit install' in repo root to enable hooks for Python code."

#!/bin/sh
set -ex
echo "Preparing frontend (husky hooks)..."
echo "Preparing repo-level husky hooks (repo root)."
npm run prepare || true

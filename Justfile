# Justfile: common developer tasks for this repository
# Requires: just (https://github.com/casey/just)

set shell := ['/bin/sh', '-euxc']

# Help (default)
default: help

help:
	@echo "Available tasks:"
	@echo ""
	@echo "  Setup & Installation:"
	@echo "    just dev-setup           # Full interactive setup (env, deps, database)"
	@echo "    just devcontainer-setup  # Auto-setup for devcontainer (installs deps)"
	@echo "    just frontend-install    # Run npm install in ./frontend"
	@echo "    just backend-install     # Install Python dependencies with PDM"
	@echo ""
	@echo "  Running Services:"
	@echo "    just run-frontend        # Start frontend dev server (Vite)"
	@echo "    just run-backend         # Start backend dev server (uvicorn)"
	@echo "    just run-worker          # Start Celery worker with beat scheduler"
	@echo "    just run-all             # Start all services concurrently"
	@echo ""
	@echo "  Database:"
	@echo "    just db-init             # Initialize database (migrations + SDE data)"
	@echo "    just db-migrate          # Run database migrations (alembic upgrade head)"
	@echo "    just db-revision MSG     # Create new migration revision"
	@echo ""
	@echo "  Code Quality:"
	@echo "    just format              # Run formatters for backend and frontend"
	@echo "    just lint                # Run linters for backend and frontend"
	@echo "    just pre-commit          # Run pre-commit checks for repo"
	@echo ""

# ============================================================================
# SETUP COMMANDS
# ============================================================================

frontend-install:
	@./scripts/frontend-install.sh

frontend-prepare:
	@./scripts/frontend-prepare.sh

# This is now a concrete recipe
backend-install:
	@./scripts/backend-install.sh

setup:
	@./scripts/setup.sh

# Devcontainer-specific setup (runs after container creation)
devcontainer-setup:
	@./scripts/devcontainer-setup.sh

# ============================================================================
# RUNNING SERVICES
# ============================================================================

run-frontend:
	@./scripts/run-frontend.sh

run-backend:
	@./scripts/run-backend.sh

run-worker:
	@./scripts/run-worker.sh

run-worker-no-beat:
	@./scripts/run-worker-no-beat.sh

# Run all services concurrently (requires terminal with job control)
run-all:
	@./scripts/run-all.sh

# ============================================================================
# DATABASE COMMANDS
# ============================================================================

db-init:
	@./scripts/db-init.sh

db-migrate:
	@./scripts/db-migrate.sh

db-revision MSG:
	@./scripts/db-revision.sh "{{MSG}}"

db-stamp:
	@./scripts/db-stamp.sh

# ============================================================================
# CODE QUALITY
# ============================================================================

format:
	@./scripts/format.sh

lint:
	@./scripts/lint.sh

pre-commit:
	@./scripts/pre-commit.sh

# ============================================================================
# DEV-SETUP: Complete first-time developer setup
# ============================================================================

# Full interactive development setup
dev-setup:
	@./scripts/dev-setup.sh
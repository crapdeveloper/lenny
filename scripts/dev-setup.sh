#!/bin/bash
set -euo pipefail

# Detect if running in non-interactive mode (e.g., devcontainer postCreateCommand)
if [[ -t 0 ]] && [[ "${TERM:-dumb}" != "dumb" ]]; then
	INTERACTIVE=true
else
	INTERACTIVE=false
	echo "Running in non-interactive mode (devcontainer setup)"
fi

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           🚀 Lenny Development Environment Setup 🚀              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Check if .env exists
if [ -f ".env" ]; then
	echo "✅ Found existing .env file - keeping it."
	SKIP_ENV=true
elif [ "$INTERACTIVE" = false ]; then
	echo "⚠️  No .env file found. Creating minimal defaults for devcontainer."
	echo "   Run 'just dev-setup' later to configure EVE SSO and LLM keys."
	# Create minimal .env with defaults for devcontainer
	SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
	cat > .env <<EOF
# Database (pre-configured for devcontainer)
DATABASE_URL=postgresql+asyncpg://lenny:lenny@db/lenny
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# EVE Online SSO (configure these later with 'just dev-setup')
EVE_CLIENT_ID=
EVE_CLIENT_SECRET=
EVE_CALLBACK_URL=http://localhost:8000/auth/callback

# LLM Provider (configure these later with 'just dev-setup')
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
OPENAI_API_KEY=
GEMINI_API_KEY=

# Security
SECRET_KEY=$SECRET_KEY

# GitHub (optional)
GITHUB_TOKEN=
GITHUB_USERNAME=
EOF
	echo "✅ Created .env with defaults"
	SKIP_ENV=true
else
	echo "⚠️  No .env file found."
	read -r -p "Create .env with configuration wizard? [Y/n]: " create_env
	case "$create_env" in
		[Nn]*) echo "Skipping .env creation."; SKIP_ENV=true ;;
		*) SKIP_ENV=false ;;
	esac
fi
# Step 2: Configure environment variables
if [ "${SKIP_ENV:-}" != "true" ]; then
	echo ""
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Environment Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Press ENTER to accept [default values]"
echo ""
echo "📦 Database & Cache"
read -r -p "  DATABASE_URL [postgresql+asyncpg://lenny:lenny@db/lenny]: " DATABASE_URL
read -r -p "  CELERY_BROKER_URL [redis://redis:6379/0]: " CELERY_BROKER_URL
read -r -p "  CELERY_RESULT_BACKEND [redis://redis:6379/0]: " CELERY_RESULT_BACKEND

echo ""
echo "🎮 EVE Online SSO (get credentials from developers.eveonline.com)"
read -r -p "  EVE_CLIENT_ID: " EVE_CLIENT_ID
read -r -p "  EVE_CLIENT_SECRET: " EVE_CLIENT_SECRET
read -r -p "  EVE_CALLBACK_URL [http://localhost:8000/auth/callback]: " EVE_CALLBACK_URL

echo ""
echo "🤖 LLM Provider"
read -r -p "  LLM_PROVIDER (openai/gemini) [gemini]: " LLM_PROVIDER
read -r -p "  LLM_MODEL [gemini-2.0-flash]: " LLM_MODEL
read -r -p "  OPENAI_API_KEY (if using OpenAI): " OPENAI_API_KEY
read -r -p "  GEMINI_API_KEY (if using Gemini): " GEMINI_API_KEY

echo ""
echo "🔐 Security"
read -r -p "  SECRET_KEY [auto-generate]: " SECRET_KEY

echo ""
echo "🐙 GitHub (optional - for private repos)"
read -r -p "  GITHUB_TOKEN: " GITHUB_TOKEN
read -r -p "  GITHUB_USERNAME: " GITHUB_USERNAME
# Apply defaults
: "${DATABASE_URL:=postgresql+asyncpg://lenny:lenny@db/lenny}"
: "${CELERY_BROKER_URL:=redis://redis:6379/0}"
: "${CELERY_RESULT_BACKEND:=redis://redis:6379/0}"
: "${EVE_CALLBACK_URL:=http://localhost:8000/auth/callback}"
: "${LLM_PROVIDER:=gemini}"
: "${LLM_MODEL:=gemini-2.0-flash}"
if [ -z "$SECRET_KEY" ]; then
	SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
	echo "  → Generated SECRET_KEY automatically"
fi

# Write .env file
cat > .env <<EOF
# Database
DATABASE_URL=$DATABASE_URL
CELERY_BROKER_URL=$CELERY_BROKER_URL
CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND

# EVE Online SSO
EVE_CLIENT_ID=$EVE_CLIENT_ID
EVE_CLIENT_SECRET=$EVE_CLIENT_SECRET
EVE_CALLBACK_URL=$EVE_CALLBACK_URL

# LLM Provider
LLM_PROVIDER=$LLM_PROVIDER
LLM_MODEL=$LLM_MODEL
OPENAI_API_KEY=$OPENAI_API_KEY
GEMINI_API_KEY=$GEMINI_API_KEY

# Security
SECRET_KEY=$SECRET_KEY

# GitHub (optional)
GITHUB_TOKEN=$GITHUB_TOKEN
GITHUB_USERNAME=$GITHUB_USERNAME
EOF
echo ""
echo "✅ .env file created"
fi

# Step 3: Install dependencies
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Installing Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📦 Setting up Python environment (PDM)..."
pdm use 3.11
echo "📦 Installing Python dependencies..."
pdm install

echo ""

echo "📦 Installing frontend dependencies..."
cd frontend && npm install && cd ..
# Step 3: Database Setup
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Database Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$INTERACTIVE" = true ]; then
    read -r -p "Initialize database now? (runs migrations + loads SDE data) [Y/n]: " init_db
else
    echo "Initializing database automatically..."
    init_db="Y"
fi

case "$init_db" in
	[Nn]*) echo "Skipping database initialization. Run 'just db-init' later." ;;
	*)
		echo ""
		echo "🗄️  Running database migrations..."
		cd backend && alembic upgrade head && cd ..
		echo ""
		echo "🗄️  Loading SDE data..."
		cd backend && python init_database.py && cd ..
		echo "✅ Database initialized"
		;;
esac

# Step 4: Configure git (skip in non-interactive mode)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Git Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$INTERACTIVE" = true ]; then
    read -r -p "Configure Git identity globally? (user.name and user.email) [Y/n]: " configure_git
    case "$configure_git" in
        [Nn]*) echo "Skipping Git configuration." ;;
        *)
            read -r -p "  Enter your Git user.name: " GIT_USER_NAME
            read -r -p "  Enter your Git user.email: " GIT_USER_EMAIL

            git config --global user.name "$GIT_USER_NAME"
            git config --global user.email "$GIT_USER_EMAIL"
            echo "✅ Git identity configured globally."
            ;;
    esac
else
    echo "Skipping Git configuration in non-interactive mode."
    echo "Configure later with: git config --global user.name/user.email"
fi

# Done!
echo ""

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ Setup Complete!                            ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
		echo "  • Run 'just run-all' to start all services"
		echo "  • Or press F5 in VS Code to debug"

echo ""
echo "Services will be available at:"
		echo "  • Frontend: http://localhost:3000"
		echo "  • Backend:  http://localhost:8000"
		echo "  • API Docs: http://localhost:8000/docs"
		echo "  • Aspire:   http://localhost:18888"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting infrastructure services (db, redis, aspire-dashboard)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose -f docker-compose.yml up -d db redis aspire-dashboard
echo "✅ Infrastructure services started!"
echo ""
echo "Run 'just run-all' or 'docker compose up -d' to start all app services."
echo ""

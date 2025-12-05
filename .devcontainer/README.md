# Lenny Devcontainer

This devcontainer provides a complete development environment for the Lenny EVE Online Market Dashboard project.

## Prerequisites

- **VS Code** with the [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension
- **Docker Desktop** (or Docker Engine + Docker Compose)

## Important: No Local Mounts

> **⚠️ Security Requirement**: Client code is prohibited from existing on your local workstation. This devcontainer does NOT use local mounts—all source code must exist ONLY inside the Docker container volume.

This means you cannot simply open a local folder and "Reopen in Container". Instead, you must use VS Code's **Clone Repository in Container Volume** feature.

## Quick Start

### Clone Repository in Container Volume

No local checkout required! VS Code clones directly from the Git URL into a Docker volume:

1. **Open VS Code** (with no folder open)

2. **Clone directly into a container volume**

   - Open Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
   - Run: **"Dev Containers: Clone Repository in Container Volume..."**
   - Enter the repository URL: `<repository-url>`
   - VS Code will clone the repo into a Docker volume and build the devcontainer

3. **Complete the setup wizard** (runs automatically in terminal)

   - Configure environment variables (EVE SSO, LLM API keys, etc.)
   - Dependencies install automatically (`pdm install` + `npm install`)
   - Database initializes (migrations + EVE SDE data)
   - Optionally configure Git identity

4. **Start developing!**
   - Press **F5** or use the Run and Debug panel to start services
   - Or run `just run-all` in the terminal

> **Tip**: On subsequent container starts, the setup wizard is skipped. To reconfigure, delete `.devcontainer-initialized` and restart.

## What's Included

### Development Tools

- **Python 3.11** with PDM for dependency management
- **Node.js 20 LTS** for frontend development
- **Just** - Cross-platform command runner
- **Docker CLI** - Run docker commands from inside the container
- **Starship** - Beautiful shell prompt with git info

### Services (Auto-started)

| Service           | Port  | Description                                         |
| ----------------- | ----- | --------------------------------------------------- |
| Frontend (Vite)   | 3000  | React development server                            |
| Backend (FastAPI) | 8000  | API server with Swagger docs at `/docs`             |
| PostgreSQL        | 5432  | Database (pre-configured in VS Code)                |
| Redis             | 6379  | Celery broker and cache (pre-configured in VS Code) |
| Aspire Dashboard  | 18888 | OpenTelemetry traces viewer                         |

### Starship Prompt

The terminal uses [Starship](https://starship.rs/) for an informative prompt showing:

- Current directory
- Git branch and status (modified, staged, ahead/behind)
- Python version and virtualenv
- Node.js version
- Docker context
- Command duration (for slow commands)

## Database & Redis Connections

The PostgreSQL and Redis extensions are pre-configured. Access them from the VS Code sidebar:

- **PostgreSQL**: Click the Database icon → "Lenny Dev PostgreSQL"
- **Redis**: Click the Redis icon → "Lenny Dev Redis"

No manual configuration needed!

## VS Code Debug Configurations

Access via **Run and Debug** panel (`Cmd+Shift+D`) or press `F5`:

| Configuration                       | Description                              |
| ----------------------------------- | ---------------------------------------- |
| **Backend: FastAPI**                | Debug the FastAPI server with hot reload |
| **Frontend: Vite Dev Server**       | Start the Vite dev server                |
| **Frontend: Chrome Debug**          | Launch Chrome with debugger attached     |
| **Worker: Celery**                  | Debug Celery worker with beat scheduler  |
| **Worker: Celery (No Beat)**        | Debug worker without scheduled tasks     |
| **Full Stack (Backend + Frontend)** | Launch both backend and frontend         |
| **Full Stack + Worker**             | Launch all three services                |

## Just Commands

All commands are run via [Just](https://github.com/casey/just), a cross-platform command runner.

### Running Services

```bash
# Start individual services
just run-backend       # FastAPI on port 8000
just run-frontend      # Vite on port 3000
just run-worker        # Celery worker with beat

# Start all services at once
just run-all
```

### Docker Commands

Since Docker CLI is installed, you can run docker commands directly:

```bash
# View worker logs
docker compose logs worker --follow

# View all service logs
docker compose logs --follow

# Restart a service
docker compose restart backend
```

### Database Operations

```bash
# Initialize (first time or reset)
just db-init           # Run migrations + load SDE data

# Apply pending migrations
just db-migrate

# Create new migration
just db-revision "Add new table"

# Stamp database (after manual changes)
just db-stamp
```

### Code Quality

```bash
# Format code
just format

# Run linters
just lint

# Run pre-commit hooks
just pre-commit
```

## Installed VS Code Extensions

The devcontainer automatically installs:

### Python

- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Python Debugger (ms-python.debugpy)
- Black Formatter (ms-python.black-formatter)
- isort (ms-python.isort)
- Ruff (charliermarsh.ruff)

### JavaScript

- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)

### Docker & Databases

- Docker (ms-azuretools.vscode-docker)
- PostgreSQL Client (cweijan.vscode-postgresql-client2)
- Redis Client (cweijan.vscode-redis-client)

### Utilities

- Just (skellock.just)
- Even Better TOML (tamasfe.even-better-toml)
- GitLens (eamodio.gitlens)

## Troubleshooting

### Container won't start

1. Ensure Docker is running
2. Check Docker resources (increase memory/CPU if needed)
3. Try rebuilding: Command Palette → "Dev Containers: Rebuild Container"

### Database connection errors

PostgreSQL takes a few seconds to initialize. The devcontainer waits for it to be healthy, but if you see connection errors:

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# View PostgreSQL logs
docker compose logs db
```

### Port conflicts

If ports are already in use on your host:

1. Stop any local PostgreSQL/Redis instances
2. Or modify `.devcontainer/docker-compose.yml` to use different host ports

### Resetting everything

To start fresh:

```bash
# Stop and remove containers, volumes
docker compose -f .devcontainer/docker-compose.yml down -v

# Rebuild without cache
docker compose -f .devcontainer/docker-compose.yml build --no-cache
```

Then reopen in VS Code.

## Environment Variables

The devcontainer loads environment variables from `.env` in the project root. Ensure you have configured:

```ini
# EVE Online API (required for SSO)
EVE_CLIENT_ID=your_client_id
EVE_CLIENT_SECRET=your_client_secret
EVE_CALLBACK_URL=http://localhost:8000/auth/callback

# LLM Provider (for AI features)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key

# Or use OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_api_key
```

Database and Redis URLs are automatically configured by the devcontainer.

#!/bin/sh
set -e

# Activate virtual environment
. /pdm/.venv/bin/activate

# Execute the command passed to the script
exec "$@"

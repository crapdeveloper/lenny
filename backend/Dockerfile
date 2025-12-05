FROM python:3.11-slim

WORKDIR /pdm

# Install PDM
RUN pip install --upgrade pip && pip install pdm

# Copy project files
COPY pyproject.toml pdm.lock README.md /pdm/

# Install dependencies using PDM (without installing the project itself)
RUN pdm config python.use_venv true
RUN pdm install --prod --no-editable

WORKDIR /app

# Copy backend code
COPY backend /app

# Use the PDM virtual environment
ENV PATH="/pdm/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

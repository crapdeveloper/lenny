Formatting and linting
======================

This project uses Black, isort and Ruff for formatting and linting. We also use pre-commit to run these checks automatically on commit.

Local setup
-----------

1. Create a virtual environment and install tools:

   python -m venv .venv
   . .venv/bin/activate
   pip install -U pip
   pip install black isort ruff pre-commit

2. Install the git hooks via pre-commit:

   pre-commit install

3. Format code or run checks manually:

   make -C backend format    # Format
   make -C backend lint      # Lint

Using in Docker
---------------

If you prefer running formatters inside Docker (matching CI), you can run the commands inside the running backend container or via a temporary container using the project's Python image.

CI
--

Add a CI step to run 'pre-commit run --all-files' or use the individual commands above to enforce style in PRs.

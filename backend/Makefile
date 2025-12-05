.PHONY: format lint check

format:
	black .
	isort .

lint:
	ruff check .

check: format lint

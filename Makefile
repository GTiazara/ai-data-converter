.PHONY: help install test lint format-check run check run-sklearn

APP ?= ia-convert
ARGS ?= --help
SKLEARN_CONF ?= conf/sklearn.yaml

help:
	@echo "install       Install dependencies"
	@echo "test          Run tests"
	@echo "lint          Check code with Ruff"
	@echo "format-check  Check formatting with Ruff"
	@echo "run           Run the application (APP=... ARGS=...)"
	@echo "run-sklearn   Export a scikit-learn toy dataset (SKLEARN_CONF=...)"
	@echo "check         Run tests and lint"

install:
	poetry install

test:
	poetry run pytest

lint:
	poetry run ruff check .

format-check:
	poetry run ruff format --check .

run:
	poetry run $(APP) $(ARGS)

run-sklearn:
	poetry run ia-convert --config $(SKLEARN_CONF)

check: lint test

# local development commands
run-dev:
	poetry run ia-convert --config conf/conf.yaml


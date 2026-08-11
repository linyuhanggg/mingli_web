.DEFAULT_GOAL := help

.PHONY: help install test check backend-test backend-check web-test web-check admin-typecheck build migrate worker-once

help:
	@echo "install       Install locked backend and web dependencies"
	@echo "test          Run backend, contract, and web tests"
	@echo "check         Run lint, type checks, tests, and production web build"
	@echo "migrate       Upgrade the configured PostgreSQL database to Alembic head"
	@echo "worker-once   Run one non-blocking Worker iteration"
	@echo "admin-typecheck  Typecheck the independent admin console"

install:
	uv sync --project backend --group dev
	npm install --prefix web
	npm install --prefix admin

backend-test:
	uv run --project backend pytest backend/tests tests/contract -q

backend-check: backend-test
	uv run --project backend ruff check --config backend/pyproject.toml backend tests
	uv run --project backend mypy --config-file backend/pyproject.toml backend/app backend/worker

web-test:
	npm --prefix web test

web-check: web-test
	npm --prefix web run lint
	npm --prefix web run typecheck

admin-typecheck:
	npm --prefix admin run typecheck

test: backend-test web-test

build:
	npm --prefix web run build

check: backend-check web-check build

migrate:
	uv run --project backend alembic -c backend/alembic.ini upgrade head

worker-once:
	uv run --directory backend python -m worker.main --once

.DEFAULT_GOAL := help

.PHONY: help bootstrap fetch-documents format lint typecheck test test-integration audit dead-code qa dev down-all

help:
	@just --list

bootstrap:
	@just bootstrap

fetch-documents:
	@just fetch-documents

format:
	@uv run ruff format backend
	@cd frontend && npm run format

lint:
	@uv run ruff check backend
	@cd frontend && npm run lint

typecheck:
	@uv run mypy backend/src
	@cd frontend && npm run typecheck

test:
	@uv run pytest backend/tests/unit
	@cd frontend && npm run test -- --run

test-integration:
	@uv run pytest backend/tests/integration

audit:
	@uv run pip-audit

dead-code:
	@uv run vulture backend/src --min-confidence 100

qa: lint typecheck test test-integration audit dead-code

dev:
	@just dev

down-all:
	@just down-all

# Written with AI assistance (Claude Code). See AI_USE.md.
# ARIADNE commands: the single source of truth for local work and CI.
# CI runs these on Linux. On Windows, run them from Git Bash with GNU make (choco install make).

SITE ?= boxwork

ifeq ($(OS),Windows_NT)
  PYTHON ?= python
  VENV_BIN := .venv/Scripts
else
  PYTHON ?= python3
  VENV_BIN := .venv/bin
endif
PY := $(VENV_BIN)/python
NPM := npm --prefix web

.PHONY: help setup setup-python setup-web setup-browsers \
	fetch derive plan validate package site \
	test test-python test-web lint guardrails licenses build-web e2e web-dev

help:
	@echo "make setup            create .venv and install the web dependencies"
	@echo "make fetch SITE=x     download or window-read sources (Phase 1)"
	@echo "make derive SITE=x    build the derived layers (Phase 2)"
	@echo "make plan SITE=x      build the leg matrix and reference plans (Phase 3)"
	@echo "make validate         run every check and write validation.json (Phase 2)"
	@echo "make package SITE=x   write tiles, GeoJSON and the manifest (Phase 4)"
	@echo "make site SITE=x      run all of the above in order"
	@echo "make test             pipeline and web tests"
	@echo "make e2e              browser tests on the production build"
	@echo "make web-dev          local dev server"
	@echo "make lint | guardrails | licenses | build-web"

# Setup

setup: setup-python setup-web

setup-python:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "pipeline[dev]"

setup-web:
	$(NPM) ci

setup-browsers:
	$(NPM) exec -- playwright install --with-deps chromium

# Data pipeline. Commands not built yet exit with code 2 and name their phase.
# derive needs the shielding calibration, which comes from the Murray Buttes crops: run
# `make fetch SITE=murray-buttes` once before deriving any site.

fetch derive validate package:
	$(PY) -m ariadne $@ --site $(SITE)

# plan also runs the browser solver's benchmark against the OR-Tools plans it writes.
plan:
	$(PY) -m ariadne plan --site $(SITE)
	cd web && BENCH_OUT=docs/validation/station-solver.json npx vitest run tests/solver.test.ts

site: fetch derive plan validate package

# Checks

test: test-python test-web

test-python:
	cd pipeline && ../$(PY) -m pytest -q

test-web:
	$(NPM) run typecheck
	$(NPM) test

lint:
	$(PY) -m ruff check pipeline
	$(PY) -m ruff format --check pipeline

guardrails:
	$(PY) -m ariadne.guardrails headers
	$(PY) -m ariadne.guardrails secrets
	$(PY) -m ariadne.guardrails trailers

licenses:
	$(NPM) run licenses

# Web

build-web:
	$(NPM) run build

e2e: build-web
	$(NPM) run e2e

web-dev:
	$(NPM) run dev

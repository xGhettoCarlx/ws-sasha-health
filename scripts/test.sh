#!/bin/bash
set -e
pytest -v --cov=app --cov-report=term-missing "$@"

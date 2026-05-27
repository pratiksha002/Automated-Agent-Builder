#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies
pip install --no-cache-dir -r requirements.txt

# Run migrations using Alembic
alembic upgrade head


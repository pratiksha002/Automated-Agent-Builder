#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies
pip install --no-cache-dir -r requirements.txt

# Run migrations using Alembic
alembic upgrade head

# Run your seed file to populate Groq and Ollama models
python seed.py
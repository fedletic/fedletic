#!/bin/bash

DB_NAME="fedletic"
DB_USER="postgres"  # Change if needed
VENV_DIR=".venv"  # Adjust if your virtualenv is named differently

echo "⚠️  WARNING: This will DROP the PostgreSQL database and DELETE all migrations! Continue? (y/n)"
read -r confirm

if [[ $confirm != "y" ]]; then
    echo "Aborted."
    exit 1
fi

echo "🗑  Detecting Django apps and deleting migrations (keeping __init__.py)..."

# Automatically find all Django apps (ignores .venv, venv, and other non-app directories)
APPS=$(find . -maxdepth 1 -type d ! -name "$(basename $VENV_DIR)" ! -name "venv" ! -name ".git" ! -name "__pycache__" ! -name "migrations" | cut -c 3-)

for app in $APPS; do
    if [[ -d "$app/migrations" ]]; then
        find "$app/migrations/" -type f -name "*.py" ! -name "__init__.py" -delete
        find "$app/migrations/" -type f -name "*.pyc" -delete
    fi
done

echo "🗑  Dropping and recreating PostgreSQL database..."
dropdb $DB_NAME
createdb $DB_NAME

echo "🚀 Running migrations..."
python manage.py makemigrations
python manage.py migrate

echo "✅ PostgreSQL database and migrations have been reset."

#!/bin/bash

# django-addcommand - A script to generate Django management commands
# Usage: django-addcommand <appname> <commandname>

# Check if correct number of arguments provided
if [ $# -ne 2 ]; then
    echo "Error: Requires exactly two arguments."
    echo "Usage: django-addcommand <appname> <commandname>"
    exit 1
fi

# Store arguments
APP_NAME=$1
COMMAND_NAME=$2

# Validate app name (check if directory exists)
if [ ! -d "$APP_NAME" ]; then
    echo "Error: App '$APP_NAME' directory not found in current location."
    echo "Make sure you're in the Django project root directory."
    exit 1
fi

# Create management directory structure if it doesn't exist
MANAGEMENT_DIR="$APP_NAME/management"
COMMANDS_DIR="$MANAGEMENT_DIR/commands"

if [ ! -d "$MANAGEMENT_DIR" ]; then
    echo "Creating management directory for $APP_NAME..."
    mkdir -p "$MANAGEMENT_DIR"
    touch "$MANAGEMENT_DIR/__init__.py"
fi

if [ ! -d "$COMMANDS_DIR" ]; then
    echo "Creating commands directory for $APP_NAME..."
    mkdir -p "$COMMANDS_DIR"
    touch "$COMMANDS_DIR/__init__.py"
fi

# Create the command file
COMMAND_FILE="$COMMANDS_DIR/${COMMAND_NAME}.py"

if [ -f "$COMMAND_FILE" ]; then
    echo "Warning: Command file already exists at $COMMAND_FILE"
    read -p "Do you want to overwrite it? (y/n): " OVERWRITE
    if [ "$OVERWRITE" != "y" ]; then
        echo "Operation cancelled."
        exit 0
    fi
fi

# Write the command template to the file
cat > "$COMMAND_FILE" << EOF
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Description of what the ${COMMAND_NAME} command does'

    def add_arguments(self, parser):
        # Add command line arguments
        # Example: parser.add_argument('--example', help='Example argument')
        pass

    def handle(self, *args, **options):
        # Command implementation goes here
        self.stdout.write('Running ${COMMAND_NAME} command')
        
        # Example success message:
        self.stdout.write(self.style.SUCCESS('${COMMAND_NAME} command completed successfully'))
EOF

echo "Created management command: $COMMAND_FILE"
echo "You can now use this command with: python manage.py $COMMAND_NAME"

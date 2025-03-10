#!/bin/bash

# Define paths
SCRIPT_PATH="./bin/pre-commit.sh"
HOOK_DIR=".git/hooks"
HOOK_PATH="${HOOK_DIR}/pre-commit"

# Make sure the script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: ${SCRIPT_PATH} does not exist."
    echo "Please create this file before setting up the hook."
    exit 1
fi

# Make sure the script is executable
if [ ! -x "$SCRIPT_PATH" ]; then
    echo "Making ${SCRIPT_PATH} executable..."
    chmod +x "$SCRIPT_PATH"
fi

# Make sure we're in a Git repository
if [ ! -d ".git" ]; then
    echo "Error: This does not appear to be a Git repository."
    echo "Please run this script from the root of your Git repository."
    exit 1
fi

# Create hooks directory if it doesn't exist
if [ ! -d "$HOOK_DIR" ]; then
    echo "Creating hooks directory..."
    mkdir -p "$HOOK_DIR"
fi

# Remove existing pre-commit hook if it exists
if [ -e "$HOOK_PATH" ]; then
    echo "Removing existing pre-commit hook..."
    rm "$HOOK_PATH"
fi

# Create the symlink
echo "Creating symlink to pre-commit script..."
ABSOLUTE_PATH="$(pwd)/${SCRIPT_PATH}"
ln -s "$ABSOLUTE_PATH" "$HOOK_PATH"

# Verify the setup
if [ -L "$HOOK_PATH" ] && [ -x "$SCRIPT_PATH" ]; then
    echo "Success! Pre-commit hook has been set up."
    echo "The hook will run automatically before each commit."
else
    echo "Error: Failed to set up the pre-commit hook."
    exit 1
fi

exit 0
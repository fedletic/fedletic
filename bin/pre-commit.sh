#!/usr/bin/env bash

# =========================================================================
# Enhanced Pre-Commit Hook for Python Projects
#
# This script runs code quality checks before allowing commits:
# - Flake8: Checks for style guide compliance and errors
# - isort: Ensures imports are sorted consistently
# - black: Enforces consistent code formatting
# =========================================================================

# Define colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner function for visual separation of steps
print_banner() {
    echo -e "\n${BLUE}======================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}======================================================${NC}\n"
}

# Run flake8
print_banner "Running flake8 to check for code quality issues"
flake8 .
if [ "$?" -ne "0" ]; then
    echo -e "${RED}flake8 found some issues${NC}.\n${YELLOW}Fix these before you commit.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ flake8 checks passed${NC}"

# Run isort and check for changes
print_banner "Running isort to check import sorting"
isort_result=$(isort . --profile black)
if [[ $isort_result =~ "Fixing" ]]; then
    echo -e "${RED}isort made some changes, please add them before you commit.${NC}"
    echo -e "${YELLOW}Files changed:${NC}"
    changed_files=$(git diff --name-only)
    echo $changed_files
    exit 1
fi
echo -e "${GREEN}✓ isort checks passed${NC}"

# Run black and check for changes
print_banner "Running black to check code formatting"
STATUS_BEFORE=$(git status --porcelain)
black .
STATUS_AFTER=$(git status --porcelain)
if [ "$STATUS_BEFORE" != "$STATUS_AFTER" ]; then
    echo -e "${RED}black made some changes, please add them before you commit.${NC}"
    echo -e "${YELLOW}Files changed:${NC}"
    git diff --name-only
    exit 1
fi
echo -e "${GREEN}✓ black checks passed${NC}"

# All checks passed
print_banner "All checks passed!"
echo -e "${GREEN}Your code meets all style and quality requirements.${NC}"
echo -e "${GREEN}Proceeding with commit...${NC}"

exit 0
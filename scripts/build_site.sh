#!/bin/bash
set -e

# Sync SUMMARY.md to index.md
echo "Syncing docs/SUMMARY.md to docs/index.md..."
cp docs/SUMMARY.md docs/index.md

# Handle commands
if [ "$1" = "serve" ]; then
    echo "Starting local Zensical preview server..."
    zensical serve
else
    echo "Building static site..."
    zensical build --clean
fi

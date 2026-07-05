#!/bin/bash
set -e

# Sync SUMMARY.md to index.md
echo "Syncing docs/SUMMARY.md to docs/index.md..."
cp docs/SUMMARY.md docs/index.md

# Temporarily move docs/superpowers out of docs directory to exclude it from Zensical build
if [ -d "docs/superpowers" ]; then
    echo "Temporarily moving docs/superpowers to exclude from build..."
    mv docs/superpowers ./superpowers_tmp
fi

# Set trap to clean up and restore docs/superpowers on exit
trap '
  rm -f docs/index.md
  if [ -d "./superpowers_tmp" ]; then
      echo "Restoring docs/superpowers..."
      mv ./superpowers_tmp docs/superpowers
  fi
' EXIT

# Handle commands
if [ "$1" = "serve" ]; then
    echo "Starting local Zensical preview server..."
    zensical serve
else
    echo "Building static site..."
    zensical build --clean
fi

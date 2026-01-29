#!/bin/bash
set -e

TOKEN="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"

#!/bin/bash
set -e

APP_DIR="$HOME/viewdx"

if [ ! -d "$APP_DIR/.git" ]; then
  echo "ERROR: App directory is not a git repository"
  exit 1
fi

cd "$APP_DIR"

git fetch origin
git checkout main
git pull origin main

echo "Update completed successfully"


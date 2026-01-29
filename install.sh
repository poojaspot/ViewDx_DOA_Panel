#!/bin/bash
set -e

TOKEN="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"

APP_DIR="$HOME/ViewDx_DOA_Panel"
REPO_URL="https://github.com/poojaspot/ViewDx_DOA_Panel.git"
BRANCH="main"

if [ ! -d "$APP_DIR" ]; then
  echo "App directory not found. Cloning repository..."
  git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  echo "App directory found. Updating repository..."
  cd "$APP_DIR"
  git fetch origin
  git checkout "$BRANCH"
  git pull origin "$BRANCH"
fi

echo "Application setup/update completed successfully"



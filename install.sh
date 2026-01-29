#!/bin/bash
set -e

TOKEN="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"

RUNTIME_DIR="/home/pi/viewdx"
TMP_DIR="/tmp/viewdx_update"
REPO_URL="https://github.com/poojaspot/ViewDx_DOA_Panel.git"
BRANCH="main"

echo "Starting ViewDx update..."

rm -rf "$TMP_DIR"
git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$TMP_DIR"

echo "Syncing application files (preserving customer-specific data)..."

rsync -av --update \
  --exclude 'deviceinfo.py' \
  --exclude 'Certificate_of_warranty.pdf' \
  --exclude 'Installation_report.pdf' \
  --exclude 'config.json' \
  --exclude 'results/' \
  --exclude 'captured/' \
  --exclude 'qr/' \
  --exclude 'hardwaretest/' \
  --exclude 'usesummary/' \
  --exclude 'addl_logo.png' \
  --exclude 'bottom_logo.png' \
  --exclude 'lab_logo.png' \
  --exclude 'logo.png' \
  --exclude 'splash.png' \
  ----exclude 'splash_logo.png' \
  "$TMP_DIR"/ "$RUNTIME_DIR"/

rm -rf "$TMP_DIR"

echo "Update completed successfully (customer data preserved)"



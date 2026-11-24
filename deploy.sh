#!/usr/bin/env bash
# Deploy the First Global Standard Bank site.
#
# There are TWO places that must stay in sync on the server:
#   1. /home/ubuntu/dhio-bank  -> the Flask app (API + database), run by
#                                 the `dhiobank` systemd service. Served at
#                                 dhiobank.13-48-31-7.sslip.io.
#   2. /var/www/fgsb           -> the static frontend users actually visit at
#                                 firstglobalstandardbank.13-48-31-7.sslip.io
#                                 (nginx serves these files directly).
#
# This script pulls the latest code, restarts the API, and copies the current
# frontend into the FGSB web root so BOTH domains always match. Run it on the
# server after pushing changes:   bash /home/ubuntu/dhio-bank/deploy.sh
set -euo pipefail

APP_DIR=/home/ubuntu/dhio-bank
WEB_DIR=/var/www/fgsb

cd "$APP_DIR"

echo "==> Pulling latest code from git"
git pull origin main

echo "==> Restarting API service (dhiobank)"
sudo systemctl restart dhiobank.service

echo "==> Syncing static frontend to $WEB_DIR (firstglobalstandardbank)"
sudo mkdir -p "$WEB_DIR/icons"
sudo cp "$APP_DIR"/*.html "$WEB_DIR"/
sudo cp -r "$APP_DIR"/icons/. "$WEB_DIR"/icons/
# Copy PWA/manifest assets if present (ignore any that don't exist)
for f in manifest.json admin-manifest.json sw.js _redirects; do
  [ -f "$APP_DIR/$f" ] && sudo cp "$APP_DIR/$f" "$WEB_DIR"/ || true
done
sudo chown -R www-data:www-data "$WEB_DIR"

echo "==> Done. Live on BOTH:"
echo "    - https://dhiobank.13-48-31-7.sslip.io (app/API)"
echo "    - https://firstglobalstandardbank.13-48-31-7.sslip.io (static frontend)"

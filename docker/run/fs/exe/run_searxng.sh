#!/bin/bash

# start webapp
sudo -H -u searxng -i
cd /usr/local/searxng/searxng-src
export SEARXNG_SETTINGS_PATH="/etc/searxng/settings.yml"

while true; do
    python searx/webapp.py

    # Optional: Add a small delay if needed to avoid rapid restarts
    sleep 1
done

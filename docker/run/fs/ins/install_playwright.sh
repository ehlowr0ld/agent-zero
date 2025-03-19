#!/bin/bash

set -e
set -o pipefail

# activate venv
. "/ins/setup_venv.sh" "$@"

# install chromium with dependencies
# for kali-based
. /etc/os-release
if [ "$ID" = "kali" ]; then
    apt-get install -y fonts-unifont libnss3 libnspr4
    playwright install chromium-headless-shell
else
    # for debian based
    playwright install --with-deps chromium-headless-shell
fi

#!/bin/bash

set -e
set -o pipefail

# install playwright here to respect the playwright version from requirements.txt
bash /ins/install_playwright.sh "$@"

# Cleanup package list
rm -rf /var/lib/apt/lists/*
apt-get clean

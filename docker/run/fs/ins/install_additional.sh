#!/bin/bash

set -e

# searxng
bash /ins/install_searxng.sh "$@"

# playwright
bash /ins/install_playwright.sh "$@"

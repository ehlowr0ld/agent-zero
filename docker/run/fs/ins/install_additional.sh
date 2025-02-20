#!/bin/bash

set -e
set -o pipefail

# install playwright
# bash /ins/install_playwright.sh "$@"
#moved to post_install.sh to respect the playwright version from requirements.txt

# searxng
bash /ins/install_searxng.sh "$@"

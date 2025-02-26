#!/bin/bash

set -e

# activate venv
. "/ins/setup_venv.sh" "$@"

# install playwright
pip install playwright==1.50.0

# install chromium with dependencies
playwright install --with-deps chromium

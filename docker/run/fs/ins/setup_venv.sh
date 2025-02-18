#!/bin/bash

if [ ! -d /opt/venv ]; then
    # Create and activate Python virtual environment
    set -e
    python -m venv --without-pip /opt/venv
    wget -qO- https://bootstrap.pypa.io/get-pip.py > /tmp/get-pip.py && \
      /opt/venv/bin/python /tmp/get-pip.py --force --break-system-packages && \
      rm /tmp/get-pip.py
    /opt/venv/bin/python -m pip config set global.break-system-packages true
    /opt/venv/bin/python -m ensurepip --upgrade
    source /opt/venv/bin/activate
else
    set -e
    source /opt/venv/bin/activate
fi

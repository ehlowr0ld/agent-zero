#!/bin/bash

set -e
set -o pipefail

# Update and install necessary packages
apt-get update && apt-get install -y \
    -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
    python3.12 \
    python3-pip \
    python3.12-venv \
    nodejs \
    npm \
    openssh-server \
    sudo \
    curl \
    wget \
    git \
    ffmpeg \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    qpdf \
    libreoffice \
    pandoc \
    libgtk-3-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libasound2 \
    libasound2-data \
    nginx

# Configure system alternatives so that /usr/bin/python3 points to Python 3.12
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
sudo update-alternatives --set python3 /usr/bin/python3.12

# Update pip3 symlink: if pip3.12 exists, point pip3 to it;
# otherwise, install pip using Python 3.12's ensurepip.
if [ -f /usr/bin/pip3.12 ]; then
  sudo ln -sf /usr/bin/pip3.12 /usr/bin/pip3
else
  # python3 -m ensurepip --upgrade
  python3 -m pip config set global.break-system-packages true
  # This will work but exit code is != 0 because pip is managed by apt
  python3 -m pip install --upgrade pip || true
fi

# Install npx for use by local MCP Servers
npm i -g npx shx

# Prepare SSH daemon
bash /ins/setup_ssh.sh "$@"

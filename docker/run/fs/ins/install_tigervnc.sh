#!/bin/bash
set -e

# activate venv
. "/ins/setup_venv.sh" "$@"

DEBIAN_FRONTEND=noninteractive apt-get install -y \
    xserver-xorg-video-dummy \
    xinit \
    x11-xserver-utils \
    xserver-xorg-core \
    tigervnc-standalone-server \
    tigervnc-tools \
    cinnamon-desktop-environment \
    --no-install-recommends

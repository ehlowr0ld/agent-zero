#!/bin/bash
set -e

# activate venv
. "/ins/setup_venv.sh" "$@"

apt-get update && apt-get install \
    -o Dpkg::Options::="--force-confdef" \
    -o Dpkg::Options::="--force-confold" \
    -y \
    tigervnc-standalone-server \
    tigervnc-tools websockify \
    dbus dbus-x11 net-tools \
    curl sudo apt-transport-https gnupg \
    xvfb novnc dbus-x11 x11vnc \
    kali-defaults kali-desktop-${KALI_DESKTOP} xfce4-goodies \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    # x11vnc

# Creating user agent-zero if not exists
if ! getent passwd $VNC_USER > /dev/null; then
    echo "$VNC_USER user not found, creating..."
    useradd -m -s /bin/bash $VNC_USER
    echo "$VNC_USER:$VNC_PASS" | chpasswd
    echo "$VNC_USER ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
fi

# create also passwd for x11vnc
if [ ! -f /etc/x11vnc.passwd ]; then
    echo "Creating VNC password file..."
    echo "$VNC_PASS" | vncpasswd -f > /etc/x11vnc.passwd
    test -f /etc/x11vnc.passwd || { echo "Failed to create VNC password file"; exit 1; }
fi

# create also passwd for tightvnc
if [ ! -f /root/.vnc/passwd ]; then
    echo "Creating VNC password file..."
    vncpasswd -f <<<"$VNC_PASS"$'\n'"viewer" >"/root/.vnc/passwd"
    test -f /root/.vnc/passwd || { echo "Failed to create VNC password file"; exit 1; }
fi

if [ ! -f /etc/tigervnc/vncserver.users ] || ! grep -q "$VNC_USER" /etc/tigervnc/vncserver.users; then
    echo "Creating VNC server users file..."
    echo ":1=$VNC_USER" > /etc/tigervnc/vncserver.users
fi

if [ ! -f /etc/tigervnc/passwd ]; then
    echo "Creating VNC password file..."
    echo "$VNC_PASS" | vncpasswd -f > /etc/tigervnc/passwd
    test -f /etc/tigervnc/passwd || { echo "Failed to create VNC password file"; exit 1; }
fi

chown -R agent-zero:agent-zero /etc/tigervnc
chmod 0400 /etc/tigervnc/*

update-alternatives --set x-session-manager /usr/bin/xfce4-session

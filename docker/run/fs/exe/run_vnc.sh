#!/bin/bash

# Wait until run_tunnel.py exists
echo "Starting VNC..."

if getent passwd agent-zero > /dev/null; then
    echo "Agent-zero user not found, creating..."
    useradd -m -s /bin/bash agent-zero
    echo "agent-zero:agent0" | chpasswd
    echo "agent-zero ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
fi

if [ ! -f /etc/tigervnc/vncserver.users ] || [ ! grep -q "agent-zero" /etc/tigervnc/vncserver.users ]; then
    echo "Creating VNC server users file..."
    echo ":1=agent-zero" > /etc/tigervnc/vncserver.users
fi

if [ ! -f /etc/tigervnc/passd ]; then
    echo "Passwd file missing, can't start VNC server..."
    exit 1
fi

chown -R agent-zero:agent-zero /etc/tigervnc
chmod 0400 /etc/tigervnc/vncserver.users
# agent0 pass
chmod 0400 /etc/tigervnc/passd

rm -f /tmp/.X11-unix/X1
mkdir -p /run/vncserver
chown agent-zero:agent-zero /run/vncserver


exec /usr/libexec/tigervncsession-start :1

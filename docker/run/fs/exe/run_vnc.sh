#!/bin/bash

# Wait until run_tunnel.py exists
echo "Starting VNC..."

rm -f /tmp/.X*-lock /tmp/.X11-unix/X*
mkdir -p /run/vncserver
chown $VNC_USER:$VNC_USER /run/vncserver

# exec /usr/bin/tigervncserver :1 -rfbport 5901 -rfbauth /etc/tigervnc/passwd -fg
# exec /usr/bin/x11vnc -forever -rfbport 5901 -rfbauth /root/passwd -fg
# exec x11vnc -display :0 -randr 1920x1080 -auth guess -forever -loop -noxdamage -repeat -rfbauth /etc/x11vnc.passwd -rfbport 5901 -shared

# exec /usr/bin/vncserver $DISPLAY -fg −UseBlacklist "no"
# exec x11vnc -display "$DISPLAY" -geometry 1920x1080 -xkb -forever -shared -repeat -listen 0.0.0.0 -nopw -reopen -rfbport 5901 -rfbauth /etc/tigervnc/passwd -fg
export USER=$VNC_USER
exec Xtightvncs $DISPLAY -name xfce4 -rfbport 5901 -SecurityTypes=none -rfbauth /root/.vnc/passwd -geometry 1920x1080 -depth 24 -interface 0.0.0.0 -alwaysshared

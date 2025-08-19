#!/bin/bash

# Set password for VNC

set -e

rm -rf /tmp/.X11-unix/X0
rm -rf /tmp/.X0-lock

if [ $VNCEXPOSE = 1 ]
then
  # Expose VNC
  vncserver $DISPLAY -rfbport $VNCPORT -geometry $VNCDISPLAY -depth $VNCDEPTH \
    > /var/log/vncserver.log 2>&1
else
  # Localhost only
  vncserver $DISPLAY -rfbport $VNCPORT -geometry $VNCDISPLAY -depth $VNCDEPTH -localhost \
    > /var/log/vncserver.log 2>&1
fi

# Start noVNC server

if [ ! -f /etc/ssl/certs/novnc_cert.pem -o ! -f /etc/ssl/private/novnc_key.pem ]
then
  openssl req -new -x509 -days 365 -nodes \
    -subj "/C=US/ST=IL/L=Springfield/O=OpenSource/CN=localhost" \
    -out /etc/ssl/certs/novnc_cert.pem -keyout /etc/ssl/private/novnc_key.pem \
    > /dev/null 2>&1
fi

# cat /etc/ssl/certs/novnc_cert.pem /etc/ssl/private/novnc_key.pem > /etc/ssl/private/novnc_combined.pem
# chmod 600 /etc/ssl/private/novnc_combined.pem

/usr/share/novnc/utils/novnc_proxy --listen $NOVNCPORT --vnc localhost:$VNCPORT \
  > /var/log/novnc.log 2>&1 &
  #   --cert /etc/ssl/private/novnc_combined.pem --ssl-only \

echo "Launch your web browser and open https://localhost:$NOVNCPORT/vnc.html"
echo "Verify the certificate fingerprint:"
openssl x509 -in /etc/ssl/certs/novnc_cert.pem -noout -fingerprint -sha256

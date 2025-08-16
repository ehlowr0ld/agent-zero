#!/bin/bash

set -ex
USER=${USER:-root}
GUI_COMMAND=$( ( which startxfce4 || which startlxde || which startkde || which gdm3 )2>/dev/null )
if [[ "$USER" != "root" ]]; then
    exec su -c "$GUI_COMMAND" "$USER"
else
    exec "$GUI_COMMAND"
fi

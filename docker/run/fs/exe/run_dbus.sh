#!/bin/bash

set -e
mkdir -p /run/dbus
rm -rf /run/dbus/*
# export DBUS_SESSION_BUS_ADDRESS='autolaunch:'
DBUS_SESSION_BUS_ADDRESS=unix:path=/var/run/dbus/session
exec dbus-daemon --session --address=$DBUS_SESSION_BUS_ADDRESS --nofork

#!/bin/bash

set -e
mkdir -p /run/dbus
rm -rf /run/dbus/*
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
exec dbus-daemon --session --address=$DBUS_SESSION_BUS_ADDRESS --nofork

#!/bin/bash

set -e
exec websockify --web=/usr/share/novnc/ 6081 localhost:5901

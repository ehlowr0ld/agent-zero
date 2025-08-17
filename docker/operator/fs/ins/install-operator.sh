#!/bin/bash

set -e

cat <<EOF >> /etc/supervisor/conf.d/supervisord.conf

# DBUS
[program:run_dbus]
command=/exe/run_dbus.sh
environment=
user=root
stopwaitsecs=60
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autorestart=true
startretries=3
stopasgroup=true
killasgroup=true

# VNC server
[program:run_operator]
command=/exe/run_operator.sh
environment=
user=root
startsecs = 0
stopwaitsecs=60
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autorestart=false
startretries=3
stopasgroup=true
killasgroup=true
EOF

if [ "$HOST_UID" -a "$DOCKER_UID" != "$HOST_UID" ]; then
    usermod -u $HOST_UID $DOCKER_USER 2> /dev/null
fi
if [ "$HOST_GID" -a "$DOCKER_GID" != "$HOST_GID" ]; then
    groupmod -g $HOST_GID $DOCKER_GROUP 2> /dev/null
fi

if [ -e '/etc/container_environment.sh' ]; then
    source /etc/container_environment.sh
fi

# Make sure that all the directories in $HOME are accessible by the user.
if [ -n "$HOST_UID" -a "$DOCKER_UID" != "$HOST_UID" -o \
    -n "$HOST_GID" -a "$DOCKER_GID" != "$HOST_GID" ]; then
    find $DOCKER_HOME -maxdepth 1 -type d -not -path "./shared" | sed "1d" | \
        xargs chown $DOCKER_USER:$DOCKER_GROUP 2> /dev/null || true

    # It is important for $HOME/.ssh to have correct ownership
    chown -R $DOCKER_USER:$DOCKER_GROUP $DOCKER_HOME/.ssh
    chown -R $DOCKER_USER:$DOCKER_GROUP $DOCKER_HOME/.config
elif [ -d $DOCKER_HOME/project ]; then
    chown -R $DOCKER_USER:$DOCKER_GROUP $DOCKER_HOME/project
fi

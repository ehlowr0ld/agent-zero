# Use the pre-built image for A0

FROM agent0ai/agent-zero:latest


ARG DOCKER_LANG=en_US
ARG DOCKER_TIMEZONE=America/New_York
ARG X11VNC_VERSION=latest

ENV LANG=$DOCKER_LANG.UTF-8 \
    LANGUAGE=$DOCKER_LANG:UTF-8 \
    LC_ALL=$DOCKER_LANG.UTF-8

ENV DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket

WORKDIR /tmp

ARG DEBIAN_FRONTEND=noninteractive

# Install some required system tools and packages for X Windows and ssh.
# Also remove the message regarding unminimize.
# Note that Ubuntu 22.04 uses snapd for firefox, which does not work properly,
# so we install it from ppa:mozillateam/ppa instead.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        apt-utils \
        apt-file \
        locales && \
    locale-gen $LANG && \
    dpkg-reconfigure -f noninteractive locales && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        less \
        vim \
        psmisc \
        runit \
        apt-transport-https ca-certificates \
        software-properties-common \
        man \
        sudo \
        rsync \
        libarchive-tools \
        net-tools \
        gpg-agent \
        inetutils-ping \
        csh \
        tcsh \
        zsh zsh-autosuggestions \
        build-essential autoconf automake autotools-dev pkg-config \
        libssl-dev \
        git \
        dos2unix \
        dbus-x11 \
        python3-pip \
        python3-setuptools \
        \
        openssh-server \
        \
        xserver-xorg-video-dummy \
        lxde \
        x11-xserver-utils xdotool \
        xterm \
        gtk2-engines-pixbuf \
        gtk2-engines-murrine \
        libcanberra-gtk3-module \
        fonts-liberation \
        xfonts-base xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-cyrillic \
        libopengl0 mesa-utils libglu1-mesa libgl1-mesa-dri libjpeg9 libjpeg62-turbo \
        xauth xdg-utils \
        x11vnc novnc && \
    chmod 755 /usr/local/share/zsh/site-functions && \
    apt-get -y autoremove && \
    ssh-keygen -A && \
    bash -c "test ! -f /lib64/ld-linux-x86-64.so.2 || ln -s -f /lib64/ld-linux-x86-64.so.2 /lib64/ld-lsb-x86-64.so " && \
    perl -p -i -e 's/#?X11Forwarding\s+\w+/X11Forwarding yes/g; \
        s/#?X11UseLocalhost\s+\w+/X11UseLocalhost no/g; \
        s/#?PasswordAuthentication\s+\w+/PasswordAuthentication no/g; \
        s/#?PermitEmptyPasswords\s+\w+/PermitEmptyPasswords no/g' \
        /etc/ssh/sshd_config && \
    rm -f /etc/update-motd.d/??-unminimize && \
    rm -f /etc/xdg/autostart/lxpolkit.desktop && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


# Fix issue with Shift-Tab not working
RUN perl -e 's/,\s*ISO_Left_Tab//g' -p -i /usr/share/X11/xkb/symbols/pc


########################################################
# Customization for user and location
########################################################
# Set up user so that we do not run as root in DOCKER
ENV DOCKER_USER=agent-zero \
    DOCKER_UID=9999 \
    DOCKER_GID=9999 \
    DOCKER_SHELL=/bin/zsh

ENV DOCKER_GROUP=$DOCKER_USER \
    DOCKER_HOME=/home/$DOCKER_USER \
    SHELL=$DOCKER_SHELL


# Change the default timezone to $DOCKER_TIMEZONE
# Run ldconfig so that /usr/local/lib etc. are in the default
# search path for dynamic linker
RUN groupadd -g $DOCKER_GID $DOCKER_GROUP && \
    useradd -m -u $DOCKER_UID -g $DOCKER_GID -s $DOCKER_SHELL -G sudo $DOCKER_USER && \
    echo "$DOCKER_USER:"`openssl rand -base64 12` | chpasswd && \
    echo "$DOCKER_USER ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    echo "$DOCKER_TIMEZONE" > /etc/timezone && \
    ln -s -f /usr/share/zoneinfo/$DOCKER_TIMEZONE /etc/localtime

ADD fs/image/etc /etc
ADD fs/image/usr /usr
ADD fs/image/sbin /sbin
ADD fs/image/home $DOCKER_HOME
ADD fs/ins/install-operator.sh /ins/install-operator.sh
RUN chmod +x /ins/install-operator.sh
ADD fs/exe/run_dbus.sh /exe/run_dbus.sh
ADD fs/exe/run_operator.sh /exe/run_operator.sh
RUN chmod +x /exe/*

# Make home directory readable to work with Singularity
RUN mkdir -p $DOCKER_HOME/.config/mozilla && \
    ln -s -f .config/mozilla $DOCKER_HOME/.mozilla && \
    touch $DOCKER_HOME/.sudo_as_admin_successful && \
    mkdir -p $DOCKER_HOME/shared && \
    mkdir -p $DOCKER_HOME/.ssh && \
    mkdir -p $DOCKER_HOME/.log && touch $DOCKER_HOME/.log/vnc.log && \
    chown -R $DOCKER_USER:$DOCKER_GROUP $DOCKER_HOME && \
    chmod -R a+r $DOCKER_HOME && \
    find $DOCKER_HOME -type d -exec chmod a+x {} \;

WORKDIR $DOCKER_HOME

USER root

RUN /ins/install-operator.sh

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

# Network manager
[program:network_manager]
command=/usr/sbin/NetworkManager --no-daemon
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
stopsignal=QUIT
killasgroup=true

# syslog
[program:syslog]
command=/sbin/syslogd -n
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
stopsignal=QUIT
killasgroup=true
EOF

mkdir -p /root/packages
cd /root/packages

apt update
DEBIAN_FRONTEND=noninteractive \
apt install -y ca-certificates

echo "deb [arch=i386,amd64,armel,armhf,arm64] https://kali.download/kali kali-bleeding-edge main contrib non-free" > /etc/apt/sources.list.d/kali-bleeding-edge.list
echo "deb [arch=i386,amd64,armel,armhf,arm64] https://kali.download/kali kali-dev main contrib non-free" > /etc/apt/sources.list.d/kali-dev.list > /etc/apt/sources.list.d/kali-dev.list
echo "deb [arch=i386,amd64,armel,armhf,arm64] https://kali.download/kali kali-dev main/debian-installer" > /etc/apt/sources.list.d/kali-dev.list
echo "deb [arch=i386,amd64,armel,armhf,arm64] https://kali.download/kali kali-experimental main contrib non-free non-free-firmware" > /etc/apt/sources.list.d/kali-experimental.list

apt update

DEBIAN_FRONTEND=noninteractive \
apt install -y libexpat1 python3-pip-whl python3-setuptools-whl media-types \
mime-support media-types libx11-6 libjs-mathjax libgdbm6t64 libncursesw6 libreadline8t64 \
libexpat1-dev zlib1g-dev netbase net-tools libfontconfig1 libxft2 libxss1 libgdbm6t64 python3

if apt -y install wget; then

wget https://http.kali.org/pool/main/p/python3.13/libpython3.13_3.13.6-1_amd64.deb  https://http.kali.org/pool/main/p/python3.13/libpython3.13-stdlib_3.13.6-1_amd64.deb https://http.kali.org/pool/main/p/python3.13/python3.13-full_3.13.6-1_amd64.deb https://http.kali.org/pool/main/p/python3.13/python3.13_3.13.6-1_amd64.deb
wget https://http.kali.org/pool/main/p/python3.13/libpython3.13-testsuite_3.13.3-2_all.deb https://http.kali.org/pool/main/p/python3.13/python3.13-dev_3.13.6-1_amd64.deb
wget https://http.kali.org/pool/main/p/python3.13/python3.13-minimal_3.13.5-2_amd64.deb https://http.kali.org/pool/main/p/python3.13/python3.13-tk_3.13.6-1_amd64.deb
wget https://http.kali.org/pool/main/p/python3.13/libpython3.13-minimal_3.13.6-1_amd64.deb
wget https://http.kali.org/pool/main/p/python3.13/libpython3.13-dbg_3.13.6-1_amd64.deb
wget https://http.kali.org/pool/main/p/python3.13/python3.13-gdbm_3.13.6-1_amd64.deb
wget https://http.kali.org/pool/main/p/python3.13/python3.13-venv_3.13.6-1_amd64.deb https://http.kali.org/pool/main/p/python3.13/idle-python3.13_3.13.6-1_all.deb
wget https://http.kali.org/pool/main/p/python3.13/libpython3.13-dev_3.13.6-1_amd64.deb
wget https://http.kali.org/pool/main/p/python3.13/python3.13-minimal_3.13.6-1_amd64.deb
apt download libtcl8.6
apt download libtk8.6
apt download python3-tk
apt download python3 blt
apt download tk8.6-blt2.5
apt download python3-minimal

fi

DEBIAN_FRONTEND=noninteractive \
dpkg --force-all -i  libpython3.13-minimal* python3-minimal* python3.13-minimal*  python3-* python3.13-tk* libtcl8.6* libtk8.6* tk8.6-blt2.5* blt* python3-tk*


DEBIAN_FRONTEND=noninteractive \
dpkg --force-all -i *

DEBIAN_FRONTEND=noninteractive \
dpkg --configure -a

apt-get update && \
apt-get dist-upgrade -y && \
apt-get -y upgrade && \
apt-get -y install kali-themes && \
DEBIAN_FRONTEND=noninteractive \
apt-get -y install \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold" \
    curl \
    dbus \
    dbus-user-session \
    dbus-x11 \
    iputils-ping \
    less \
    lightdm \
    novnc \
    mousepad \
    nano \
    net-tools \
    network-manager \
    psmisc \
    rsync \
    sudo \
    thunar \
    thunar-archive-plugin \
    thunar-gtkhash \
    tightvncserver \
    vim \
    xdg-user-dirs-gtk \
    xdg-utils \
    xfce4 \
    xfce4-cpugraph-plugin \
    xfce4-genmon-plugin \
    xfce4-goodies \
    xfce4-power-manager-plugins \
    xfce4-screensaver \
    xfce4-screenshooter \
    xfce4-taskmanager \
    xfce4-whiskermenu-plugin \
    xserver-xorg-legacy \
    zenmap \
    mate-calc \
    mate-desktop-environment \
    mate-polkit \
    mate-system-monitor \
    mate-terminal \
    mate-utils \
    kali-archive-keyring \
    kali-defaults-desktop \
    kali-desktop-base \
    kali-desktop-core \
    kali-desktop-mate \
    kali-desktop-xfce \
    kali-grant-root \
    kali-linux-core \
    kali-menu \
    kali-system-gui \
    kali-themes-common \
    kali-tools-top10 \
    kali-defaults-desktop \
    kali-grant-root \
    software-properties-common \
    kali-archive-keyring \
    kali-menu \
    kali-system-gui \
    kali-themes-common \
    xfonts-base xfonts-100dpi xfonts-75dpi \
    kali-tools-top10 wmctrl tightvncpasswd --no-install-recommends \
    libpthread-stubs0-dev libxau-dev libxcb1-dev libxdmcp-dev libxext-dev libxfixes-dev \
    libxi-dev x11proto-dev xorg-sgml-doctools xtrans-dev \
    libx11-dev libxau-dev libxcb1-dev libxdmcp-dev  libxext-dev libxfixes-dev libxi-dev \
    libxinerama-dev libxkbcommon-dev libxtst-dev --no-install-recommends \
    gimp imagemagick shutter gnome-screenshot thunar-media-tags-plugin \
    openssh-client git curl wget nodejs npm htop glances vim tmux copyq libreoffice \
    busybox-syslogd && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

# Creating user agent-zero if not exists
if ! getent passwd $VNC_USER > /dev/null; then
    echo "$VNC_USER user not found, creating..."
    useradd -m -s /bin/bash $VNC_USER
    echo "$VNC_USER:$VNC_PASS" | chpasswd
    echo "$VNC_USER ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
fi
# create also passwd for tightvnc
if [ ! -f /root/.vnc/passwd ]; then
    echo "Creating VNC password file..."
    mkdir -p /root/.vnc/
    echo $VNCPWD | vncpasswd -f > /root/.vnc/passwd
    chmod 600 /root/.vnc/passwd
    test -f /root/.vnc/passwd || { echo "Failed to create VNC password file"; exit 1; }
fi

git clone https://github.com/jordansissel/xdotool /root/xdotool
cd /root/xdotool
git checkout edbbb7a8f664ceacbb2cffbe8ee4f5a26b5addc8
make static
chmod 777 xdotool.static
mv xdotool.static /usr/local/bin/xdotool

DEBIAN_FRONTEND=noninteractive \
apt purge -y libpthread-stubs0-dev  libx11-dev  libxau-dev  libxcb1-dev  libxdmcp-dev  libxext-dev  libxfixes-dev  libxi-dev  libxinerama-dev  libxkbcommon-dev  libxtst-dev  x11proto-dev  xorg-sgml-doctools  xtrans-dev

# First, install the package
DEBIAN_FRONTEND=noninteractive \
apt install -y golang

# Then add the following to your .bashrc
echo "export GOROOT=/usr/lib/go" >> ~/.bashrc
echo "export GOPATH=$HOME/go" >> ~/.bashrc
echo "export PATH=$GOPATH/bin:$GOROOT/bin:$PATH" >> ~/.bashrc

# for developer agent
go install github.com/isaacphi/mcp-language-server@latest

mkdir -p /root/.config/xfce4
touch /root/.config/xfce4/helpers.rc
echo "WebBrowser=firefox" >> /root/.config/xfce4/helpers.rc
echo "TerminalEmulator=xfce4-terminal" >> /root/.config/xfce4/helpers.rc


# Create desktop shortcuts directory if not exists
mkdir -p ~/Desktop

# Set up basic panel configuration
xfce4-panel --add=launcher
xfce4-panel --add=menu
xfce4-panel --add=clock
xfce4-panel --add=tasklist
xfce4-panel --add=notification-area
xfce4-panel --add=launcher
xfce4-panel --add=menu
xfce4-panel --add=clock
xfce4-panel --add=tasklist
xfce4-panel --add=notification-area

update-alternatives --set x-session-manager /usr/bin/xfce4-session

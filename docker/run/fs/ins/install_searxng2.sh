#!/bin/bash

set -e

# clone SearXNG repo
git clone "https://github.com/searxng/searxng" \
                   "/usr/local/searxng/searxng-src"

# create virtualenv:
python -m venv --without-pip "/usr/local/searxng/searx-pyenv"
wget -qO- https://bootstrap.pypa.io/get-pip.py > /tmp/get-pip.py && \
      /usr/local/searxng/searx-pyenv/bin/python /tmp/get-pip.py --force --break-system-packages && \
      rm /tmp/get-pip.py
/usr/local/searxng/searx-pyenv/bin/python -m pip config set global.break-system-packages true
/usr/local/searxng/searx-pyenv/bin/python -m ensurepip --upgrade

# make it default
echo ". /usr/local/searxng/searx-pyenv/bin/activate" \
                   >>  "/usr/local/searxng/.profile"

# activate venv
source "/usr/local/searxng/searx-pyenv/bin/activate"

# update pip's boilerplate
pip install -U pip
pip install -U setuptools
pip install -U wheel
pip install -U pyyaml
pip install -U babel

# jump to SearXNG's working tree and install SearXNG into virtualenv
cd "/usr/local/searxng/searxng-src"
pip install --use-pep517 --no-build-isolation -e .

# cleanup cache
pip cache purge

#!/bin/bash

set -e

# Cleanup package list
rm -rf /var/cache/apt/* /var/lib/apt/lists/*
apt-get clean

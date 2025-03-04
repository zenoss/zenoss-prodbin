#!/usr/bin/bash

# Ensure there's a login-like environment
source /home/zenoss/.bashrc

# Run the tests
echo
echo Test the 'zenoss' package
python2 /opt/zenoss/bin/runtests.py

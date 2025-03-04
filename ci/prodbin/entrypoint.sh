#!/bin/bash

LOCAL_GID=$(stat -c "%g" .)
if [ "$LOCAL_GID" -ne "0" ]; then
	if [ "$LOCAL_GID" -ne "$(id -g zenoss)" ]; then
		groupmod -g $LOCAL_GID zenoss
	fi
fi

LOCAL_UID=$(stat -c "%u" .)
if [ "$LOCAL_UID" -ne "0" ]; then
	if [ "$LOCAL_UID" -ne "$(id -u zenoss)" ]; then
		usermod -u $LOCAL_UID zenoss
	fi
fi

find /opt/zenoss -type d -exec chown zenoss:zenoss {} \+
chown zenoss:zenoss /opt/zenoss/bin/*
find /home/zenoss -type d -exec chown zenoss:zenoss {} \+

exec gosu zenoss "$@"

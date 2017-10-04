#! /usr/bin/env bash
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

help() {
    echo "usage:"
    echo "   nagios-plugins help"
    echo "   nagios-plugins download"
    echo "   nagios-plugins install"
    return 1
}

COMMON_NAME="nagios-common"
COMMON_VER="4.0.8"

PLUGIN_NAMES="nagios-plugins nagios-plugins-perl nagios-plugins-dig nagios-plugins-dns nagios-plugins-http nagios-plugins-ircd nagios-plugins-ldap nagios-plugins-ntp nagios-plugins-ping nagios-plugins-rpc nagios-plugins-tcp"
PLUGIN_VER="2.1.4"

PKG_SUFFIX="2.sdl7.x86_64.rpm"

download() {
    DEST=/root/rpm/nagios
    if [[ ! -z "$1" ]]; then
        DEST=$1
        shift
    fi
    mkdir -p $DEST
    URL_BASE="http://get.zenoss.io/yum/zenoss/stable/centos/el7/os/x86_64"

    FILENAME=$COMMON_NAME-$COMMON_VER-$PKG_SUFFIX
    URL="$URL_BASE/$FILENAME"
    echo "Downloading $COMMON_NAME..."
    wget "$URL" -O "$DEST/$FILENAME"
    RC=$?
    if [ $RC -ne 0 ]; then
        echo "Error downloading $COMMON_NAME!"
        return $RC
    fi

    for PLUGIN_NAME in $PLUGIN_NAMES; do
        FILENAME=$PLUGIN_NAME-$PLUGIN_VER-$PKG_SUFFIX
        URL="$URL_BASE/$FILENAME"
        echo "Downloading $PLUGIN_NAME..."
        wget "$URL" -O "$DEST/$FILENAME"
        RC=$?
        if [ $RC -ne 0 ]; then
            echo "Error downloading $PLUGIN_NAME!"
            return $RC
        fi
    done
	return 0
}

install() {
    # /usr/sbin/rpcinfo is needed for nagios-plugins-rpc.
    yum install -y rpcbind
	RC=$?
    if [ $RC -ne 0 ]; then
        echo "Error installing rpcbind! rpcbind is needed for installing nagios-plugins-rpc."
        return $RC
    fi

    DEST=/root/rpm/nagios
    if [[ ! -z "$1" ]]; then
        DEST=$1
        shift
    fi
    pushd $DEST
    yum localinstall -y $COMMON_NAME-$COMMON_VER-$PKG_SUFFIX
    for PLUGIN_NAME in $PLUGIN_NAMES; do
        yum localinstall -y $PLUGIN_NAME-$PLUGIN_VER-$PKG_SUFFIX
        RC=$?
        if [ $RC -ne 0 ]; then
            echo "Error installing $PLUGIN_NAME!"
            return $RC
        fi
    done
    popd
    return 0
}

if [[ "$1" == "install" ]]; then
    shift
    install $@
elif [[ "$1" == "download" ]]; then
	shift
  	download $@
else
    help
fi
return $?

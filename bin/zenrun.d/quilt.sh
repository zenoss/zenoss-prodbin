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
    echo "   quilt help"
    echo "   quilt install"
    return 1
}


install() {
    URL="http://download.savannah.gnu.org/releases/quilt/quilt-0.64.tar.gz"

    echo "Downloading quilt sources: $URL"
    curl -L "$URL" | tar -C /tmp -xz

    RC=$?
    if [ $RC -ne 0 ]; then
        echo "Error downloading quilt!"
        return $RC
    fi

    echo "Compiling quilt..."
    cd /tmp/quilt-0.64 && ./configure --prefix=/opt/zenoss/var/ext && make && make install

    return $?
}


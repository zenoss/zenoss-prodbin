#! /usr/bin/env bash
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


install(){
    ZVAR="/var/zenoss"
    PERCONADIR="${ZVAR}/percona"
    URL="http://www.percona.com/downloads/percona-toolkit/2.2.12/tarball/percona-toolkit-2.2.12.tar.gz"
    if [ ! -d ${ZVAR} ]; then
      echo "No such directory: ${ZVAR}"
      return 1
    fi

    mkdir -p "${PERCONADIR}" || return "$?"

    echo "Downloading percona toolkit: ${URL}"
    curl -L ${URL} |tar -xzv  --strip-components=1 -C ${PERCONADIR}
    RC=$?
    if [[ $RC != 0 ]]; then
        echo "Error downloading percona!"
        return "$RC"
    fi

    return 0
}

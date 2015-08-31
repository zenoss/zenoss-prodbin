#! /usr/bin/env bash
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__DEFAULT__() {
    # start up a zope instance that we can hit
    echo "Starting zope..."
    zopectl start
    reportmail "$@"
    return $?
}

help() {
    echo "usage:"
    echo "   reportmail help"
    echo "   reportmail <report_url>"
    echo "       --version             show program's version number and exit"
    echo "       -h, --help            show this help message and exit"
    echo "       -C CONFIGFILE, --configfile=CONFIGFILE"
    echo "       Use an alternate configuration file"
    echo "       --genconf             Generate a template configuration file"
    echo "       --genxmltable         Generate a Docbook table showing command-line"
    echo "       switches."
    echo "       --genxmlconfigs       Generate an XML file containing command-line switches."
    echo "       -u URL, --url=URL     URL of report to send"
    echo "       -r REPORTFILETYPE, --reportFileType=REPORTFILETYPE"
    echo "                       report file type (PDF|PNG|JPG|GIF)"
    echo "       -U USER, --user=USER  User to log into Zenoss"
    echo "       -p PASSWD, --passwd=PASSWD Password to log into Zenoss"
    echo "       -a ADDRESSES, --address=ADDRESSES"
    echo "                       Email address destination (may be given more than"
    echo "                       once).  Default valuecomes from the user's profile."
    echo "       -s SUBJECT, --subject=SUBJECT"
    echo "                       Subject line for email message.Default value is the"
    echo "                       title of the html page."
    echo "       -f FROMADDRESS, --from=FROMADDRESS"
    echo "                       Origination address"
    echo "       "
    return 1
}

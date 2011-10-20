#!/usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import sys
from optparse import OptionParser
from amqplib.client_0_8.connection import Connection

import Globals
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

class Main(object):

    def __init__(self):
        self._global_conf = getGlobalConfiguration()

    def _get_setting(self, name):
        val = self._global_conf.get(name, None)
        if val is None:
            print >> sys.stderr, "global.conf setting %s must be set."
            sys.exit(1)
        return val

    def verify(self, expected_version):
        
        hostname = self._get_setting('amqphost')
        port     = self._get_setting('amqpport')
        username = self._get_setting('amqpuser')
        password = self._get_setting('amqppassword')
        vhost    = self._get_setting('amqpvhost')
        ssl      = self._get_setting('amqpusessl')
        use_ssl  = True if ssl in ('1', 'True', 'true') else False

        conn = None
        rc = 0
        try:
            conn = Connection(host="%s:%s" % (hostname, port), userid=username,
                      password=password, virtual_host=vhost, ssl=use_ssl)
            server_version = conn.server_properties.get('version')
            e_ver = tuple(int(v) for v in expected_version.split('.'))
            s_ver = tuple(int(v) for v in server_version.split('.'))
            if s_ver < e_ver:
                print >> sys.stderr, "Server version: %s < Expected version: %s" % (
                    server_version, expected_version)
                rc = 1
        finally:
            if conn:
                conn.close()
        sys.exit(rc)

if __name__=="__main__":
    
    epilog = "Verifies connectivity with the amqp server configued in global.conf."
    parser = OptionParser(epilog=epilog)
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_usage()
        sys.exit(1)

    main = Main()
    main.verify(args[0])




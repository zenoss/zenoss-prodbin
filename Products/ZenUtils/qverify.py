#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys
from optparse import OptionParser
from amqplib.client_0_8.connection import Connection
from contextlib import closing

import Globals
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

import logging
LOG = logging.getLogger("zen.qverify")

def _addSetting(name, settings, globalSettings, default=None):
    setting = globalSettings.get(name, default)
    if setting is not None:
        settings[name] = setting

_ZEN_AMQP_SETTINGS =  {
   'amqphost': 'localhost',
   'amqpport': 5672,
   'amqpuser': 'zenoss',
   'amqppassword': 'zenoss',
   'amqpvhost': '/zenoss',
   'amqpusessl': False,
   'amqpadminport': 55672,
   'amqpadminusessl': False,
}

class ZenAmqp(object):

    def __init__(self):
        self._global_conf = getGlobalConfiguration()

    def _getSettings(self, admin, extraParams=None):
        sslkey = 'amqpadminusessl' if admin else 'amqpusessl'
        port = 'amqpadminport' if admin else 'amqpport'
        zenSettings = {}
        for setting, default in _ZEN_AMQP_SETTINGS.iteritems():
            _addSetting(setting, zenSettings, self._global_conf, default)
        if extraParams:
            zenSettings.update(extraParams)
        ssl = zenSettings.get(sslkey, False) in ('1', 'True', 'true', 1, True)
        settings = {
            'host': '%s:%s' % (zenSettings['amqphost'], zenSettings[port]),
            'userid': '%(amqpuser)s' % zenSettings,
            'password': '%(amqppassword)s' % zenSettings,
            'virtual_host': '%(amqpvhost)s' % zenSettings,
            'ssl': ssl,
        }
        # provide a method for overriding system supplied values
        if extraParams:
            for name, value in extraParams.iteritems():
                if name not in _ZEN_AMQP_SETTINGS:
                    settings[name] = value
        return settings

    def getAdminConnectionSettings(self, extraParams=None):
        return self._getSettings(admin=True, extraParams=extraParams)

    def getConnectionSettings(self, extraParams=None):
        return self._getSettings(admin=False, extraParams=extraParams)

    def getConnection(self):
        settings = self.getConnectionSettings()
        return Connection(**settings)

    def getVersion(self):
        with closing(self.getConnection()) as conn:
             return conn.server_properties.get('version')

class Main(object):

    def __init__(self, verbose=False):
        self._verbose = verbose

    def verify(self, expected_version):
        rc = 1
        try:
            server_version = ZenAmqp().getVersion()
            e_ver = tuple(int(v) for v in expected_version.split('.'))
            s_ver = tuple(int(v) for v in server_version.split('.'))
            if s_ver < e_ver:
                print >> sys.stderr, "Server version: %s < Expected version: %s" % (
                    server_version, expected_version)
                rc = 2
            else:
                if self._verbose:
                    print "Server version: %s" % server_version
                rc = 0
        except Exception as e:
            print >> sys.stderr, "Error determining RabbitMQ version: %s" % e
            rc = 1
        sys.exit(rc)

if __name__=="__main__":
    usage = "%prog VERSION_NUMBER" 
    epilog = "Verifies connectivity with the amqp server configued in global.conf and " \
             "checks if server version is >= VERSION_NUMBER. Returns exit code 1 if " \
             "connection fails, 2 if server version < VERSION_NUMBER, and 0 if " \
             "connection is OK and server version >= VERSION_NUMBER."
    parser = OptionParser(usage=usage, epilog=epilog)
    parser.add_option("--verbose", "-v", default=False, action='store_true')
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    main = Main(options.verbose)
    main.verify(args[0])

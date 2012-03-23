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

    def getAdminConnectionSettings(self, extraParams={}):
        zenSettings = {}
        for setting, default in _ZEN_AMQP_SETTINGS.items():
            _addSetting(setting, zenSettings, self._global_conf, default)
        zenSettings.update(extraParams)
        ssl = zenSettings.get('amqpadminusessl', False) in ('1', 'True', 'true', 1, True) 
        settings = { 
            'host': '%(amqphost)s:%(amqpadminport)s' % zenSettings,
            'userid': '%(amqpuser)s' % zenSettings,
            'password': '%(amqppassword)s' % zenSettings,
            'virtual_host': '%(amqpvhost)s' % zenSettings,
            'ssl': ssl,
        }
        # provide a method for overriding system supplied values
        for name, value in extraParams.items():
            if name not in _ZEN_AMQP_SETTINGS:
                settings[name] = value
        return settings

    def getConnectionSettings(self, extraParams={}):
        zenSettings = {}
        for setting, default in _ZEN_AMQP_SETTINGS.items():
            _addSetting(setting, zenSettings, self._global_conf, default)
        zenSettings.update(extraParams)
        ssl = zenSettings.get('amqpusessl', False) in ('1', 'True', 'true', 1, True) 
        settings = { 
            'host': '%(amqphost)s:%(amqpport)s' % zenSettings,
            'userid': '%(amqpuser)s' % zenSettings,
            'password': '%(amqppassword)s' % zenSettings,
            'virtual_host': '%(amqpvhost)s' % zenSettings,
            'ssl': ssl,
        }
        # provide a method for overriding system supplied values
        for name, value in extraParams.items():
            if name not in _ZEN_AMQP_SETTINGS:
                settings[name] = value
        return settings

    def getConnection(self):
        settings = self.getConnectionSettings()
        return Connection(**settings)

class Main(object):

    def __init__(self, verbose=False):
        self._verbose = verbose
        LOG.debug("Getting global conf")
        self._global_conf = getGlobalConfiguration()

    def _get_setting(self, name):
        val = self._global_conf.get(name, None)
        if val is None:
            print >> sys.stderr, "global.conf setting %s must be set." % name
            sys.exit(1)
        return val

    def verify(self, expected_version):
        conn = None
        rc = 1
        try:
            # verify all settings exist
            for setting in _ZEN_AMQP_SETTINGS:
                self._get_setting(setting)
            conn = ZenAmqp().getConnection()
            server_version = conn.server_properties.get('version')
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
        finally:
            if conn:
                conn.close()
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




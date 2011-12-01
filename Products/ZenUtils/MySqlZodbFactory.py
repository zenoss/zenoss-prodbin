###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""MySqlZodbConnection
"""

import optparse
import sys
import os
from zope.interface import implements
import ZODB
import relstorage.storage 
import relstorage.adapters.mysql
import relstorage.options
import _mysql_exceptions as db_exceptions


from GlobalConfig import globalConfToDict
from ZodbFactory import IZodbFactory

def _getDefaults(options=None):
    if options is None:
       o = globalConfToDict()
    else:
       o = options
    settings = {
        'host': o.get('zodb_host', "localhost"),
        'port': o.get('zodb_port', 3306),
        'user': o.get('zodb_user', 'zenoss'),
        'passwd': o.get('zodb_password', 'zenoss'),
        'db': o.get('zodb_db', 'zodb'),
    }
    if 'zodb_socket' in o:
        settings['unix_socket'] = o['zodb_socket']
    return settings



class MySqlZodbFactory(object):
    implements(IZodbFactory)

    # set db specific here to allow more flexible imports
    exceptions = db_exceptions
 
    def _getConf(self, settings):
        config = []
        keys = ['host', 'port', 'unix_socket', 'user', 'passwd', 'db']
        for key in keys:
            if key in settings:
                config.append("    %s %s" % (key, settings[key],))

        stanza = "\n".join([
            "<mysql>",
            "\n".join(config),
            "</mysql>\n",
        ])
        return stanza

    def getZopeZodbConf(self):
        """Return a zope.conf style zodb config."""
        settings = _getDefaults()
        return self._getConf(settings)

    def getZopeZodbSessionConf(self):
        """Return a zope.conf style zodb config."""
        settings = _getDefaults()
        settings['db'] += '_session'
        return self._getConf(settings)

    def getConnection(self, **kwargs):
        """Return a ZODB connection."""
        connectionParams = {
            'host': kwargs.get('zodb_host', "localhost"),
            'port': kwargs.get('zodb_port', 3306),
            'user': kwargs.get('zodb_user', 'zenoss'),
            'passwd': kwargs.get('zodb_password', 'zenoss'),
            'db': kwargs.get('zodb_db',  'zodb'),
        }
        socket = kwargs.get('zodb_socket', 'None')
        if socket is None or socket == 'None':
            # try to auto set ZENDS socket
            use_zends = os.environ.get("USE_ZENDS", False)
            if use_zends and use_zends == "1":
                zends_home = os.environ.get("ZENDSHOME","")
                zends_socket = zends_home + "/data/zends.sock"
                if zends_home and os.path.exists(zends_socket):
                    socket = zends_socket
        if socket and socket != 'None':
            connectionParams['unix_socket'] = socket
        kwargs = {
            'cache_module_name':'memcache',
            'keep_history': kwargs.get('zodb_keep_history', False)
        }
        adapter = relstorage.adapters.mysql.MySQLAdapter(
             options=relstorage.options.Options(**kwargs), 
             **connectionParams)

        # rename the poll_interval and cache_servers options to not
        # have the zodb prefix. 
        if 'zodb_poll_interval' in kwargs:
            kwargs['poll_interval'] = kwargs['zodb_poll_interval']
        if 'zodb_cache_servers' in kwargs:
            kwargs['cache_servers'] = kwargs['zodb_cache_servers']

        if 'poll_interval' in kwargs:
            if 'cache_servers' in kwargs:
                if self.options.pollinterval is None:
                    self.log.info("Using default poll-interval of 60 seconds because "
                        "cache-servers was set.")
                    kwargs['poll_interval'] = 60
                else:
                    kwargs['poll_interval'] = self.options.pollinterval
            else:
                self.log.warn("poll-interval of %r is being ignored because "
                    "cache-servers was not set." % self.options.pollinterval)
        storage = relstorage.storage.RelStorage(adapter, **kwargs)
        cache_size = kwargs.get('cache_size', 1000)
        db = ZODB.DB(storage, cache_size=cache_size)
        return (db, storage)

    def buildOptions(self, parser):
        """build OptParse options for ZODB connections"""
        group = optparse.OptionGroup(parser, "ZODB Options",
            "ZODB connection options and MySQL Adaptor options.")
        group.add_option('-R', '--zodb-dataroot',
                    dest="dataroot",
                    default="/zport/dmd",
                    help="root object for data load (i.e. /zport/dmd)")
        group.add_option('--zodb-cachesize',
                    dest="zodb_cache_size",default=1000, type='int',
                    help="in memory cachesize default: 1000")
        group.add_option('--zodb-host',
                    dest="zodb_host",default="localhost",
                    help="hostname of the MySQL server for ZODB")
        group.add_option('--zodb-port',
                    dest="zodb_port", type="int", default=3306,
                    help="port of the MySQL server for ZODB")
        group.add_option('--zodb-user', dest='zodb_user', default='zenoss',
                    help='user of the MySQL server for ZODB')
        group.add_option('--zodb-password', dest='zodb_password', default='zenoss',
                    help='password of the MySQL server for ZODB')
        group.add_option('--zodb-db', dest='zodb_db', default='zodb',
                    help='Name of database for MySQL object store')
        group.add_option('--zodb-socket', dest='zodb_socket', default=None,
                    help='Name of socket file for MySQL server connection if host is localhost')
        group.add_option('--zodb-cacheservers', dest='zodb_cacheservers', default="",
                    help='memcached servers to use for object cache (eg. 127.0.0.1:11211)')
        group.add_option('--zodb-poll-interval', dest='zodb_poll_interval', default=None, type='int',
                    help='Defer polling the database for the specified maximum time interval, in seconds.'
                    ' This will default to 60 only if --zodb-cacheservers is set.')
        parser.add_option_group(group)
    


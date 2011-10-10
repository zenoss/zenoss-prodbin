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

__doc__="""PostgresqlZodbFactory
"""

import optparse
import sys
import os
from zope.interface import implements
import ZODB
import relstorage.storage 
import relstorage.adapters.postgresql
import relstorage.options

from ZodbFactory import IZodbFactory


class PostgresqlZodbFactory(object):
    implements(IZodbFactory)

    def getConnection(self, **kwargs):
        """Return a ZODB connection."""
        connectionParams = {
            'host': kwargs.get('zodb_host', "localhost"),
            'port': kwargs.get('zodb_port', 5432),
            'user': kwargs.get('zodb_user', 'zenoss'),
            'passwd': kwargs.get('zodb_password', 'zenoss'),
            'dbname': kwargs.get('zodb_db', 'zodb'),
        }
        kwargs = {
            'cache_module_name':'memcache',
            'keep_history': kwargs.get('zodb_keep_history', False)
        }
        adapter = relstorage.adapters.postgresql.PostgreSQLAdapter(
             dsn="dbname=%(dbname)s port=%(port)s user=%(user)s password=%(passwd)s" % connectionParams,
             options=relstorage.options.Options(**kwargs))

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
            "ZODB connection options and PostgreSQL Adaptor options.")
        group.add_option('-R', '--zodb-dataroot',
                    dest="dataroot",
                    default="/zport/dmd",
                    help="root object for data load (i.e. /zport/dmd)")
        group.add_option('--zodb-cachesize',
                    dest="zodb_cache_size",default=1000, type='int',
                    help="in memory cachesize default: 1000")
        group.add_option('--zodb-host',
                    dest="zodb_host",default="localhost",
                    help="hostname of the PostgreSQL server for ZODB")
        group.add_option('--zodb-port',
                    dest="zodb_port", type="int", default=5432,
                    help="port of the PostgreSQL server for ZODB")
        group.add_option('--zodb-user', dest='zodb_user', default='zenoss',
                    help='user of the PostgreSQL server for ZODB')
        group.add_option('--zodb-password', dest='zodb_password', default='zenoss',
                    help='password of the PostgreSQL server for ZODB')
        group.add_option('--zodb-db', dest='zodb_db', default='zodb',
                    help='Name of database for PostgreSQL object store')
        # TODO: implement passing socket option to postgres adaptor
        group.add_option('--zodb-socket', dest='zodb_socket', default=None,
                    help='Name of socket file for PostgreSQL server connection if host is localhost')
        group.add_option('--zodb-cacheservers', dest='zodb_cacheservers', default="",
                    help='memcached servers to use for object cache (eg. 127.0.0.1:11211)')
        group.add_option('--zodb-poll-interval', dest='zodb_poll_interval', default=None, type='int',
                    help='Defer polling the database for the specified maximum time interval, in seconds.'
                    ' This will default to 60 only if --zodb-cacheservers is set.')
        parser.add_option_group(group)
    


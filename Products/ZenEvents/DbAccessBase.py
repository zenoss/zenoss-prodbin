###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import types

from DbConnectionPool import DbConnectionPool

class DbAccessBase(object):
    
    _cpool = DbConnectionPool()

    def close(self, conn):
        self._cpool.put(conn)

    def connect(self):
        """Load our database driver and connect to the database."""
        return self._cpool.get(backend=self.backend, 
                               host=self.host,
                               port=self.port,
                               username=self.username,
                               password=self.password,
                               database=self.database)

    def cleanstring(self, value):
        """Remove the trailing \x00 off the end of a string."""
        if type(value) in types.StringTypes:
            return value.rstrip("\x00")
        return value

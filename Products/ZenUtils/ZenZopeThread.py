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
import logging
from threading import Thread

class ZenZopeThread(Thread):
    """ 
    Thread running inside zope that has its own read-only connection to the db.
    """

    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(1)


    def opendb(self):
        """Open a connection to the zope database.
        """
        from Zope2 import DB
        self.conn = DB.open()
        root = self.conn.root()
        self.app  = root['Application']


    def syncdb(self):
        """Sync the connection to the zope database.
        """
        self.conn.sync()


    def closedb(self):
        """Abort our transaction (we are read-only) and close connection.
        """
        try:
            import transaction
            transaction.abort()
            self.conn.close() 
        except:
            pass

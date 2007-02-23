import types

from DbConnectionPool import DbConnectionPool

class DbAccessBase(object):
    
    _cpool = DbConnectionPool()

    def __init__(self):
        self.close(self.connect()) # Create and return a connection

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

import types

from DbConnectionPool import DbConnectionPool

class DbAccessBase(object):
    
    _cpool = DbConnectionPool()
    _currConn = None

    def __init__(self):
        try:
            self.connect() # Create a connection (and Pool)
        finally: self.close() # Return the connection
        
    def conn(self):
        if not self._currConn: 
            #self.connect()
            raise Exception, "Stray conn() or cursor() call: Call connect() before and close() after"
        return self._currConn
    
    def cursor(self):
        return self.conn().cursor()

    def close(self):
        if self._currConn:
            self._cpool.put(self._currConn)
            self._currConn = None

    def connect(self):
        """Load our database driver and connect to the database."""
        if self._currConn:
            raise Exception, "A connection has already been retrieved, call close() when finished."
        else:
            self._currConn = self._cpool.get(backend=self.backend, 
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

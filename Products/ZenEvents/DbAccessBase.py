import types
import struct
import DateTime


class DbAccessBase(object):

    def __init__(self, backend=None, host=None, port=None, username=None, 
                    password=None, database=None):
        self.backend = backend
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.connect()

    def cursor(self):
        return self.conn.cursor()

    def close(self):
        self.conn.close()
        self.conn = None

    def connect(self):
        """Load our database driver and connect to the database.""" 
        self.conn = None
        if self.backend == "omnibus":
            import Sybase
            self.conn = Sybase.connect(self.database,self.username,
                                        self.password)
        elif self.backend == "mysql": 
            import MySQLdb
            import MySQLdb.converters
            mysqlconv = MySQLdb.converters.conversions.copy()
            from MySQLdb.constants import FIELD_TYPE
            mysqlconv[FIELD_TYPE.DATETIME] = DateTime.DateTime
            mysqlconv[FIELD_TYPE.TIMESTAMP] = DateTime.DateTime
            # FIXME for some reason it thinks my int is a long -EAD
            mysqlconv[FIELD_TYPE.LONG] = int
            if hasattr(self, 'host'):
                host, database = self.host, self.database
            else:
                host, database = self.database, 'events'
            self.conn = MySQLdb.connect(host=host, user=self.username,
                                 port=self.port, passwd=self.password, 
                                 db=database, conv=mysqlconv)
            self.conn.autocommit(1)
        elif self.backend == "oracle":
            import DCOracle2
            connstr = "%s/%s@%s" % (self.username, self.password, self.database)
            self.conn = DCOracle2.connect(connstr)


    def cleanstring(value):
        """Remove the trailing \x00 off the end of a string."""
        if type(value) in types.StringTypes:
            return value.rstrip("\x00")
        return value

import types
import struct
import DateTime


class DbAccessBase(object):

    def connect(self):
        """Load our database driver and connect to the database.""" 
        if self.backend == "omnibus":
            import Sybase
            db = Sybase.connect(self.database,self.username,
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
            db = MySQLdb.connect(host=self.database, user=self.username,
                            passwd=self.password, db="events",conv=mysqlconv)
            db.autocommit(1)
        elif self.backend == "oracle":
            import DCOracle2
            connstr = "%s/%s@%s" % (self.username, self.password, self.database)
            db = DCOracle2.connect(connstr)
        return db


    def cleanstring(self, value):
        """Remove the trailing \x00 off the end of a string."""
        if type(value) in types.StringTypes:
            return value.rstrip("\x00")
        return value

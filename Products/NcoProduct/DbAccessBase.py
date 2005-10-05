import types
import DateTime

from Products.ZenUtils.Utils import cleanstring
    
class DbAccessBase:
    """
    Methods to abstract opening connections to databases from different vendors.
    """


    def _getCursor(self):
        """try to get a cursor to get data from database"""
        if self.backend == "netcool":
            import Sybase
            self._v_db = Sybase.connect(self.omniname,self.username,
                                        self.password)
        else: 
            import MySQLdb
            self._v_db = MySQLdb.connect(host=self.hostname, user=self.username,
                                        passwd=self.password, db="alerts")
        return self._v_db.cursor()


    def _closeDb(self):
        """close the databaes handle"""
        if hasattr(self, '_v_db') and self._v_db:
            self._v_db.close()
            self._v_db = None


    def _getHistoryCursor(self):
        import DCOracle2
        self._v_hdb = DCOracle2.connect(self.oracleconnstr)
        cur = self._v_hdb.cursor()
        return cur


    def _closeHistoryDb(self):
        if hasattr(self, '_v_hdb') and self._v_hdb:
            self._v_hdb.close()
            self._v_hdb = None

    
    def _cleanstring(self,value):
        """take the trailing \x00 off the end of a string"""
        if self.backend == "netcool":
            return cleanstring(value)
        else:
            return value
       

    def _convert(self, field, value):
        """convert a netcool value if nessesary"""
        value = self._cleanstring(value)
        key = field + str(value)
        if self._conversions.has_key(key):
            value = self._conversions[key]
        if self.isDate(field) and self.backend != "mysql":
            value = self._convertDate(value)
        return value
  

    def _convertDate(self, value):
        """convert dates to proper string format"""
        if type(value) != types.StringType:
            return DateTime.DateTime(value).strftime("%Y/%m/%d %H:%M:%S")
        else:
            return value


    def _escapeValue(self, value):
        """escape string values"""
        if self.backend == "mysql":
            return self._v_db.escape(value)
        return "'"+value+"'"


    def _checkConn(self):
        """check to see if the connection information in product works"""
        self._getCursor()
        self._closeDb()

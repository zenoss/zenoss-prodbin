import pdb
import unittest
import Globals
import transaction

from Products.ZenUtils.ZeoPoolBase import ZeoPoolBase

from ZODB.POSException import ConnectionStateError

class ZeoPoolBaseTest(unittest.TestCase):
    """
    Test ZeoPoolBase class.  These tests require a valid zeo server running
    on localhost:8100.  It must have an initialized zope database.
    """

    def testOpenCloseDB(self):
        zpb = ZeoPoolBase()
        app = zpb.getConnection()
        self.assert_(app.getId()=="Zope")
        zpb.closeAll()
        self.assert_(not zpb.is_connected())
        

    def testUseClosedDB(self):
        zpb = ZeoPoolBase()
        app = zpb.getConnection()
        self.assert_(app.getId()=="Zope")
        app._p_jar.close()
        del app
        zpb.closeAll()
        #pdb.set_trace()
        app = zpb.getConnection()
        app.unrestrictedTraverse("/zport/dmd")
        

    def testOpenCloseConn(self):
        import logging
        log = logging.getLogger()
        log.setLevel(60)
        zpb = ZeoPoolBase()
        app = zpb.getConnection()
        self.assert_(app.getId()=="Zope")
        app._p_jar.close()
        self.assertRaises(ConnectionStateError, 
                          app.unrestrictedTraverse, "/Control_Panel/Database")
                          
        

    def testOpenTwoCloseOne(self):
        zpb = ZeoPoolBase()
        a1 = zpb.getConnection()
        self.assert_(a1.getId()=="Zope")
        a2 = zpb.getConnection()
        self.assert_(a2.getId()=="Zope")
        a1._p_jar.close()
        self.assert_(zpb.available()==1)
        a2._p_jar.close()
        self.assert_(zpb.available()==2)
        

#    def testAddToDbPool(self):
#        zpb = ZeoPoolBase()
#        for i in range(zpb.options.conninc+1):
#            zpb.getConnection()
#        self.assert_(len(zpb._freepool) == zpb.options.conninc-1)
#        self.assert_(len(zpb._inusepool) == zpb.options.conninc+1)
#        zpb.closeAll()
#        self.assert_(len(zpb._freepool) == 0)
#        self.assert_(len(zpb._inusepool) == 0)
#   
#
#    def testGetConnectionAfterClose(self):
#        zpb = ZeoPoolBase()
#        zpb.closeAll()
#        app = zpb.getConnection()
#        self.assert_(len(zpb._freepool) == zpb.options.conninc-1)
#        self.assert_(len(zpb._inusepool) == 1)
#        zpb.closeAll()
#   
#
#    def testMaxOpenConnections(self):
#        zpb = ZeoPoolBase()
#        for i in range(zpb.options.maxconns):
#            zpb.getConnection()
#        self.assertRaises(MaxOpenConnections, zpb.getConnection)

   
if __name__ == "__main__":
    unittest.main()
 

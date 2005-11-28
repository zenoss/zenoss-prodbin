import pdb
import unittest
import Globals
import transaction

from Products.ZenUtils.ZeoPoolBase import ZeoPoolBase, MaxOpenConnections

class ZeoPoolBaseTest(unittest.TestCase):
    """
    Test ZeoPoolBase class.  These tests require a valid zeo server running
    on localhost:8100.  It must have an initialized zope database.
    """

    def testInit(self):
        zpb = ZeoPoolBase()
        self.assert_(len(zpb._freepool) == zpb.options.conninc)
        self.assert_(len(zpb._inusepool) == 0)
        zpb.closeAll()
        

    def testGetConnection(self):
        zpb = ZeoPoolBase()
        app = zpb.getConnection()
        self.assert_(hasattr(app, "Control_Panel"))
        self.assert_(len(zpb._freepool) == zpb.options.conninc-1)
        self.assert_(len(zpb._inusepool) == 1)
        zpb.freeConnection(app)
        self.assert_(len(zpb._freepool) == zpb.options.conninc)
        self.assert_(len(zpb._inusepool) == 0)
        zpb.closeAll()
        self.assert_(len(zpb._freepool) == 0)
        self.assert_(len(zpb._inusepool) == 0)


    def testAddToDbPool(self):
        zpb = ZeoPoolBase()
        for i in range(zpb.options.conninc+1):
            zpb.getConnection()
        self.assert_(len(zpb._freepool) == zpb.options.conninc-1)
        self.assert_(len(zpb._inusepool) == zpb.options.conninc+1)
        zpb.closeAll()
        self.assert_(len(zpb._freepool) == 0)
        self.assert_(len(zpb._inusepool) == 0)
   

    def testGetConnectionAfterClose(self):
        zpb = ZeoPoolBase()
        zpb.closeAll()
        app = zpb.getConnection()
        self.assert_(len(zpb._freepool) == zpb.options.conninc-1)
        self.assert_(len(zpb._inusepool) == 1)
        zpb.closeAll()
   

    def testMaxOpenConnections(self):
        zpb = ZeoPoolBase()
        for i in range(zpb.options.maxconns):
            zpb.getConnection()
        self.assertRaises(MaxOpenConnections, zpb.getConnection)

   
if __name__ == "__main__":
    unittest.main()
 

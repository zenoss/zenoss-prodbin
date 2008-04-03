
from ZenModelBaseTest import ZenModelBaseTest

class TestBogusRPNEval(ZenModelBaseTest):

    def testRpn(self):
        from Products.ZenModel.MinMaxThreshold import rpneval
        self.assertEquals(rpneval(2, '2,*'), 4)
        self.assertEquals(rpneval(7, '2,3,*,*'), 42)
        self.assertEquals(rpneval(19, '9,5,/,*,32,+'), 66.2)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestBogusRPNEval))
    return suite
        

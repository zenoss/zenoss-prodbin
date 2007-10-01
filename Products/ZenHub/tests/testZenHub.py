
import unittest
import Globals

from Products.ZenUtils.Driver import drive
import unittest

from twisted.internet import reactor
from twisted.cred import credentials
from twisted.spread import pb
import sys

def stop(ignored=None):
    if reactor.running:
        reactor.crash()

from Products.ZenHub.zenhub import ZenHub

class TestClient(pb.Referenceable):

    success = False
    
    def __init__(self, tester):
        self.tester = tester
        factory = pb.PBClientFactory()
        reactor.connectTCP("localhost", 7000, factory)
        d = factory.login(credentials.UsernamePassword("admin", "zenoss"),
                          client=self)
        d.addCallback(self.connected)
        d.addErrback(self.bad)

    def connected(self, perspective):
        svc = 'Products.ZenHub.tests.TestService'
        d = perspective.callRemote('getService', svc, self)
        d.addCallback(self.test)
        d.addErrback(self.bad)

    def bad(self, reason):
        stop()
        self.tester.fail('error: '+str(reason.value))

    def test(self, service):
        def Test(driver):
            data = ('Some Data', 17)
            yield service.callRemote('echo', data)
            self.tester.assertEqual(driver.next(), data)
            self.success = True
            stop()
        drive(Test).addBoth(stop)

class TestZenHub(unittest.TestCase):

    def testGetService(self):
        try:
            before, sys.argv = sys.argv, ['run',
                                          '--pbport=7000',
                                          '--xport=7001']
            zenhub = ZenHub()
        finally:
            sys.argv = before
        client = TestClient(self)
        reactor.callLater(1, stop)
        zenhub.main()
        self.assertTrue(client.success)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestZenHub))
    return suite

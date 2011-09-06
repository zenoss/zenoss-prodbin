# BaseTestCase is a subclass of ZopeTestCase which is ultimately a subclass of
# Python's standard unittest.TestCase. Because of this the following
# documentation on unit testing in Zope and Python are both applicable here.
#
# Python Unit testing framework
# http://docs.python.org/library/unittest.html
#
# Zope Unit Testing
# http://wiki.zope.org/zope2/Testing

from Products.ZenTestCase.BaseTestCase import BaseTestCase


class TestExample(BaseTestCase):
    def afterSetup(self):
        # You can use the afterSetup method to create a proper environment for
        # your tests to execute in, or to run common code between the tests.
        self.device = self.dmd.Devices.createInstance('testDevice')

    def testExampleOne(self):
        self.assertEqual("One", "One")
        self.assertTrue(True)

    def testExampleTwo(self):
        self.assertEqual(self.device.id, "testDevice")
        self.assertFalse(False)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()

    # Add your BaseTestCase subclasses here to have them executed.
    # suite.addTest(makeSuite(TestExample))

    return suite

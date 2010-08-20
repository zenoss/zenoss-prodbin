import unittest
from Products.ZenUtils.orm import nested_transaction
from Products.ZenUtils.tests.orm import ORMTestCase
#from Products.Five import zcml
#from Products.ZenTestCase.BaseTestCase import BaseTestCase

from ..impacts import ImpactRelationship

class TestImpactRelationship(ORMTestCase):
    _tables = (ImpactRelationship,)

    def test_creation(self):
        pass



def test_suite():
    return unittest.makeSuite(TestImpactRelationship)

###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""
Test the utilities that help with migration scripts.
"""

from unittest import TestCase, TestSuite, makeSuite
from Products.ZenModel.migrate.MigrateUtils import migratePropertyType
from Products.ZenRelations.RelationshipManager import RelationshipManager
from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager
from Products.ZenRelations.ZenPropertyManager import PropertyDescriptor

class StringTransformer(object):
    
    def transformForSet(self, value):
        return 'hello_' + value
    
    def transformForGet(self, value):
        return 'quux_' + value
        
class BarTransfromer(object):
    
    def transformForSet(self, value):
        return 'blah_' + value
        
    def transformForGet(self, value):
        return 'world_' + value

class MigratePropertyTypeTest(TestCase):
    
    def setUp(self):
        self.manager = RelationshipManager('manager')
        
    def tearDown(self):
        del self.manager
        
    def testPlainOld(self):
        """
        Test a plain old property (doesn't have a desciptor)
        """
        self.manager._setProperty('p0', 'foo', 'string')
        self.assertEqual('string', self.manager.getPropertyType('p0'))
        migratePropertyType(self.manager, 'p0', 'bar')
        self.assertEqual('bar', self.manager.getPropertyType('p0'))
        
    def testPropertyDescriptor(self):
        """
        Test a property that uses PropertyDescriptor
        """
        ZenPropertyManager.p0 = PropertyDescriptor('p0', 'string')
        self.manager.propertyTransformers = {
                'string': StringTransformer,
                'bar': BarTransfromer}
        self.manager._setProperty('p0', 'foo', 'string')
        self.assertEqual('string', self.manager.getPropertyType('p0'))
        migratePropertyType(self.manager, 'p0', 'bar')
        self.assertEqual('bar', self.manager.getPropertyType('p0'))
        self.assertEqual('world_blah_quux_hello_foo', self.manager.p0)
        
def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(MigratePropertyTypeTest))
    return suite
    

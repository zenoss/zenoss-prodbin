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

import unittest

import zope.component
from zope.interface.verify import verifyClass

from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.Zuul.interfaces import ISerializableFactory
from Products.Zuul.interfaces import IProcessNode
from Products.Zuul.facades.processfacade import ProcessNode
from Products.Zuul.interfaces import IProcessInfo
from Products.Zuul.facades.processfacade import ProcessInfo
from Products.Zuul.interfaces import IProcessFacade
from Products.Zuul.facades.processfacade import ProcessFacade
from Products.ZenModel.OSProcessOrganizer import manage_addOSProcessOrganizer

class ProcessFacadeTest(ZuulFacadeTestCase):

    def setUp(self):
        super(ProcessFacadeTest, self).setUp()
        self.facade = zope.component.queryUtility(IProcessFacade)
        manage_addOSProcessOrganizer(self.dmd.Processes, 'foo')
        self.dmd.Processes.foo.manage_addOSProcessClass('bar')

    def test_interfaces(self):
        verifyClass(IProcessNode, ProcessNode)
        verifyClass(IProcessInfo, ProcessInfo)
        verifyClass(IProcessFacade, ProcessFacade)
        
    def test_getTree(self):
        root = self.facade.getTree('Processes')
        self.assertEqual('Processes', root.id)
        self.assertEqual('Processes', root.text['text'])
        self.assertEqual(3, root.text['count'])
        self.assertEqual('instances', root.text['description'])
        self.failIf(root.leaf)
        children = list(root.children)
        self.assertEqual(1, len(children))
        foo = children[0]
        self.assertEqual('Processes/foo', foo.id)
        self.assertEqual('foo', foo.text['text'])
        self.assertEqual(3, foo.text['count'])
        self.assertEqual('instances', foo.text['description'])
        self.failIf(foo.leaf)
        fooChildren = list(foo.children)
        self.assertEqual(1, len(fooChildren))
        bar = fooChildren[0]
        self.assertEqual('Processes/foo/bar', bar.id)
        self.assertEqual('bar', bar.text['text'])
        self.assertEqual(3, bar.text['count'])
        self.assertEqual('instances', bar.text['description'])
        self.assert_(bar.leaf)
        self.assertEqual([], list(bar.children))
        obj = ISerializableFactory(root)()
        self.assertEqual('Processes', obj['id'])
        self.assertEqual('Processes', obj['text']['text'])
        self.assertEqual(3, obj['text']['count'])
        self.assertEqual('instances', obj['text']['description'])
        self.assertEqual(False, obj['leaf'])
        self.assertEqual(1, len(obj['children']))
        fooObj = obj['children'][0]
        self.assertEqual('Processes/foo', fooObj['id'])
        self.assertEqual('foo', fooObj['text']['text'])
        self.assertEqual(False, fooObj['leaf'])
        self.assertEqual(1, len(fooObj['children']))
        barObj = fooObj['children'][0]
        self.assertEqual('Processes/foo/bar', barObj['id'])
        self.assertEqual('bar', barObj['text']['text'])
        self.assert_(barObj['leaf'])
        self.failIf('children' in barObj)

    def test_getInfo(self):
        info = self.facade.getInfo('Processes/foo/bar')
        self.assertEqual('bar', info.name)
        serializable = ISerializableFactory(info)()
        self.assertEqual('bar', serializable['name'])

    def test_getMonitoringInfo(self):
        info = self.facade.getMonitoringInfo('Processes/foo/bar')
        self.assertEqual(True, info.enabled)
        self.assertEqual(4, info.eventSeverity)
        serializable = ISerializableFactory(info)()
        self.assertEqual(True, serializable['enabled'])
        self.assertEqual(4, serializable['eventSeverity'])

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ProcessFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
    

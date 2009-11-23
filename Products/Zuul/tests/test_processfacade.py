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
from Products.Zuul.interfaces import IProcessFacade
from Products.Zuul.facades.processfacade import ProcessNode
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
        verifyClass(IProcessFacade, ProcessFacade)

    def test_getProcessTree(self):
        root = self.facade.getTree('Processes')
        self.assertEqual('Processes', root.id)
        self.assert_(isinstance(root.text, dict))
        self.assertEqual('Processes', root.text['text'])
        self.failIf(root.leaf)
        children = list(root.children)
        self.assertEqual(1, len(children))
        foo = children[0]
        self.assertEqual('Processes/foo', foo.id)
        self.assertEqual('foo', foo.text['text'])
        self.failIf(foo.leaf)
        children = list(foo.children)
        self.assertEqual(1, len(children))
        bar = children[0]
        self.assertEqual('Processes/foo/bar', bar.id)
        self.assertEqual('bar', bar.text['text'])
        self.assert_(bar.leaf)
        children = list(bar.children)
        self.assertEqual([], children)
        obj = ISerializableFactory(root)()
        self.assertEqual('Processes', obj['id'])
        self.assertEqual('Processes', obj['text']['text'])
        self.failIf(obj['leaf'])
        self.assertEqual(1, len(obj['children']))
        fooObj = obj['children'][0]
        self.assertEqual('Processes/foo', fooObj['id'])
        self.assertEqual('foo', fooObj['text']['text'])
        self.failIf(fooObj['leaf'])
        self.assertEqual(1, len(fooObj['children']))
        barObj = fooObj['children'][0]
        self.assertEqual('Processes/foo/bar', barObj['id'])
        self.assertEqual('bar', barObj['text']['text'])
        self.assert_(barObj['leaf'])
        self.failIf('children' in barObj)

    def test_getProcessInfo(self):
        info = self.facade.getInfo('Processes/foo/bar')
        self.assertEqual('bar', info.name)
        serializable = ISerializableFactory(info)()
        self.assertEqual('bar', serializable['name'])


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ProcessFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
    

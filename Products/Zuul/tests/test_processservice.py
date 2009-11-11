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

from Products.Zuul.tests.base import ZuulServiceTestCase
from Products.Zuul.interfaces import IProcessTree, IProcessService
from Products.Zuul.services.processservice import ProcessTree
from Products.Zuul.services.processservice import ProcessService
from Products.ZenModel.OSProcessOrganizer import manage_addOSProcessOrganizer

class ProcessServiceTest(ZuulServiceTestCase):

    def setUp(self):
        super(ProcessServiceTest, self).setUp()
        self.svc = zope.component.queryUtility(IProcessService)

    def test_interfaces(self):
        verifyClass(IProcessTree, ProcessTree)
        verifyClass(IProcessService, ProcessService)

    def test_getProcessTree(self):
        manage_addOSProcessOrganizer(self.dmd.Processes, 'foo')
        self.dmd.Processes.foo.manage_addOSProcessClass('bar')
        root = self.svc.getProcessTree('Processes')
        self.assertEqual('Processes', root.id)
        self.assertEqual('Processes', root.text)
        self.failIf(root.leaf)
        self.assertEqual(1, len(root.children))
        foo = root.children[0]
        self.assertEqual('Processes/foo', foo.id)
        self.assertEqual('foo', foo.text)
        self.failIf(foo.leaf)
        self.assertEqual(1, len(foo.children))
        bar = foo.children[0]
        self.assertEqual('Processes/foo/bar', bar.id)
        self.assertEqual('bar', bar.text)
        self.assert_(bar.leaf)
        self.assertEqual([], bar.children)
        obj = root.serializableObject
        self.assertEqual('Processes', obj['id'])
        self.assertEqual('Processes', obj['text'])
        self.failIf('leaf' in obj)
        self.assertEqual(1, len(obj['children']))
        fooObj = obj['children'][0]
        self.assertEqual('Processes/foo', fooObj['id'])
        self.assertEqual('foo', fooObj['text'])
        self.failIf('leaf' in fooObj)
        self.assertEqual(1, len(fooObj['children']))
        barObj = fooObj['children'][0]
        self.assertEqual('Processes/foo/bar', barObj['id'])
        self.assertEqual('bar', barObj['text'])
        self.assert_(barObj['leaf'])
        self.failIf('children' in barObj)


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ProcessServiceTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
    

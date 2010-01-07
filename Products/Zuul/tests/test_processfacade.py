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

from zope.interface.verify import verifyClass

from Products import Zuul
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.Zuul.tests.base import EventTestCase
from Products.Zuul.interfaces import IProcessNode
from Products.Zuul.facades.processfacade import ProcessNode
from Products.Zuul.interfaces import IProcessInfo
from Products.Zuul.facades.processfacade import ProcessInfo
from Products.Zuul.interfaces import IProcessFacade
from Products.Zuul.facades.processfacade import ProcessFacade
from Products.ZenModel.OSProcessOrganizer import manage_addOSProcessOrganizer

class ProcessFacadeTest(EventTestCase, ZuulFacadeTestCase):

    def setUp(self):
        super(ProcessFacadeTest, self).setUp()
        self.facade = Zuul.getFacade('process')
        manage_addOSProcessOrganizer(self.dmd.Processes, 'foo')
        self.dmd.Processes.foo.manage_addOSProcessClass('bar')

    def test_interfaces(self):
        verifyClass(IProcessNode, ProcessNode)
        verifyClass(IProcessInfo, ProcessInfo)
        verifyClass(IProcessFacade, ProcessFacade)

    def test_getTree(self):
        root = self.facade.getTree('/zport/dmd/Processes')
        self.assertEqual('Processes', root.id)
        self.assertEqual('Processes', root.text['text'])
        self.assertEqual(0, root.text['count'])
        self.assertEqual('instances', root.text['description'])
        self.failIf(root.leaf)
        children = list(root.children)
        self.assertEqual(1, len(children))
        foo = children[0]
        self.assertEqual('/zport/dmd/Processes/foo', foo.uid)
        self.assertEqual('foo', foo.id)
        self.assertEqual('Processes/foo', foo.path)
        self.assertEqual('foo', foo.text['text'])
        self.assertEqual(0, foo.text['count'])
        self.assertEqual('instances', foo.text['description'])
        self.failIf(foo.leaf)
        fooChildren = list(foo.children)
        self.assertEqual(1, len(fooChildren))
        bar = fooChildren[0]
        self.assertEqual('/zport/dmd/Processes/foo/osProcessClasses/bar', bar.uid)
        self.assertEqual('bar', bar.id)
        self.assertEqual('Processes/foo/bar', bar.path)
        self.assertEqual('bar', bar.text['text'])
        self.assertEqual(0, bar.text['count'])
        self.assertEqual('instances', bar.text['description'])
        self.assert_(bar.leaf)
        self.assertEqual([], list(bar.children))
        obj = Zuul.marshal(root)
        self.assertEqual('Processes', obj['id'])
        self.assertEqual('Processes', obj['text']['text'])
        self.assertEqual(0, obj['text']['count'])
        self.assertEqual('instances', obj['text']['description'])
        self.assertEqual(False, obj['leaf'])
        self.assertEqual(1, len(obj['children']))
        fooObj = obj['children'][0]
        self.assertEqual('/zport/dmd/Processes/foo', fooObj['uid'])
        self.assertEqual('foo', fooObj['id'])
        self.assertEqual('Processes/foo', fooObj['path'])
        self.assertEqual('foo', fooObj['text']['text'])
        self.assertEqual(False, fooObj['leaf'])
        self.assertEqual(1, len(fooObj['children']))
        barObj = fooObj['children'][0]
        self.assertEqual('/zport/dmd/Processes/foo/osProcessClasses/bar', barObj['uid'])
        self.assertEqual('bar', barObj['id'])
        self.assertEqual('Processes/foo/bar', barObj['path'])
        self.assertEqual('bar', barObj['text']['text'])
        self.assert_(barObj['leaf'])
        self.failIf('children' in barObj)

    def test_getInfo(self):
        obj = self.facade.getInfo('/zport/dmd/Processes/foo/osProcessClasses/bar')
        self.assertEqual('bar', obj.name)
        data = Zuul.marshal(obj)
        self.assertEqual('bar', data['name'])
        data = {'name': 'barbar'}
        Zuul.unmarshal(data, obj)
        self.assertEqual('barbar', obj.name)

    def test_getDevices(self):
        device = self.dmd.Devices.createInstance('quux')
        device.os.addOSProcess('/zport/dmd/Processes/foo/osProcessClasses/bar', True)
        deviceInfos = self.facade.getDevices('/zport/dmd/Processes/foo/osProcessClasses/bar')
        self.assertEqual(1, len(deviceInfos))
        deviceInfo = deviceInfos[0]
        self.assertEqual('quux', deviceInfo.device)

    def test_getEvents(self):
        device = self.dmd.Devices.createInstance('quux')
        uid = '/zport/dmd/Processes/foo/osProcessClasses/bar'
        device.os.addOSProcess(uid, True)
        self.sendEvent(device='quux', component='bar', severity=4)
        events = self.facade.getEvents(uid)
        self.assert_(len(events) > 0)
        self.assertEqual(4, events[0].severity)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ProcessFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')


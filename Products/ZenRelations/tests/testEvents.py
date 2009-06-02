###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest

import transaction

from Testing import ZopeTestCase
from Testing.ZopeTestCase.layer import ZopeLite

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager

from OFS.SimpleItem import SimpleItem
from OFS.Folder import Folder

from zope import interface
from zope import component
from zope.app.component.hooks import setHooks
from zope.component.interfaces import IObjectEvent
from zope.testing import cleanup

from OFS.interfaces import IItem
from Products.Five import zcml
from Products.ZenRelations.RelationshipBase import IRelationship
from Products.ZenRelations.RelationshipManager import RelationshipManager
from Products.ZenRelations.RelSchema import *

class EventLogger(object):
    def __init__(self):
        self.reset()
    def reset(self):
        self._called = []
    def trace(self, ob, event):
        self._called.append((ob.getId(), event.__class__.__name__))
    def called(self):
        return self._called
    def print_called(self):
        from pprint import pprint
        pprint(self.called())

eventlog = EventLogger()

class ITestItem(interface.Interface):
    pass

class TestItem(RelationshipManager):
    interface.implements(ITestItem, IItem)
    def __init__(self, id):
        self.id = id
        self.buildRelations()


TS = 'Products.ZenRelations.tests.testEvents.'
class TestParentContainer(TestItem):
    _relations = (
        ("contained", ToManyCont(ToOne, TS + "TestToManyCont", "container")),

    )

class TestToManyCont(TestItem):
    _relations = (
        ("contained", ToManyCont(ToOne, TS + "TestContained", "container")),
        ("container", ToOne(ToManyCont, TS + "TestParentContainer", "contained")),
    )

class TestContained(TestItem):
    _relations = (
        ("container", ToOne(ToManyCont, TS + "TestToManyCont", "contained")),
    )

import zope.interface
def setUpEventlog(iface=None):
    eventlog.reset()
    component.provideHandler(eventlog.trace, (iface, IObjectEvent))
    return eventlog


class EventLayer(ZopeLite):

    @classmethod
    def setUp(cls):
        import Products

        zcml._initialized = 0
        zcml.load_site()
        setHooks()
        component.provideHandler(eventlog.trace, (ITestItem, IObjectEvent))
        component.provideHandler(eventlog.trace, (IRelationship, IObjectEvent))

    @classmethod
    def tearDown(cls):
        cleanup.cleanUp()
        zcml._initialized = 0


class EventTest(unittest.TestCase):

    layer = EventLayer

    def setUp(self):
        transaction.begin()
        self.app = self.root = ZopeTestCase.app()

    def tearDown(self):
        transaction.abort()
        ZopeTestCase.close(self.app)


class TestToManyContRelationship(EventTest):

    def setUp(self):
        EventTest.setUp(self)
        self.app._setObject('root', TestToManyCont('root'))
        self.root = getattr(self.app, 'root')
        transaction.savepoint(1)
        eventlog.reset()

    def testToManyContAdding(self):
        self.root.contained._setObject('ob1', TestContained('ob1'))
        self.assertEqual(eventlog.called(),
            [
            # Addition of ToOneRelationship
             ('container', 'ObjectWillBeAddedEvent'),
             ('container', 'ObjectAddedEvent'),
             ('ob1', 'ContainerModifiedEvent'),
            # Addition of the RelationshipManager to ToManyCont
             ('container', 'ObjectWillBeAddedEvent'),
             ('ob1', 'ObjectWillBeAddedEvent'),
             ('container', 'ObjectAddedEvent'),
             ('ob1', 'ObjectAddedEvent'),
             ('contained', 'ContainerModifiedEvent'),
             ('ob1', 'ContainerModifiedEvent'),
            ]
        )

    def testToManyContDeleteContained(self):
        self.root.contained._setObject('ob1', TestContained('ob1'))
        eventlog.reset()
        self.root.contained._delObject('ob1')
        self.assertEqual(eventlog.called(),
            [
             ('container', 'ObjectWillBeRemovedEvent'),
             ('ob1', 'ObjectWillBeRemovedEvent'),
             ('container', 'ObjectRemovedEvent'),
             ('ob1', 'ObjectRemovedEvent'),
             ('contained', 'ContainerModifiedEvent')
            ]
        )

    def testToManyContDeleteContainer(self):
        self.app._setObject('grandpa', TestParentContainer('grandpa'))
        grandpa = getattr(self.app, 'grandpa')
        grandpa.contained._setObject('pops', TestToManyCont('pops'))
        pops = getattr(grandpa.contained, 'pops')
        pops.contained._setObject('sonny', TestContained('sonny'))
        eventlog.reset()
        grandpa.contained._delObject('pops')
        self.assertEqual(eventlog.called(),
            [
                ('contained', 'ObjectWillBeRemovedEvent'),
                ('container', 'ObjectWillBeRemovedEvent'),
                ('sonny', 'ObjectWillBeRemovedEvent'),
                ('container', 'ObjectWillBeRemovedEvent'),
                ('pops', 'ObjectWillBeRemovedEvent'),
                ('contained', 'ObjectRemovedEvent'),
                ('container', 'ObjectRemovedEvent'),
                ('sonny', 'ObjectRemovedEvent'),
                ('container', 'ObjectRemovedEvent'),
                ('pops', 'ObjectRemovedEvent'),
                ('contained', 'ContainerModifiedEvent')
            ]
        )


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestToManyContRelationship))
    return suite

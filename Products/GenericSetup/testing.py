##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Node adapter testing utils.

$Id: testing.py 66587 2006-04-06 10:47:06Z yuppie $
"""

import unittest
import Testing

from xml.dom.minidom import parseString

import Products.Five
from Products.Five import zcml
from zope.component import getMultiAdapter
from zope.interface import implements
from zope.interface.verify import verifyClass

from interfaces import IBody
from interfaces import INode
from interfaces import ISetupEnviron

try:
    from zope.app.testing.placelesssetup import PlacelessSetup
except ImportError:  # BBB, Zope3 < 3.1
    from zope.app.tests.placelesssetup import PlacelessSetup


class DummyLogger:

    def __init__(self, id, messages):
        self._id = id
        self._messages = messages

    def info(self, msg, *args, **kwargs):
        self._messages.append((20, self._id, msg))

    def warning(self, msg, *args, **kwargs):
        self._messages.append((30, self._id, msg))


class DummySetupEnviron(object):

    """Context for body im- and exporter.
    """

    implements(ISetupEnviron)

    def __init__(self):
        self._notes = []
        self._should_purge = True

    def getLogger(self, name):
        return DummyLogger(name, self._notes)

    def shouldPurge(self):
        return self._should_purge


class _AdapterTestCaseBase(PlacelessSetup, unittest.TestCase):

    def _populate(self, obj):
        pass

    def _verifyImport(self, obj):
        pass

    def setUp(self):
        PlacelessSetup.setUp(self)
        zcml.load_config('meta.zcml', Products.Five)
        zcml.load_config('permissions.zcml', Products.Five)


class BodyAdapterTestCase(_AdapterTestCaseBase):

    def test_z3interfaces(self):
        verifyClass(IBody, self._getTargetClass())

    def test_body_get(self):
        self._populate(self._obj)
        context = DummySetupEnviron()
        adapted = getMultiAdapter((self._obj, context), IBody)
        self.assertEqual(adapted.body, self._BODY)

    def test_body_set(self):
        context = DummySetupEnviron()
        adapted = getMultiAdapter((self._obj, context), IBody)
        adapted.body = self._BODY
        self._verifyImport(self._obj)
        self.assertEqual(adapted.body, self._BODY)

        # now in update mode
        context._should_purge = False
        adapted = getMultiAdapter((self._obj, context), IBody)
        adapted.body = self._BODY
        self._verifyImport(self._obj)
        self.assertEqual(adapted.body, self._BODY)

        # and again in update mode
        adapted = getMultiAdapter((self._obj, context), IBody)
        adapted.body = self._BODY
        self._verifyImport(self._obj)
        self.assertEqual(adapted.body, self._BODY)

class NodeAdapterTestCase(_AdapterTestCaseBase):

    def test_z3interfaces(self):
        verifyClass(INode, self._getTargetClass())

    def test_node_get(self):
        self._populate(self._obj)
        context = DummySetupEnviron()
        adapted = getMultiAdapter((self._obj, context), INode)
        self.assertEqual(adapted.node.toprettyxml(' '), self._XML)

    def test_node_set(self):
        context = DummySetupEnviron()
        adapted = getMultiAdapter((self._obj, context), INode)
        adapted.node = parseString(self._XML).documentElement
        self._verifyImport(self._obj)
        self.assertEqual(adapted.node.toprettyxml(' '), self._XML)

        # now in update mode
        context._should_purge = False
        adapted = getMultiAdapter((self._obj, context), INode)
        adapted.node = parseString(self._XML).documentElement
        self._verifyImport(self._obj)
        self.assertEqual(adapted.node.toprettyxml(' '), self._XML)

        # and again in update mode
        adapted = getMultiAdapter((self._obj, context), INode)
        adapted.node = parseString(self._XML).documentElement
        self._verifyImport(self._obj)
        self.assertEqual(adapted.node.toprettyxml(' '), self._XML)

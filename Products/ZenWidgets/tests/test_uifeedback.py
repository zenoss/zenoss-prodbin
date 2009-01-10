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
from Queue import Queue

from AccessControl.SecurityManagement import newSecurityManager

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenWidgets.uifeedback import Messenger, INFO, WARNING

MSG = 'Test Message'


class TestUIFeedback(BaseTestCase):

    def _login(self, name):
        """
        Log in as a particular user.
        """
        uf = self.dmd.zport.acl_users
        user = uf.getUserById(name)
        if not hasattr(user, 'aq_base'):
            user = user.__of__(uf)
        newSecurityManager(None, user)

    def setUp(self):
        BaseTestCase.setUp(self)
        self.m = Messenger()
        # Make a new user for comparison with default tester user
        self.dmd.ZenUsers.manage_addUser('nottester', roles=())

    def test_singleton(self):
        """
        Make sure only one instance is created from the Messenger constructor
        """
        m1 = Messenger()
        self.assert_(self.m is m1)

    def test_getCurrentUser(self):
        """
        Log in as a different user to see if the queue works out
        """
        # Check that we're the default user from BaseTestCase
        self.assertEqual(self.m._getCurrentUser(), 'tester')
        # Log in as somebody else
        self._login('nottester')
        # Make sure the messenger sees it
        self.assertEqual(self.m._getCurrentUser(), 'nottester')

    def test_getQueueSlice(self):
        def _getQueue():
            q = Queue()
            for i in range(10):
                q.put(i)
            return q
        result = self.m._getQueueSlice(_getQueue(), limit=4)
        self.assertEqual(len(result), 4)
        result = self.m._getQueueSlice(_getQueue(), limit=0)
        self.assertEqual(len(result), 0)
        result = self.m._getQueueSlice(_getQueue(), limit=None)
        self.assertEqual(len(result), 10)

    def test_queue_creation(self):
        # Clear out the user queue if it's there for some reason
        if self.m._queue_dict.has_key('tester'):
            del self.m._queue_dict['tester']
        q = self.m._getUserQueue()
        self.assert_(self.m._queue_dict.has_key('tester'))

    def test_getUserQueue(self):
        self._login('tester')
        q = self.m._getUserQueue()
        self._login('nottester')
        q2 = self.m._getUserQueue()
        self.assertEqual(self.m._queue_dict['tester'], q)
        self.assertEqual(self.m._queue_dict['nottester'], q2)
        self.assertNotEqual(q, q2)

    def test_send(self):
        # Send to current user
        self.m.send(MSG)
        msg = self.m._queue_dict['tester'].get(block=False)
        self.assertEqual(msg['msg'], MSG)

        # Send to different user
        self.m.send(MSG, 'nottester')
        msg = self.m._queue_dict['nottester'].get(block=False)
        self.assertEqual(msg['msg'], MSG)

    def test_get(self):
        self.m.send(MSG)
        msgs = self.m.get()
        self.assertEqual(len(msgs), 1)
        msg = msgs[0]
        self.assertEqual(msg['msg'], MSG)

        # Send a bunch
        for i in range(10):
            self.m.send('%s %s' % (MSG, i))

        # Get some of them
        msgs = self.m.get(limit=3)
        self.assertEqual(len(msgs), 3)

        # Get the rest
        msgs = self.m.get()
        self.assertEqual(len(msgs), 7)

        # None left, we hope
        msgs = self.m.get()
        self.assertEqual(len(msgs), 0)

    def test_notify(self):
        self.m.notify(MSG)
        msg = self.m.get()[0]
        self.assertEqual(msg['severity'], INFO)

    def test_warn(self):
        self.m.warn(MSG)
        msg = self.m.get()[0]
        self.assertEqual(msg['severity'], WARNING)

    def test_next(self):
        # Send a bunch
        for i in range(10):
            self.m.send('%s %s' % (MSG, i))
        for i in range(10):
            msg = self.m.next()
            self.assertEqual(msg['msg'], '%s %s' % (MSG, i))

    def test_iter(self):
        for i in range(10):
            self.m.send('%s %s' % (MSG, i))
        for i, msg in enumerate(self.m):
            self.assertEqual(msg['msg'], '%s %s' % (MSG, i))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestUIFeedback))
    return suite

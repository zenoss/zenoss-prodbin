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
from AccessControl.SecurityManagement import newSecurityManager

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenWidgets.messaging import MessageSender
from Products.ZenWidgets.messaging import BrowserMessageBox, UserMessageBox

class TestMessaging(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.dmd.REQUEST.SESSION = {}

    def _login(self, name):
        """
        Log in as a particular user.
        """
        uf = self.dmd.zport.acl_users
        user = uf.getUserById(name)
        if not hasattr(user, 'aq_base'):
            user = user.__of__(uf)
        newSecurityManager(None, user)

    def test_sending_to_request(self):
        MessageSender(self.dmd).sendToBrowser('title', 'This is a message')
        us = self.dmd.ZenUsers.getUserSettings('tester')
        self.assertEqual(len(us.messages()), 0)
        self.assertEqual(len(self.dmd.REQUEST.SESSION['messages']), 1)
        self.assertEqual(self.dmd.REQUEST.SESSION['messages'][0].body,
                         'This is a message')

    def test_sending_to_user(self):
        self._login('tester')
        MessageSender(self.dmd).sendToUser('title', 'This is a message')
        us = self.dmd.ZenUsers.getUserSettings('tester')
        self.assertEqual(len(us.messages), 1)
        self.assertEqual(us.messages()[0].body, 'This is a message')

    def test_adapters(self):
        MessageSender(self.dmd).sendToBrowser(
            'title',
            'This is a browser message')
        MessageSender(self.dmd).sendToUser(
            'title',
            'This is a user message')
        brow = BrowserMessageBox(self.dmd)
        user = UserMessageBox(self.dmd)
        browmsgs = brow.get_messages()
        usermsgs = user.get_messages()
        self.assertEqual(len(browmsgs), 1)
        self.assertEqual(len(usermsgs), 1)
        self.assertEqual(browmsgs[0].body, 'This is a browser message')
        self.assertEqual(usermsgs[0].body, 'This is a user message')

    def test_mark_as_read(self):
        MessageSender(self.dmd).sendToBrowser('title',
                                              'This is a browser message')
        MessageSender(self.dmd).sendToUser('title',
                                            'This is a user message')
        brow = BrowserMessageBox(self.dmd)
        user = UserMessageBox(self.dmd)

        self.assertEqual(len(brow.get_messages()), 1)
        brow.get_messages()[0].mark_as_read()
        # For browser messages, mark_as_read deletes
        self.assertEqual(len(brow.get_messages()), 0)
        self.assertEqual(len(brow.get_unread()), 0)

        self.assertEqual(len(user.get_messages()), 1)
        user.get_messages()[0].mark_as_read()
        self.assertEqual(len(user.get_messages()), 1)
        self.assertEqual(len(user.get_unread()), 0)





def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestMessaging))
    return suite

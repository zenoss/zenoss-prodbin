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
"""MailHost export / import support unit tests.

$Id: test_exportimport.py 40413 2005-11-29 19:44:07Z yuppie $
"""

import unittest
import Testing

from Products.Five import zcml

from Products.GenericSetup.testing import BodyAdapterTestCase

_MAILHOST_BODY = """\
<?xml version="1.0"?>
<object name="foo_mailhost" meta_type="Mail Host" smtp_host="localhost"
   smtp_port="25" smtp_pwd="" smtp_uid=""/>
"""


class MailHostXMLAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.MailHost.exportimport \
                import MailHostXMLAdapter

        return MailHostXMLAdapter

    def _verifyImport(self, obj):
        self.assertEqual(type(obj.smtp_host), str)
        self.assertEqual(obj.smtp_host, 'localhost')
        self.assertEqual(type(obj.smtp_port), int)
        self.assertEqual(obj.smtp_port, 25)
        self.assertEqual(type(obj.smtp_pwd), str)
        self.assertEqual(obj.smtp_pwd, '')
        self.assertEqual(type(obj.smtp_uid), str)
        self.assertEqual(obj.smtp_uid, '')

    def setUp(self):
        import Products.GenericSetup.MailHost
        from Products.MailHost.MailHost import MailHost

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.GenericSetup.MailHost)

        self._obj = MailHost('foo_mailhost')
        self._BODY = _MAILHOST_BODY


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(MailHostXMLAdapterTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

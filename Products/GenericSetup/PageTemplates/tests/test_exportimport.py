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
"""PageTemplate export / import support unit tests.

$Id: test_exportimport.py 68406 2006-05-31 10:12:09Z yuppie $
"""

import unittest
import Testing

from Products.Five import zcml

from Products.GenericSetup.testing import BodyAdapterTestCase


_PAGETEMPLATE_BODY = """\
<html>
  <div>Foo</div>
</html>
"""


class ZopePageTemplateBodyAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PageTemplates.exportimport \
                import ZopePageTemplateBodyAdapter

        return ZopePageTemplateBodyAdapter

    def _populate(self, obj):
        obj.write(_PAGETEMPLATE_BODY)

    def setUp(self):
        import Products.GenericSetup.PageTemplates
        from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PageTemplates)

        self._obj = ZopePageTemplate('foo_template')
        self._BODY = _PAGETEMPLATE_BODY


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(ZopePageTemplateBodyAdapterTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

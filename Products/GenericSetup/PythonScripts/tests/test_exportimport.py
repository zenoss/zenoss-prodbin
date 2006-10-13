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
"""PythonScript export / import support unit tests.

$Id: test_exportimport.py 40314 2005-11-22 13:21:47Z yuppie $
"""

import unittest
import Testing

from Products.Five import zcml

from Products.GenericSetup.testing import BodyAdapterTestCase


_PYTHONSCRIPT_BODY = """\
## Script (Python) "foo_script"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
"""


class PythonScriptBodyAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PythonScripts.exportimport \
                import PythonScriptBodyAdapter

        return PythonScriptBodyAdapter

    def setUp(self):
        import Products.GenericSetup.PythonScripts
        from Products.PythonScripts.PythonScript import PythonScript

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PythonScripts)

        self._obj = PythonScript('foo_script')
        self._BODY = _PYTHONSCRIPT_BODY


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(PythonScriptBodyAdapterTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Unit tests for zcml module.

$Id: test_zcml.py 68512 2006-06-07 16:24:12Z yuppie $
"""

import unittest
import Testing
from zope.testing import doctest


def test_registerProfile():
    """
    Use the genericsetup:registerProfile directive::

      >>> import Products.GenericSetup
      >>> from Products.Five import zcml
      >>> configure_zcml = '''
      ... <configure
      ...     xmlns:genericsetup="http://namespaces.zope.org/genericsetup"
      ...     i18n_domain="foo">
      ...   <genericsetup:registerProfile
      ...       name="default"
      ...       title="Install Foo Extension"
      ...       description="Adds foo support."
      ...       provides="Products.GenericSetup.interfaces.EXTENSION"
      ...       />
      ... </configure>'''
      >>> zcml.load_config('meta.zcml', Products.GenericSetup)
      >>> zcml.load_string(configure_zcml)

    Make sure the profile is registered correctly::

      >>> from Products.GenericSetup.registry import _profile_registry
      >>> profile_id = 'Products.GenericSetup:default'
      >>> profile_id in _profile_registry._profile_ids
      True
      >>> info = _profile_registry._profile_info[profile_id]
      >>> info['id']
      u'Products.GenericSetup:default'
      >>> info['title']
      u'Install Foo Extension'
      >>> info['description']
      u'Adds foo support.'
      >>> info['path']
      u'profiles/default'
      >>> info['product']
      'Products.GenericSetup'
      >>> from Products.GenericSetup.interfaces import EXTENSION
      >>> info['type'] is EXTENSION
      True
      >>> info['for'] is None
      True

    Clean up and make sure the cleanup works::

      >>> # BBB: in Zope 2.8 we can't import cleanUp
      ... from zope.testing.cleanup import CleanUp
      >>> CleanUp().cleanUp()
      >>> profile_id in _profile_registry._profile_ids
      False
      >>> profile_id in _profile_registry._profile_info
      False
    """


def test_suite():
    return unittest.TestSuite((
        doctest.DocTestSuite(),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

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
""" Mix-in classes for testing interface conformance.

$Id: conformance.py 39493 2005-10-17 18:48:24Z yuppie $
"""

class ConformsToISimpleItem:

    def test_conforms_to_Five_ISimpleItem(self):
        from zope.interface.verify import verifyClass
        from Products.Five.interfaces import ISimpleItem

        verifyClass(ISimpleItem, self._getTargetClass())

class ConformsToIINIAware:

    def test_conforms_to_IINIAware(self):
        from zope.interface.verify import verifyClass
        from Products.CMFCore.interfaces import IINIAware

        verifyClass(IINIAware, self._getTargetClass())

class ConformsToICSVAware:

    def test_conforms_to_ICSVAware(self):
        from zope.interface.verify import verifyClass
        from Products.CMFCore.interfaces import ICSVAware

        verifyClass(ICSVAware, self._getTargetClass())

class ConformsToIFilesystemExporter:
    """ Mix-in for test cases whose target class implements IFilesystemExporter.
    """
    def test_conforms_to_IFilesystemExporter(self):
        from zope.interface.verify import verifyClass
        from Products.CMFCore.interfaces import IFilesystemExporter

        verifyClass(IFilesystemExporter, self._getTargetClass())

class ConformsToIFilesystemImporter:
    """ Mix-in for test cases whose target class implements IFilesystemImporter.
    """
    def test_conforms_to_IFilesystemImporter(self):
        from zope.interface.verify import verifyClass
        from Products.CMFCore.interfaces import IFilesystemImporter

        verifyClass(IFilesystemImporter, self._getTargetClass())

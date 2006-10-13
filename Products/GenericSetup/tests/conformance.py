##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Base classes for testing interface conformance.

Derived testcase classes should define '_getTargetClass()', which must
return the class being tested for conformance.

$Id: conformance.py 40140 2005-11-15 18:53:19Z tseaver $
"""

class ConformsToISetupContext:

    def test_ISetupContext_conformance( self ):

        from Products.GenericSetup.interfaces import ISetupContext
        from zope.interface.verify import verifyClass

        verifyClass( ISetupContext, self._getTargetClass() )

class ConformsToIImportContext:

    def test_IImportContext_conformance( self ):

        from Products.GenericSetup.interfaces import IImportContext
        from zope.interface.verify import verifyClass

        verifyClass( IImportContext, self._getTargetClass() )

class ConformsToIExportContext:

    def test_IExportContext_conformance( self ):

        from Products.GenericSetup.interfaces import IExportContext
        from zope.interface.verify import verifyClass

        verifyClass( IExportContext, self._getTargetClass() )

class ConformsToIStepRegistry:

    def test_IStepRegistry_conformance( self ):

        from Products.GenericSetup.interfaces import IStepRegistry
        from zope.interface.verify import verifyClass

        verifyClass( IStepRegistry, self._getTargetClass() )

class ConformsToIImportStepRegistry:

    def test_IImportStepRegistry_conformance( self ):

        from Products.GenericSetup.interfaces import IImportStepRegistry
        from zope.interface.verify import verifyClass

        verifyClass( IImportStepRegistry, self._getTargetClass() )

class ConformsToIExportStepRegistry:

    def test_IExportStepRegistry_conformance( self ):

        from Products.GenericSetup.interfaces import IExportStepRegistry
        from zope.interface.verify import verifyClass

        verifyClass( IExportStepRegistry, self._getTargetClass() )

class ConformsToIToolsetRegistry:

    def test_IToolsetRegistry_conformance( self ):

        from Products.GenericSetup.interfaces import IToolsetRegistry
        from zope.interface.verify import verifyClass

        verifyClass( IToolsetRegistry, self._getTargetClass() )

class ConformsToIProfileRegistry:

    def test_IProfileRegistry_conformance( self ):

        from Products.GenericSetup.interfaces import IProfileRegistry
        from zope.interface.verify import verifyClass

        verifyClass( IProfileRegistry, self._getTargetClass() )

class ConformsToISetupTool:

    def test_ISetupTool_conformance( self ):

        from Products.GenericSetup.interfaces import ISetupTool
        from zope.interface.verify import verifyClass

        verifyClass( ISetupTool, self._getTargetClass() )

class ConformsToIContentFactory:

    def test_conforms_to_IContentFactory(self):

        from Products.GenericSetup.interfaces import IContentFactory
        from zope.interface.verify import verifyClass

        verifyClass( IContentFactory, self._getTargetClass() )

class ConformsToIContentFactoryName:

    def test_conforms_to_IContentFactory(self):

        from Products.GenericSetup.interfaces import IContentFactoryName
        from zope.interface.verify import verifyClass

        verifyClass( IContentFactoryName, self._getTargetClass() )

class ConformsToIFilesystemExporter:

    def test_conforms_to_IFilesystemExporter(self):

        from Products.GenericSetup.interfaces import IFilesystemExporter
        from zope.interface.verify import verifyClass

        verifyClass( IFilesystemExporter, self._getTargetClass() )

class ConformsToIFilesystemImporter:

    def test_conforms_to_IFilesystemImporter(self):

        from Products.GenericSetup.interfaces import IFilesystemImporter
        from zope.interface.verify import verifyClass

        verifyClass( IFilesystemImporter, self._getTargetClass() )

class ConformsToIINIAware:

    def test_conforms_to_IINIAware(self):

        from Products.GenericSetup.interfaces import IINIAware
        from zope.interface.verify import verifyClass

        verifyClass (IINIAware, self._getTargetClass() )

class ConformsToICSVAware:

    def test_conforms_to_ICSVAware(self):

        from Products.GenericSetup.interfaces import ICSVAware
        from zope.interface.verify import verifyClass

        verifyClass( ICSVAware, self._getTargetClass() )

class ConformsToIDAVAware:

    def test_conforms_to_IDAVAware(self):

        from Products.GenericSetup.interfaces import IDAVAware
        from zope.interface.verify import verifyClass

        verifyClass( IDAVAware, self._getTargetClass() )

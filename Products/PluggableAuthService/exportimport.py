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
"""Filesystem exporter / importer adapters.

$Id: exportimport.py 40142 2005-11-15 21:10:43Z tseaver $
"""

from zope.interface import implements
from Products.GenericSetup.interfaces import IContentFactory
from Products.GenericSetup.interfaces import IContentFactoryName
from Products.GenericSetup.interfaces import IFilesystemExporter
from Products.GenericSetup.interfaces import IFilesystemImporter
from Products.GenericSetup.utils import _getDottedName

#
#   setup_tool handlers
#
def exportPAS(context):
    IFilesystemExporter(context.getSite()).export(context, 'PAS', True)

def importPAS(context):
    IFilesystemImporter(context.getSite()).import_(context, 'PAS', True)


class PAS_PR_ContentFactory(object):

    implements(IContentFactory)

    def __init__(self, context):
        self.context = context

    def __call__(self, object_id):
        from Products.PluginRegistry.PluginRegistry import PluginRegistry
        registry = PluginRegistry(())
        registry._setId(object_id)
        self.context._setObject(object_id, registry)
        return registry
    
class PAS_CF_Namer(object):

    implements(IContentFactoryName)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        return 'plugins'

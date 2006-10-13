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
"""SampleSite setup handlers.

$Id: exportimport.py 68596 2006-06-12 08:46:53Z yuppie $
"""

from zope.component import queryMultiAdapter

from Products.GenericSetup.interfaces import IBody
from Products.GenericSetup.interfaces import ISetupTool
from Products.GenericSetup.utils import exportObjects
from Products.GenericSetup.utils import importObjects

_PATH = 'siteroot'


def importSite(context):
    """Import site configuration.
    """
    site = context.getSite()
    importer = queryMultiAdapter((site, context), IBody)
    if importer:
        body = context.readDataFile(_PATH+'.xml')
        if body is not None:
            importer.body = body

    for sub in site.objectValues():
        if ISetupTool.providedBy(sub):
            continue
        importObjects(sub, _PATH+'/', context)

def exportSite(context):
    """Export site configuration.
    """
    site = context.getSite()
    exporter = queryMultiAdapter((site, context), IBody)
    if exporter:
        body = exporter.body
        if body is not None:
            context.writeDataFile(_PATH+'.xml', body, exporter.mime_type)

    for sub in site.objectValues():
        if ISetupTool.providedBy(sub):
            continue
        exportObjects(sub, _PATH+'/', context)

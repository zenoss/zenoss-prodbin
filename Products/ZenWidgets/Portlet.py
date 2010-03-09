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

from Products.ZenModel.ZenossSecurity import *
from os.path import basename, exists
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM
from Globals import InitializeClass
from Products.ZenUtils.Utils import zenPath

def manage_addPortlet(self, context, REQUEST=None):
    """
    Add a portlet.
    """
    pass

class Portlet(ZenModelRM):
    """
    A wrapper for a portlet javascript source file that can include metadata
    such as a name, a title, a description and permissions.

    Portlets should not be instantiated directly. They should only be created
    by a PortletManager object.
    """
    source = ''

    portal_type = meta_type = 'Portlet'

    _relations = (
        ("portletManager", ToOne(
            ToManyCont, "Products.ZenWidgets.PortletManager", "portlets")),
    )

    _properties = (
        {'id':'title','type':'string','mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
        {'id':'permission', 'type':'string', 'mode':'w'},
        {'id':'sourcepath', 'type':'string', 'mode':'w'},
        {'id':'preview', 'type':'string', 'mode':'w'},
    )


    def __init__(self, sourcepath, id='', title='', description='', 
                 preview='', permission=ZEN_COMMON):
        if not id: id = basename(sourcepath).split('.')[0]
        self.id = id
        ZenModelRM.__init__(self, id)
        self.title = title
        self.description = description
        self.permission = permission
        self.sourcepath = sourcepath
        self.preview = preview
        self._read_source()

    def _getSourcePath(self):
        return zenPath(self.sourcepath)

    def check(self):
        return exists(self._getSourcePath())

    def _read_source(self):
        try:
            f = file(self._getSourcePath())
        except IOError, e:
            return
        else:
            self.source = f.read()
            f.close()

    def getPrimaryPath(self,fromNode=None):
        """
        Override the default, which doesn't account for things on zport
        """
        return ('', 'zport') + super(Portlet, self).getPrimaryPath(fromNode)

    def get_source(self, debug_mode=False):
        if debug_mode: self._read_source()
        src = []
        src.append(self.source)
        src.append("YAHOO.zenoss.portlet.register_portlet('%s', '%s');" % (
            self.id, self.title))
        return '\n'.join(src)

InitializeClass(Portlet)

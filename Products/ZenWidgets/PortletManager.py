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

import os, md5
from Globals import InitializeClass, DevelopmentMode
from AccessControl import getSecurityManager
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM

from Products.ZenModel.ZenossSecurity import *

from Portlet import Portlet

getuid = lambda:md5.md5(os.urandom(10)).hexdigest()[:8]

class DuplicatePortletRegistration(Exception): pass

def manage_addPortletManager(context, id="", REQUEST=None):
    """
    Create a portlet manager under context.
    """
    if not id: id = "ZenPortletManager"
    zpm = PortletManager(id)
    context._setObject(id, zpm)
    zpm = context._getOb(id)
    zpm.buildRelations()

class PortletManager(ZenModelRM):
    """
    A registry for portlet source and metadata. Provides access functions and
    handles portlet permissions.
    """

    portal_type = meta_type = 'PortletManager'

    _relations = (
        ("portlets", ToManyCont(ToOne, "Products.ZenWidgets.Portlet", 
            "portletManager")),
    )

    def register_portlet(self, sourcepath, id='', title='', description='', 
                         preview='', permission=ZEN_COMMON):
        """
        Registers a new source file and creates an associated Portlet to store
        the metadata and provide access methods.
        """
        p = self.find(id, sourcepath) 
        if p: self.unregister_portlet(p.id)
        p = Portlet(sourcepath, id, title, description, preview, permission)
        self.portlets._setObject(id, p)

    def unregister_portlet(self, id):
        try:
            self.portlets._delObject(id)
        except: pass

    def get_portlets(self):
        """
        Looks up in the registry and returns all portlet objects to which the
        current user has access.
        """
        user = getSecurityManager().getUser()
        dmd = self.dmd.primaryAq()
        return filter(
            lambda x:user.has_permission(x.permission, dmd) and x.check(),
            self.portlets())

    def find(self, id='', sourcepath=''):
        """
        Look for a registered portlet with an id or source path.
        """
        for portlet in self.portlets():
            if portlet.id==id or portlet.sourcepath==sourcepath: return portlet
        return None

    def get_source(self, REQUEST=None):
        """
        Return the source of the portlets permitted to this user as a
        javascript file.
        """
        srcs = [x.get_source(DevelopmentMode) for x in self.get_portlets()]
        srcs.append('YAHOO.register("portletsource", YAHOO.zenoss.portlet, {})')
        if REQUEST:
            REQUEST.response.headers['Content-Type'] = 'text/javascript'
        return '\n'.join(srcs)

    def edit_portlet_perms(self, REQUEST=None):
        """
        blargh
        """
        for portlet in REQUEST.form:
            if not portlet.endswith('_permission'): continue
            portname = portlet.split('_')[0]
            p = self.find(id=portname)
            p.permission = REQUEST.form[portlet]
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            REQUEST['message'] = SaveMessage()
            REQUEST['RESPONSE'].redirect('/zport/dmd/editPortletPerms')


InitializeClass(PortletManager)


###########################################################################
#       
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#       
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#       
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope import interface
from Products.Five.viewlet.manager import ViewletManagerBase
from Products.ZenUtils.json import json
from Products.Five.viewlet import viewlet
from interfaces import ISecurityManager, IPermissionsDeclarationViewlet
from AccessControl import getSecurityManager


class SecurityManager(ViewletManagerBase):
    """The Viewlet manager class for the permissions declaration
    """ 
    interface.implements(ISecurityManager)


class PermissionsDeclaration(viewlet.ViewletBase):
    """This is responsible for sending to the client side
    which permissions the user has
    """
    interface.implements(IPermissionsDeclarationViewlet)

    def render(self):
        """Creates a global function in JavaScript that returns the
        json encoding of all the permissions available to the current
        user in the current context.  The permissions will be in the
        form of a dictionary.
        """
        permissions = self.permissionsForCurrentContext()
        data = json(permissions)
        func = """
<script type="text/javascript">
    function _global_permissions(){
        return %s;
    }
</script>
        """ % data
        return func

    def permissionsForCurrentContext(self):
        """Given a context return a list of all the permissions the logged in
        user has.
        """
        manager = getSecurityManager()
        all_permissions = self.context.zport.acl_users.possible_permissions()
        
        # filter out the ones we have in this context
        valid_permissions = [permission for permission in all_permissions 
                             if manager.checkPermission(permission, self.context)]
        
        # turn the list into a dictionary to make it easier to look up on
        # the client side (just look up the key instead of iterating)
        perms = {}
        for permission in valid_permissions:
            perms[permission.lower()] = True
        return perms

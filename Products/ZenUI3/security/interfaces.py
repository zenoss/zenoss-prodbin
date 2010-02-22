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
from zope.viewlet.interfaces import IViewletManager, IViewlet


class ISecurityManager(IViewletManager):
    """
    The Viewlet manager for the security declaratives
    """

class IPermissionsDeclarationViewlet(IViewlet):
    """
    Will return to the client side all of our security declaritives
    """


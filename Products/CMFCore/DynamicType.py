##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" DynamicType: Mixin for dynamic properties.

$Id: DynamicType.py 38612 2005-09-25 13:02:39Z jens $
"""

from urllib import quote

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from interfaces.Dynamic import DynamicType as IDynamicType
from utils import getToolByName


class DynamicType:
    """
    Mixin for portal content that allows the object to take on
    a dynamic type property.
    """

    __implements__ = IDynamicType

    portal_type = None

    security = ClassSecurityInfo()

    def _setPortalTypeName(self, pt):
        """ Set the portal type name.

        Called by portal_types during construction, records an ID that will be
        used later to locate the correct ContentTypeInformation.
        """
        self.portal_type = pt

    security.declarePublic('getPortalTypeName')
    def getPortalTypeName(self):
        """ Get the portal type name that can be passed to portal_types.
        """
        pt = self.portal_type
        if callable( pt ):
            pt = pt()
        return pt

    # deprecated alias
    _getPortalTypeName = getPortalTypeName

    security.declarePublic('getTypeInfo')
    def getTypeInfo(self):
        """ Get the TypeInformation object specified by the portal type.
        """
        tool = getToolByName(self, 'portal_types', None)
        if tool is None:
            return None
        return tool.getTypeInfo(self)  # Can return None.

    security.declarePublic('getActionInfo')
    def getActionInfo(self, action_chain, check_visibility=0,
                      check_condition=0):
        """ Get an Action info mapping specified by a chain of actions.
        """
        ti = self.getTypeInfo()
        if ti:
            return ti.getActionInfo(action_chain, self, check_visibility,
                                    check_condition)
        else:
            msg = 'Action "%s" not available for %s' % (
                        action_chain, '/'.join(self.getPhysicalPath()))
            raise ValueError(msg) 

    # Support for dynamic icons

    security.declarePublic('getIcon')
    def getIcon(self, relative_to_portal=0):
        """
        Using this method allows the content class
        creator to grab icons on the fly instead of using a fixed
        attribute on the class.
        """
        ti = self.getTypeInfo()
        if ti is not None:
            icon = quote(ti.getIcon())
            if icon:
                if relative_to_portal:
                    return icon
                else:
                    # Relative to REQUEST['BASEPATH1']
                    portal_url = getToolByName( self, 'portal_url' )
                    res = portal_url(relative=1) + '/' + icon
                    while res[:1] == '/':
                        res = res[1:]
                    return res
        return 'misc_/OFSP/dtmldoc.gif'

    security.declarePublic('icon')
    icon = getIcon  # For the ZMI

    def __before_publishing_traverse__(self, arg1, arg2=None):
        """ Pre-traversal hook.
        """
        # XXX hack around a bug(?) in BeforeTraverse.MultiHook
        REQUEST = arg2 or arg1

        if REQUEST['REQUEST_METHOD'] not in ('GET', 'POST'):
            return

        stack = REQUEST['TraversalRequestNameStack']
        key = stack and stack[-1] or '(Default)'
        ti = self.getTypeInfo()
        method_id = ti and ti.queryMethodID(key, context=self)
        if method_id:
            if key != '(Default)':
                stack.pop()
            if method_id != '(Default)':
                stack.append(method_id)
            REQUEST._hacked_path = 1

InitializeClass(DynamicType)

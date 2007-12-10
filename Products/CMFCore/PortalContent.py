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
""" PortalContent: Base class for all CMF content.

$Id: PortalContent.py 40634 2005-12-07 21:04:44Z tseaver $
"""

from Globals import InitializeClass
from Acquisition import aq_base
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo
from webdav.WriteLockInterface import WriteLockInterface

from interfaces.Contentish import Contentish
from DynamicType import DynamicType
from utils import _getViewFor
from CMFCatalogAware import CMFCatalogAware
from exceptions import ResourceLockedError
from permissions import FTPAccess
from permissions import View


# Old names that some third-party packages may need.
NoWL = 0


class PortalContent(DynamicType, CMFCatalogAware, SimpleItem):
    """
        Base class for portal objects.

        Provides hooks for reviewing, indexing, and CMF UI.

        Derived classes must implement the interface described in
        interfaces/DublinCore.py.
    """

    __implements__ = (Contentish,
                      WriteLockInterface,
                      DynamicType.__implements__)

    isPortalContent = 1
    _isPortalContent = 1  # More reliable than 'isPortalContent'.

    manage_options = ( ( { 'label'  : 'Dublin Core'
                         , 'action' : 'manage_metadata'
                         }
                       , { 'label'  : 'Edit'
                         , 'action' : 'manage_edit'
                         }
                       , { 'label'  : 'View'
                         , 'action' : 'view'
                         }
                       )
                     + CMFCatalogAware.manage_options
                     + SimpleItem.manage_options
                     )

    security = ClassSecurityInfo()

    security.declareObjectProtected(View)

    # The security for FTP methods aren't set up by default in our
    # superclasses...  :(
    security.declareProtected(FTPAccess, 'manage_FTPstat')
    security.declareProtected(FTPAccess, 'manage_FTPlist')

    def failIfLocked(self):
        """ Check if isLocked via webDav
        """
        if self.wl_isLocked():
            raise ResourceLockedError('This resource is locked via webDAV.')
        return 0

    #
    #   Contentish interface methods
    #
    security.declareProtected(View, 'SearchableText')
    def SearchableText(self):
        """ Returns a concatination of all searchable text.

        Should be overriden by portal objects.
        """
        return "%s %s" % (self.Title(), self.Description())

    def __call__(self):
        """ Invokes the default view.
        """
        ti = self.getTypeInfo()
        method_id = ti and ti.queryMethodID('(Default)', context=self)
        if method_id:
            method = getattr(self, method_id)
        else:
            method = _getViewFor(self)

        if getattr(aq_base(method), 'isDocTemp', 0):
            return method(self, self.REQUEST, self.REQUEST['RESPONSE'])
        else:
            return method()

    index_html = None  # This special value informs ZPublisher to use __call__

    security.declareProtected(View, 'view')
    def view(self):
        """ Returns the default view even if index_html is overridden.
        """
        return self()

InitializeClass(PortalContent)

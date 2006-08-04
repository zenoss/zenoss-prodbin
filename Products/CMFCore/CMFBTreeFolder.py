##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""CMFBTreeFolder

$Id: CMFBTreeFolder.py 37144 2005-07-13 02:31:01Z tseaver $
"""

from AccessControl.SecurityInfo import ClassSecurityInfo
from Globals import InitializeClass
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2Base

from PortalFolder import PortalFolderBase
from PortalFolder import factory_type_information as PortalFolder_FTI

_actions = PortalFolder_FTI[0]['actions']

factory_type_information = ( { 'id'             : 'CMF BTree Folder',
                               'meta_type'      : 'CMF BTree Folder',
                               'description'    : """\
CMF folder designed to hold a lot of objects.""",
                               'icon'           : 'folder_icon.gif',
                               'product'        : 'CMFCore',
                               'factory'        : 'manage_addCMFBTreeFolder',
                               'filter_content_types' : 0,
                               'immediate_view' : 'folder_edit_form',
                               'actions'        : _actions,
                               },
                           )


def manage_addCMFBTreeFolder(dispatcher, id, title='', REQUEST=None):
    """Adds a new BTreeFolder object with id *id*.
    """
    id = str(id)
    ob = CMFBTreeFolder(id)
    ob.title = str(title)
    dispatcher._setObject(id, ob)
    ob = dispatcher._getOb(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(ob.absolute_url() + '/manage_main' )


class CMFBTreeFolder(BTreeFolder2Base, PortalFolderBase):
    """BTree folder for CMF sites.
    """
    meta_type = 'CMF BTree Folder'
    security = ClassSecurityInfo()

    def __init__(self, id, title=''):
        PortalFolderBase.__init__(self, id, title)
        BTreeFolder2Base.__init__(self, id)

    def _checkId(self, id, allow_dup=0):
        PortalFolderBase._checkId(self, id, allow_dup)
        BTreeFolder2Base._checkId(self, id, allow_dup)


InitializeClass(CMFBTreeFolder)

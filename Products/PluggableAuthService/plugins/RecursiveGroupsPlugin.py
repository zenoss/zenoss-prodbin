##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Classes: RecursiveGroupsPlugin

$Id: RecursiveGroupsPlugin.py 40169 2005-11-16 20:09:11Z tseaver $
"""
from Acquisition import aq_parent
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from BTrees.OOBTree import OOBTree
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces.plugins \
    import IGroupsPlugin

from Products.PluggableAuthService.PropertiedUser import PropertiedUser
from Products.PluggableAuthService.permissions import ManageGroups
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import Interface

class IRecursiveGroupsPlugin(Interface):
    """ Marker interface.
    """

manage_addRecursiveGroupsPluginForm = PageTemplateFile(
    'www/rgpAdd', globals(), __name__='manage_addRecursiveGroupsPluginForm' )

def addRecursiveGroupsPlugin( dispatcher, id, title=None, REQUEST=None ):
    """ Add a RecursiveGroupsPlugin to a Pluggable Auth Service. """

    rgp = RecursiveGroupsPlugin(id, title)
    dispatcher._setObject(rgp.getId(), rgp)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(
                                '%s/manage_workspace'
                                '?manage_tabs_message='
                                'RecursiveGroupsPlugin+added.'
                            % dispatcher.absolute_url())

class SimpleGroup:

    def __init__( self, id ):
        self._id = id

    def getId( self ):
        return self._id

    def getGroups( self ):
        return ()

    def _addGroups( self, groups ):
        pass

class RecursiveGroupsPlugin( BasePlugin ):

    """ PAS plugin for recursively flattening a collection of groups
    """
    meta_type = 'Recursive Groups Plugin'

    security = ClassSecurityInfo()

    def __init__(self, id, title=None):

        self._id = self.id = id
        self.title = title

    #
    #   IGroupsPlugin implementation
    #
    security.declarePrivate( 'getGroupsForPrincipal' )
    def getGroupsForPrincipal( self, user, request=None ):

        set = list( user.getGroups() )
        seen = []
        parent = aq_parent( self )

        while set:
            test = set.pop(0)
            if test in seen:
                continue
            seen.append( test )
            new_groups = parent._getGroupsForPrincipal(
                PropertiedUser( test ).__of__(parent), 
                ignore_plugins=( self.getId(), ) )
            if new_groups:
                set.extend( new_groups )

        return tuple( seen )

classImplements( RecursiveGroupsPlugin
               , IRecursiveGroupsPlugin
               , IGroupsPlugin
               )

InitializeClass(RecursiveGroupsPlugin)

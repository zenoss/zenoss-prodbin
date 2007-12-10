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
""" Actions tool interface.

$Id: portal_actions.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class portal_actions(Interface):
    """ Gathers a list of links which the user is allowed to view according to
    the current context.
    """
    id = Attribute('id', 'Must be set to "portal_actions"')

    def listActionProviders():
        """ List the ids of all Action Providers queried by this tool.

        Permission -- Manage portal

        Returns -- Tuple of Action Provider ids
        """

    def addActionProvider(provider_name):
        """ Add an Action Provider id to the providers queried by this tool.

        A provider must implement the ActionProvider Interface.
        OldstyleActionProviders are currently also supported.

        The provider is only added if the actions tool can find the object
        corresponding to the provider_name.

        Permission -- Manage portal
        """

    def deleteActionProvider(provider_name):
        """ Delete an Action Provider id from providers queried by this tool.

        The deletion only takes place if provider_name is actually found among
        the known action providers.

        Permission -- Manage portal
        """

    def listFilteredActionsFor(object=None):
        """ List all actions available to the user.

        See the ActionInfo interface for provided keys. 'visible', 'available'
        and 'allowed' are always True in actions returned by this method.

        Permission -- Always available

        Returns -- Dictionary of category / ActionInfo list pairs
        """

    def listFilteredActions(object=None):
        """ Deprecated alias of listFilteredActionsFor.
        """


class ActionProvider(Interface):
    """ The interface expected of an object that can provide actions.
    """

    def listActions(info=None, object=None):
        """ List all the actions defined by a provider.

        If 'object' is specified, object specific actions are included.

        The 'info' argument is deprecated and may be removed in a future
        version. If 'object' isn't specified, the method uses for backwards
        compatibility 'info.content' as object.

        Returns -- Tuple of ActionInformation objects (or Action mappings)
        """

    def getActionObject(action):
        """Return the actions object or None if action doesn't exist.
        
        'action' is an action 'path' (e.g. 'object/view').
        
        Raises an ValueError exception if the action is of the wrong format.
        
        Permission -- Private
        
        Returns -- The actions object reference.
        """

    def listActionInfos(action_chain=None, object=None, check_visibility=1,
                        check_permissions=1, check_condition=1, max=-1):
        """ List ActionInfo objects.

        'action_chain' is a sequence of action 'paths' (e.g. 'object/view').
        If specified, only these actions will be returned in the given order.

        If 'object' is specified, object specific Actions are included.

        If 'max' is specified, only the first max Actions are returned.

        Permission -- Always available (not publishable)

        Returns -- Tuple of ActionInfo objects
        """

    def getActionInfo(action_chain, object=None, check_visibility=0,
                      check_condition=0):
        """ Get an ActionInfo object specified by a chain of actions.

        Permission -- Always available

        Returns -- ActionInfo object
        """


class ActionInfo(Interface):
    """ A lazy dictionary for Action infos.

    Each ActionInfo object has the following keys:

      - id (string): not unique identifier

      - title (string)

      - url (string): URL to access the action

      - category (string): one of "user", "folder", "object", "global",
        "workflow" or a custom category

      - visible (boolean)

      - available (boolean): the result of checking the condition

      - allowed (boolean): the result of checking permissions

    Deprecated keys:
        
      - name (string): use 'id' or 'title' instead

      - permissions (tuple): use 'allowed' instead; The user must have at
        least one of the listed permissions to access the action. If the list
        is empty, the user is allowed.
    """

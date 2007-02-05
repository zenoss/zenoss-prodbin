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
""" Workflow tool interface.

$Id: portal_workflow.py 40138 2005-11-15 17:47:37Z jens $
"""

from Interface import Attribute
from Interface import Interface

_marker = []


class portal_workflow(Interface):
    '''This tool accesses and changes the workflow state of content.
    '''
    id = Attribute('id', 'Must be set to "portal_workflow"')

    # security.declarePrivate('getCatalogVariablesFor')
    def getCatalogVariablesFor(ob):
        '''
        Invoked by portal_catalog.  Allows workflows
        to add variables to the catalog based on workflow status,
        making it possible to implement queues.
        Returns a mapping containing the catalog variables
        that apply to ob.
        '''

    # security.declarePublic('getActionsFor')
    def getActionsFor(ob):
        '''
        This method is deprecated and will be removed in CMF 2.0. 

        Return a list of action dictionaries for 'ob', just as though
        queried via 'ActionsTool.listFilteredActionsFor'.
        '''

    # security.declarePublic('doActionFor')
    def doActionFor(ob, action, wf_id=None, *args, **kw):
        '''
        Invoked by user interface code.
        Allows the user to request a workflow action.  The workflow object
        must perform its own security checks.
        '''

    # security.declarePublic('getInfoFor')
    def getInfoFor(ob, name, default=_marker, wf_id=None, *args, **kw):
        '''
        Invoked by user interface code.  Allows the user to request
        information provided by the workflow.  The workflow object
        must perform its own security checks.
        '''

    # security.declarePrivate('notifyCreated')
    def notifyCreated(ob):
        '''
        Notifies all applicable workflows after an object has been created
        and put in its new place.
        '''

    # security.declarePrivate('notifyBefore')
    def notifyBefore(ob, action):
        '''
        Notifies all applicable workflows of an action before it happens,
        allowing veto by exception.  Unless an exception is thrown, either
        a notifySuccess() or notifyException() can be expected later on.
        The action usually corresponds to a method name.
        '''

    # security.declarePrivate('notifySuccess')
    def notifySuccess(ob, action, result=None):
        '''
        Notifies all applicable workflows that an action has taken place.
        '''

    # security.declarePrivate('notifyException')
    def notifyException(ob, action, exc):
        '''
        Notifies all applicable workflows that an action failed.
        '''

    # security.declarePrivate('getHistoryOf')
    def getHistoryOf(wf_id, ob):
        '''
        Invoked by workflow definitions.  Returns the history
        of an object.
        '''

    # security.declarePrivate('getStatusOf')
    def getStatusOf(wf_id, ob):
        '''
        Invoked by workflow definitions.  Returns the last element of a
        history.
        '''

    # security.declarePrivate('setStatusOf')
    def setStatusOf(wf_id, ob, status):
        '''
        Invoked by workflow definitions.  Appends to the workflow history.
        '''


class WorkflowDefinition(Interface):
    '''The interface expected of workflow definitions objects.
    Accesses and changes the workflow state of objects.
    '''

    # security.declarePrivate('getCatalogVariablesFor')
    def getCatalogVariablesFor(ob):
        '''
        Invoked by the portal_workflow tool.
        Allows this workflow to make workflow-specific variables
        available to the catalog, making it possible to implement
        queues in a simple way.
        Returns a mapping containing the catalog variables
        that apply to ob.
        '''

    #security.declarePrivate('updateRoleMappingsFor')
    def updateRoleMappingsFor(ob):
        '''
        Updates the object permissions according to the current
        workflow state.
        '''

    # security.declarePrivate('listObjectActions')
    def listObjectActions(info):
        '''
        Invoked by the portal_workflow tool.
        Allows this workflow to
        include actions to be displayed in the actions box.
        Called only when this workflow is applicable to
        info.content.
        Returns the actions to be displayed to the user.
        '''

    # security.declarePrivate('listGlobalActions')
    def listGlobalActions(info):
        '''
        Invoked by the portal_workflow tool.
        Allows this workflow to
        include actions to be displayed in the actions box.
        Generally called on every request!
        Returns the actions to be displayed to the user.
        '''

    # security.declarePrivate('isActionSupported')
    def isActionSupported(ob, action):
        '''
        Invoked by the portal_workflow tool.
        Returns a true value if the given action name is supported.
        '''

    # security.declarePrivate('doActionFor')
    def doActionFor(ob, action, comment=''):
        '''
        Invoked by the portal_workflow tool.
        Allows the user to request a workflow action.  This method
        must perform its own security checks.
        '''

    # security.declarePrivate('isInfoSupported')
    def isInfoSupported(ob, name):
        '''
        Invoked by the portal_workflow tool.
        Returns a true value if the given info name is supported.
        '''

    # security.declarePrivate('getInfoFor')
    def getInfoFor(ob, name, default):
        '''
        Invoked by the portal_workflow tool.
        Allows the user to request information provided by the
        workflow.  This method must perform its own security checks.
        '''

    # security.declarePrivate('notifyCreated')
    def notifyCreated(ob):
        '''
        Invoked by the portal_workflow tool.
        Notifies this workflow after an object has been created
        and put in its new place.
        '''

    # security.declarePrivate('notifyBefore')
    def notifyBefore(ob, action):
        '''
        Invoked by the portal_workflow tool.
        Notifies this workflow of an action before it happens,
        allowing veto by exception.  Unless an exception is thrown, either
        a notifySuccess() or notifyException() can be expected later on.
        The action usually corresponds to a method name.
        '''

    # security.declarePrivate('notifySuccess')
    def notifySuccess(ob, action, result):
        '''
        Invoked by the portal_workflow tool.
        Notifies this workflow that an action has taken place.
        '''

    # security.declarePrivate('notifyException')
    def notifyException(ob, action, exc):
        '''
        Invoked by the portal_workflow tool.
        Notifies this workflow that an action failed.
        '''

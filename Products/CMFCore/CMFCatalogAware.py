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
""" Base class for catalog aware content items.

$Id: CMFCatalogAware.py 38390 2005-09-08 12:49:28Z anguenot $
"""

from zLOG import LOG, PROBLEM
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from ExtensionClass import Base
from Globals import DTMLFile
from Globals import InitializeClass

from permissions import AccessContentsInformation
from permissions import ManagePortal
from permissions import ModifyPortalContent
from utils import _dtmldir
from utils import _getAuthenticatedUser
from utils import getToolByName

from interfaces.IOpaqueItems import ICallableOpaqueItem

class CMFCatalogAware(Base):
    """Mix-in for notifying portal_catalog and portal_workflow
    """

    security = ClassSecurityInfo()

    # The following methods can be overriden using inheritence so that
    # it's possible to specifiy another catalog tool or workflow tool
    # for a given content type

    def _getCatalogTool(self):
        return getToolByName(self, 'portal_catalog', None)

    def _getWorkflowTool(self):
        return getToolByName(self, 'portal_workflow', None)

    # Cataloging methods
    # ------------------

    security.declareProtected(ModifyPortalContent, 'indexObject')
    def indexObject(self):
        """
            Index the object in the portal catalog.
        """
        catalog = self._getCatalogTool()
        if catalog is not None:
            catalog.indexObject(self)

    security.declareProtected(ModifyPortalContent, 'unindexObject')
    def unindexObject(self):
        """
            Unindex the object from the portal catalog.
        """
        catalog = self._getCatalogTool()
        if catalog is not None:
            catalog.unindexObject(self)

    security.declareProtected(ModifyPortalContent, 'reindexObject')
    def reindexObject(self, idxs=[]):
        """
            Reindex the object in the portal catalog.
            If idxs is present, only those indexes are reindexed.
            The metadata is always updated.

            Also update the modification date of the object,
            unless specific indexes were requested.
        """
        if idxs == []:
            # Update the modification date.
            if hasattr(aq_base(self), 'notifyModified'):
                self.notifyModified()
        catalog = self._getCatalogTool()
        if catalog is not None:
            catalog.reindexObject(self, idxs=idxs)

    _cmf_security_indexes = ('allowedRolesAndUsers',)

    security.declareProtected(ModifyPortalContent, 'reindexObjectSecurity')
    def reindexObjectSecurity(self, skip_self=False):
        """Reindex security-related indexes on the object.

        Recurses in the children to reindex them too.

        If skip_self is True, only the children will be reindexed. This
        is a useful optimization if the object itself has just been
        fully reindexed, as there's no need to reindex its security twice.
        """
        catalog = self._getCatalogTool()
        if catalog is None:
            return
        path = '/'.join(self.getPhysicalPath())

        # XXX if _getCatalogTool() is overriden we will have to change
        # this method for the sub-objects.
        for brain in catalog.unrestrictedSearchResults(path=path):
            brain_path = brain.getPath()
            if brain_path == path and skip_self:
                continue
            # Get the object
            if hasattr(aq_base(brain), '_unrestrictedGetObject'):
                ob = brain._unrestrictedGetObject()
            else:
                # BBB: Zope 2.7
                ob = self.unrestrictedTraverse(brain_path, None)
            if ob is None:
                # BBB: Ignore old references to deleted objects.
                # Can happen only in Zope 2.7, or when using
                # catalog-getObject-raises off in Zope 2.8
                LOG('reindexObjectSecurity', PROBLEM,
                    "Cannot get %s from catalog" % brain_path)
                continue
            # Recatalog with the same catalog uid.
            s = getattr(ob, '_p_changed', 0)
            catalog.reindexObject(ob, idxs=self._cmf_security_indexes,
                                  update_metadata=0, uid=brain_path)
            if s is None: ob._p_deactivate()

    # Workflow methods
    # ----------------

    security.declarePrivate('notifyWorkflowCreated')
    def notifyWorkflowCreated(self):
        """
            Notify the workflow that self was just created.
        """
        wftool = self._getWorkflowTool()
        if wftool is not None:
            wftool.notifyCreated(self)

    # Opaque subitems
    # ---------------

    security.declareProtected(AccessContentsInformation, 'opaqueItems')
    def opaqueItems(self):
        """
            Return opaque items (subelements that are contained
            using something that is not an ObjectManager).
        """
        items = []

        # Call 'talkback' knowing that it is an opaque item.
        # This will remain here as long as the discussion item does
        # not implement ICallableOpaqueItem (backwards compatibility).
        if hasattr(aq_base(self), 'talkback'):
            talkback = self.talkback
            if talkback is not None:
                items.append((talkback.id, talkback))

        # Other opaque items than 'talkback' may have callable
        # manage_after* and manage_before* hooks.
        # Loop over all attributes and add those to 'items'
        # implementing 'ICallableOpaqueItem'.
        self_base = aq_base(self)
        for name in self_base.__dict__.keys():
            obj = getattr(self_base, name)
            if ICallableOpaqueItem.isImplementedBy(obj):
                items.append((obj.getId(), obj))

        return tuple(items)

    security.declareProtected(AccessContentsInformation, 'opaqueIds')
    def opaqueIds(self):
        """
            Return opaque ids (subelements that are contained
            using something that is not an ObjectManager).
        """
        return [t[0] for t in self.opaqueItems()]

    security.declareProtected(AccessContentsInformation, 'opaqueValues')
    def opaqueValues(self):
        """
            Return opaque values (subelements that are contained
            using something that is not an ObjectManager).
        """
        return [t[1] for t in self.opaqueItems()]

    # Hooks
    # -----

    def manage_afterAdd(self, item, container):
        """
            Add self to the catalog.
            (Called when the object is created or moved.)
        """
        self.indexObject()
        self.__recurse('manage_afterAdd', item, container)

    def manage_afterClone(self, item):
        """
            Add self to the workflow.
            (Called when the object is cloned.)
        """
        self.notifyWorkflowCreated()
        self.__recurse('manage_afterClone', item)

        # Make sure owner local role is set after pasting
        # The standard Zope mechanisms take care of executable ownership
        current_user = _getAuthenticatedUser(self)
        if current_user is not None:
            local_role_holders = [x[0] for x in self.get_local_roles()]
            self.manage_delLocalRoles(local_role_holders)
            self.manage_setLocalRoles(current_user.getId(), ['Owner'])

    def manage_beforeDelete(self, item, container):
        """
            Remove self from the catalog.
            (Called when the object is deleted or moved.)
        """
        self.__recurse('manage_beforeDelete', item, container)
        self.unindexObject()

    def __recurse(self, name, *args):
        """
            Recurse in both normal and opaque subobjects.
        """
        values = self.objectValues()
        opaque_values = self.opaqueValues()
        for subobjects in values, opaque_values:
            for ob in subobjects:
                s = getattr(ob, '_p_changed', 0)
                if hasattr(aq_base(ob), name):
                    getattr(ob, name)(*args)
                if s is None: ob._p_deactivate()

    # ZMI
    # ---

    manage_options = ({'label': 'Workflows',
                       'action': 'manage_workflowsTab',
                       },
                       )

    _manage_workflowsTab = DTMLFile('zmi_workflows', _dtmldir)

    security.declareProtected(ManagePortal, 'manage_workflowsTab')
    def manage_workflowsTab(self, REQUEST, manage_tabs_message=None):
        """
            Tab displaying the current workflows for the content object.
        """
        ob = self
        wftool = self._getWorkflowTool()
        # XXX None ?
        if wftool is not None:
            wf_ids = wftool.getChainFor(ob)
            states = {}
            chain = []
            for wf_id in wf_ids:
                wf = wftool.getWorkflowById(wf_id)
                if wf is not None:
                    # XXX a standard API would be nice
                    if hasattr(wf, 'getReviewStateOf'):
                        # Default Workflow
                        state = wf.getReviewStateOf(ob)
                    elif hasattr(wf, '_getWorkflowStateOf'):
                        # DCWorkflow
                        state = wf._getWorkflowStateOf(ob, id_only=1)
                    else:
                        state = '(Unknown)'
                    states[wf_id] = state
                    chain.append(wf_id)
        return self._manage_workflowsTab(
            REQUEST,
            chain=chain,
            states=states,
            management_view='Workflows',
            manage_tabs_message=manage_tabs_message)

InitializeClass(CMFCatalogAware)

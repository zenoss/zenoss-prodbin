##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" CMFCore.interfaces package.

$Id: __init__.py 38636 2005-09-25 22:42:33Z tseaver $
"""

from _content import *
from _tools import *

import CachingPolicyManager
import Contentish
import ContentTypeRegistry
import Discussions
import DublinCore
import Dynamic
import Folderish
import IOpaqueItems
import portal_actions
import portal_catalog
import portal_discussion
import portal_memberdata
import portal_membership
import portal_metadata
import portal_properties
import portal_registration
import portal_skins
import portal_types
import portal_undo
import portal_url
import portal_workflow
import Syndicatable

# BBB: will be removed in CMF 2.2
#      create zope2 interfaces
from Interface.bridge import createZope3Bridge
createZope3Bridge(ICachingPolicyManager, CachingPolicyManager,
                  'CachingPolicyManager')
createZope3Bridge(IContentish, Contentish, 'Contentish')
createZope3Bridge(IContentTypeRegistryPredicate, ContentTypeRegistry,
                  'ContentTypeRegistryPredicate')
createZope3Bridge(IContentTypeRegistry, ContentTypeRegistry,
                  'ContentTypeRegistry')
createZope3Bridge(IDiscussable, Discussions, 'Discussable')
createZope3Bridge(IOldstyleDiscussable, Discussions, 'OldDiscussable')
createZope3Bridge(IDiscussionResponse, Discussions, 'DiscussionResponse')
createZope3Bridge(IDublinCore, DublinCore, 'DublinCore')
createZope3Bridge(ICatalogableDublinCore, DublinCore, 'CatalogableDublinCore')
createZope3Bridge(IMutableDublinCore, DublinCore, 'MutableDublinCore')
createZope3Bridge(IDynamicType, Dynamic, 'DynamicType')
createZope3Bridge(IFolderish, Folderish, 'Folderish')
createZope3Bridge(ICallableOpaqueItem, IOpaqueItems, 'ICallableOpaqueItem')
createZope3Bridge(ICallableOpaqueItemEvents, IOpaqueItems,
                  'ICallableOpaqueItemEvents')
createZope3Bridge(IActionsTool, portal_actions, 'portal_actions')
createZope3Bridge(IActionProvider, portal_actions, 'ActionProvider')
createZope3Bridge(IActionInfo, portal_actions, 'ActionInfo')
createZope3Bridge(ICatalogTool, portal_catalog, 'portal_catalog')
createZope3Bridge(IIndexableObjectWrapper, portal_catalog,
                  'IndexableObjectWrapper')
createZope3Bridge(IOldstyleDiscussionTool, portal_discussion,
                  'oldstyle_portal_discussion')
createZope3Bridge(IDiscussionTool, portal_discussion, 'portal_discussion')
createZope3Bridge(IMemberDataTool, portal_memberdata, 'portal_memberdata')
createZope3Bridge(IMemberData, portal_memberdata, 'MemberData')
createZope3Bridge(IMembershipTool, portal_membership, 'portal_membership')
createZope3Bridge(IMetadataTool, portal_metadata, 'portal_metadata')
createZope3Bridge(IPropertiesTool, portal_properties, 'portal_properties')
createZope3Bridge(IRegistrationTool, portal_registration,
                  'portal_registration')
createZope3Bridge(ISkinsContainer, portal_skins, 'SkinsContainer')
createZope3Bridge(ISkinsTool, portal_skins, 'portal_skins')
createZope3Bridge(ITypeInformation, portal_types, 'ContentTypeInformation')
createZope3Bridge(ITypesTool, portal_types, 'portal_types')
createZope3Bridge(IUndoTool, portal_undo, 'portal_undo')
createZope3Bridge(IURLTool, portal_url, 'portal_url')
createZope3Bridge(IWorkflowTool, portal_workflow, 'portal_workflow')
createZope3Bridge(IWorkflowDefinition, portal_workflow, 'WorkflowDefinition')
createZope3Bridge(ISyndicatable, Syndicatable, 'Syndicatable')

del createZope3Bridge

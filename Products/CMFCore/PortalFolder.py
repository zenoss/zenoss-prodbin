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
""" PortalFolder: CMF-enabled Folder objects.

$Id: PortalFolder.py 40136 2005-11-15 17:41:36Z jens $
"""

import base64
import marshal
import re
from warnings import warn

from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from Acquisition import aq_parent, aq_inner, aq_base
from Globals import DTMLFile
from Globals import InitializeClass
from OFS.OrderSupport import OrderSupport
from OFS.Folder import Folder

from CMFCatalogAware import CMFCatalogAware
from DynamicType import DynamicType
from exceptions import AccessControl_Unauthorized
from exceptions import BadRequest
from exceptions import zExceptions_Unauthorized
from interfaces.Folderish import Folderish as IFolderish
from permissions import AddPortalContent
from permissions import AddPortalFolders
from permissions import ChangeLocalRoles
from permissions import DeleteObjects
from permissions import ListFolderContents
from permissions import ManagePortal
from permissions import ManageProperties
from permissions import View
from utils import _checkPermission
from utils import getToolByName


factory_type_information = (
  { 'id'             : 'Folder'
  , 'meta_type'      : 'Portal Folder'
  , 'description'    : """ Use folders to put content in categories."""
  , 'icon'           : 'folder_icon.gif'
  , 'product'        : 'CMFCore'
  , 'factory'        : 'manage_addPortalFolder'
  , 'filter_content_types' : 0
  , 'immediate_view' : 'folder_edit_form'
  , 'aliases'        : {'(Default)': 'index_html',
                        'view': 'index_html',
                        'index.html':'index_html'}
  , 'actions'        : ( { 'id'            : 'view'
                         , 'name'          : 'View'
                         , 'action': 'string:${object_url}'
                         , 'permissions'   : (View,)
                         }
                       , { 'id'            : 'edit'
                         , 'name'          : 'Edit'
                         , 'action': 'string:${object_url}/folder_edit_form'
                         , 'permissions'   : (ManageProperties,)
                         }
                       , { 'id'            : 'localroles'
                         , 'name'          : 'Local Roles'
                         , 'action':
                                  'string:${object_url}/folder_localrole_form'
                         , 'permissions'   : (ChangeLocalRoles,)
                         }
                       , { 'id'            : 'folderContents'
                         , 'name'          : 'Folder contents'
                         , 'action': 'string:${object_url}/folder_contents'
                         , 'permissions'   : (ListFolderContents,)
                         }
                       , { 'id'            : 'new'
                         , 'name'          : 'New...'
                         , 'action': 'string:${object_url}/folder_factories'
                         , 'permissions'   : (AddPortalContent,)
                         , 'visible'       : 0
                         }
                       , { 'id'            : 'rename_items'
                         , 'name'          : 'Rename items'
                         , 'action': 'string:${object_url}/folder_rename_form'
                         , 'permissions'   : (AddPortalContent,)
                         , 'visible'       : 0
                         }
                       )
  }
,
)


class PortalFolderBase(DynamicType, CMFCatalogAware, Folder):
    """Base class for portal folder
    """
    meta_type = 'Portal Folder Base'

    __implements__ = (IFolderish, DynamicType.__implements__,
                      Folder.__implements__)

    security = ClassSecurityInfo()

    description = ''

    manage_options = ( Folder.manage_options +
                       CMFCatalogAware.manage_options )

    def __init__( self, id, title='' ):
        self.id = id
        self.title = title

    #
    #   'MutableDublinCore' interface methods
    #
    security.declareProtected(ManageProperties, 'setTitle')
    def setTitle( self, title ):
        """ Set Dublin Core Title element - resource name.
        """
        self.title = title

    security.declareProtected(ManageProperties, 'setDescription')
    def setDescription( self, description ):
        """ Set Dublin Core Description element - resource summary.
        """
        self.description = description

    #
    #   other methods
    #
    security.declareProtected(ManageProperties, 'edit')
    def edit(self, title='', description=''):
        """
        Edit the folder title (and possibly other attributes later)
        """
        self.setTitle( title )
        self.setDescription( description )
        self.reindexObject()

    security.declarePublic('allowedContentTypes')
    def allowedContentTypes( self ):
        """
            List type info objects for types which can be added in
            this folder.
        """
        result = []
        portal_types = getToolByName(self, 'portal_types')
        myType = portal_types.getTypeInfo(self)

        if myType is not None:
            for contentType in portal_types.listTypeInfo(self):
                if myType.allowType( contentType.getId() ):
                    result.append( contentType )
        else:
            result = portal_types.listTypeInfo()

        return filter( lambda typ, container=self:
                          typ.isConstructionAllowed( container )
                     , result )


    def _morphSpec(self, spec):
        '''
        spec is a sequence of meta_types, a string containing one meta type,
        or None.  If spec is empty or None, returns all contentish
        meta_types.  Otherwise ensures all of the given meta types are
        contentish.
        '''
        warn('Using the \'spec\' argument is deprecated. In CMF 2.0 '
             'contentItems(), contentIds(), contentValues() and '
             'listFolderContents() will no longer support \'spec\'. Use the '
             '\'filter\' argument with \'portal_type\' instead.',
             DeprecationWarning)
        new_spec = []
        types_tool = getToolByName(self, 'portal_types')
        types = types_tool.listContentTypes( by_metatype=1 )
        if spec is not None:
            if type(spec) == type(''):
                spec = [spec]
            for meta_type in spec:
                if not meta_type in types:
                    raise ValueError('%s is not a content type' % meta_type)
                new_spec.append(meta_type)
        return new_spec or types

    def _filteredItems( self, ids, filt ):
        """
            Apply filter, a mapping, to child objects indicated by 'ids',
            returning a sequence of ( id, obj ) tuples.
        """
        # Restrict allowed content types
        if filt is None:
            filt = {}
        else:
            # We'll modify it, work on a copy.
            filt = filt.copy()
        pt = filt.get('portal_type', [])
        if type(pt) is type(''):
            pt = [pt]
        types_tool = getToolByName(self, 'portal_types')
        allowed_types = types_tool.listContentTypes()
        if not pt:
            pt = allowed_types
        else:
            pt = [t for t in pt if t in allowed_types]
        if not pt:
            # After filtering, no types remain, so nothing should be
            # returned.
            return []
        filt['portal_type'] = pt

        query = ContentFilter(**filt)
        result = []
        append = result.append
        get = self._getOb
        for id in ids:
            obj = get( id )
            if query(obj):
                append( (id, obj) )
        return result

    #
    #   'Folderish' interface methods
    #
    security.declarePublic('contentItems')
    def contentItems( self, spec=None, filter=None ):
        # List contentish and folderish sub-objects and their IDs.
        # (method is without docstring to disable publishing)
        #
        if spec is None:
            ids = self.objectIds()
        else:
            # spec is deprecated, use filter instead!
            spec = self._morphSpec(spec)
            ids = self.objectIds(spec)
        return self._filteredItems( ids, filter )

    security.declarePublic('contentIds')
    def contentIds( self, spec=None, filter=None):
        # List IDs of contentish and folderish sub-objects.
        # (method is without docstring to disable publishing)
        #
        if spec is None:
            ids = self.objectIds()
        else:
            # spec is deprecated, use filter instead!
            spec = self._morphSpec(spec)
            ids = self.objectIds(spec)
        return map( lambda item: item[0],
                    self._filteredItems( ids, filter ) )

    security.declarePublic('contentValues')
    def contentValues( self, spec=None, filter=None ):
        # List contentish and folderish sub-objects.
        # (method is without docstring to disable publishing)
        #
        if spec is None:
            ids = self.objectIds()
        else:
            # spec is deprecated, use filter instead!
            spec = self._morphSpec(spec)
            ids = self.objectIds(spec)
        return map( lambda item: item[1],
                    self._filteredItems( ids, filter ) )

    security.declareProtected(ListFolderContents, 'listFolderContents')
    def listFolderContents( self, spec=None, contentFilter=None ):
        """ List viewable contentish and folderish sub-objects.
        """
        items = self.contentItems(spec=spec, filter=contentFilter)
        l = []
        for id, obj in items:
            # validate() can either raise Unauthorized or return 0 to
            # mean unauthorized.
            try:
                if getSecurityManager().validate(self, self, id, obj):
                    l.append(obj)
            except zExceptions_Unauthorized:  # Catch *all* Unauths!
                pass
        return l

    #
    #   webdav Resource method
    #

    # protected by 'WebDAV access'
    def listDAVObjects(self):
        # List sub-objects for PROPFIND requests.
        # (method is without docstring to disable publishing)
        #
        if _checkPermission(ManagePortal, self):
            return self.objectValues()
        else:
            return self.listFolderContents()

    #
    #   'DublinCore' interface methods
    #
    security.declareProtected(View, 'Title')
    def Title( self ):
        """ Dublin Core Title element - resource name.
        """
        return self.title

    security.declareProtected(View, 'Description')
    def Description( self ):
        """ Dublin Core Description element - resource summary.
        """
        return self.description

    security.declareProtected(View, 'Type')
    def Type( self ):
        """ Dublin Core Type element - resource type.
        """
        if hasattr(aq_base(self), 'getTypeInfo'):
            ti = self.getTypeInfo()
            if ti is not None:
                return ti.Title()
        return self.meta_type

    #
    #   other methods
    #
    security.declarePublic('encodeFolderFilter')
    def encodeFolderFilter(self, REQUEST):
        """
            Parse cookie string for using variables in dtml.
        """
        filter = {}
        for key, value in REQUEST.items():
            if key[:10] == 'filter_by_':
                filter[key[10:]] = value
        encoded = base64.encodestring( marshal.dumps(filter) ).strip()
        encoded = ''.join( encoded.split('\n') )
        return encoded

    security.declarePublic('decodeFolderFilter')
    def decodeFolderFilter(self, encoded):
        """
            Parse cookie string for using variables in dtml.
        """
        filter = {}
        if encoded:
            filter.update(marshal.loads(base64.decodestring(encoded)))
        return filter

    def content_type( self ):
        """
            WebDAV needs this to do the Right Thing (TM).
        """
        return None

    # Ensure pure PortalFolders don't get cataloged.
    # XXX We may want to revisit this.

    def indexObject(self):
        pass

    def unindexObject(self):
        pass

    def reindexObject(self, idxs=[]):
        pass

    def reindexObjectSecurity(self):
        pass

    def PUT_factory( self, name, typ, body ):
        """ Factory for PUT requests to objects which do not yet exist.

        Used by NullResource.PUT.

        Returns -- Bare and empty object of the appropriate type (or None, if
        we don't know what to do)
        """
        registry = getToolByName(self, 'content_type_registry', None)
        if registry is None:
            return None

        typeObjectName = registry.findTypeName( name, typ, body )
        if typeObjectName is None:
            return None

        self.invokeFactory( typeObjectName, name )

        # invokeFactory does too much, so the object has to be removed again
        obj = aq_base( self._getOb( name ) )
        self._delObject( name )
        return obj

    security.declareProtected(AddPortalContent, 'invokeFactory')
    def invokeFactory(self, type_name, id, RESPONSE=None, *args, **kw):
        """ Invokes the portal_types tool.
        """
        pt = getToolByName(self, 'portal_types')
        myType = pt.getTypeInfo(self)

        if myType is not None:
            if not myType.allowType( type_name ):
                raise ValueError('Disallowed subobject type: %s' % type_name)

        return pt.constructContent(type_name, self, id, RESPONSE, *args, **kw)

    security.declareProtected(AddPortalContent, 'checkIdAvailable')
    def checkIdAvailable(self, id):
        try:
            self._checkId(id)
        except BadRequest:
            return False
        else:
            return True

    def MKCOL_handler(self,id,REQUEST=None,RESPONSE=None):
        """
            Handle WebDAV MKCOL.
        """
        self.manage_addFolder( id=id, title='' )

    def _checkId(self, id, allow_dup=0):
        PortalFolderBase.inheritedAttribute('_checkId')(self, id, allow_dup)

        if allow_dup:
            return

        # FIXME: needed to allow index_html for join code
        if id == 'index_html':
            return

        # Another exception: Must allow "syndication_information" to enable
        # Syndication...
        if id == 'syndication_information':
            return

        # This code prevents people other than the portal manager from
        # overriding skinned names and tools.
        if not getSecurityManager().checkPermission(ManagePortal, self):
            ob = self
            while ob is not None and not getattr(ob, '_isPortalRoot', False):
                ob = aq_parent( aq_inner(ob) )
            if ob is not None:
                # If the portal root has a non-contentish object by this name,
                # don't allow an override.
                if (hasattr(ob, id) and
                    id not in ob.contentIds() and
                    # Allow root doted prefixed object name overrides
                    not id.startswith('.')):
                    raise BadRequest('The id "%s" is reserved.' % id)
            # Don't allow ids used by Method Aliases.
            ti = self.getTypeInfo()
            if ti and ti.queryMethodID(id, context=self):
                raise BadRequest('The id "%s" is reserved.' % id)
        # Otherwise we're ok.

    def _verifyObjectPaste(self, object, validate_src=1):
        # This assists the version in OFS.CopySupport.
        # It enables the clipboard to function correctly
        # with objects created by a multi-factory.
        securityChecksDone = False
        sm = getSecurityManager()
        parent = aq_parent(aq_inner(object))
        object_id = object.getId()
        mt = getattr(object, '__factory_meta_type__', None)
        meta_types = getattr(self, 'all_meta_types', None)

        if mt is not None and meta_types is not None:
            method_name=None
            permission_name = None

            if callable(meta_types):
                meta_types = meta_types()

            for d in meta_types:

                if d['name']==mt:
                    method_name=d['action']
                    permission_name = d.get('permission', None)
                    break

            if permission_name is not None:

                if not sm.checkPermission(permission_name,self):
                    raise AccessControl_Unauthorized, method_name

                if validate_src:

                    if not sm.validate(None, parent, None, object):
                        raise AccessControl_Unauthorized, object_id

                if validate_src > 1:
                    if not sm.checkPermission(DeleteObjects, parent):
                        raise AccessControl_Unauthorized

                # validation succeeded
                securityChecksDone = 1

            #
            # Old validation for objects that may not have registered
            # themselves in the proper fashion.
            #
            elif method_name is not None:

                meth = self.unrestrictedTraverse(method_name)

                factory = getattr(meth, 'im_self', None)

                if factory is None:
                    factory = aq_parent(aq_inner(meth))

                if not sm.validate(None, factory, None, meth):
                    raise AccessControl_Unauthorized, method_name

                # Ensure the user is allowed to access the object on the
                # clipboard.
                if validate_src:

                    if not sm.validate(None, parent, None, object):
                        raise AccessControl_Unauthorized, object_id

                if validate_src > 1: # moving
                    if not sm.checkPermission(DeleteObjects, parent):
                        raise AccessControl_Unauthorized

                securityChecksDone = 1

        # Call OFS' _verifyObjectPaste if necessary
        if not securityChecksDone:
            PortalFolderBase.inheritedAttribute(
                '_verifyObjectPaste')(self, object, validate_src)

        # Finally, check allowed content types
        if hasattr(aq_base(object), 'getPortalTypeName'):

            type_name = object.getPortalTypeName()

            if type_name is not None:

                pt = getToolByName(self, 'portal_types')
                myType = pt.getTypeInfo(self)

                if myType is not None and not myType.allowType(type_name):
                    raise ValueError('Disallowed subobject type: %s'
                                        % type_name)

    security.setPermissionDefault(AddPortalContent, ('Owner','Manager'))

    security.declareProtected(AddPortalFolders, 'manage_addFolder')
    def manage_addFolder( self
                        , id
                        , title=''
                        , REQUEST=None
                        ):
        """ Add a new folder-like object with id *id*.

        IF present, use the parent object's 'mkdir' alias; otherwise, just add
        a PortalFolder.
        """
        ti = self.getTypeInfo()
        method_id = ti and ti.queryMethodID('mkdir', context=self)
        if method_id:
            # call it
            getattr(self, method_id)(id=id)
        else:
            self.invokeFactory( type_name='Folder', id=id )

        ob = self._getOb( id )
        ob.setTitle( title )
        try:
            ob.reindexObject()
        except AttributeError:
            pass

        if REQUEST is not None:
            return self.manage_main(self, REQUEST, update_menu=1)

InitializeClass(PortalFolderBase)


class PortalFolder(OrderSupport, PortalFolderBase):
    """
        Implements portal content management, but not UI details.
    """
    meta_type = 'Portal Folder'
    portal_type = 'Folder'

    __implements__ = (PortalFolderBase.__implements__,
                      OrderSupport.__implements__)

    security = ClassSecurityInfo()

    manage_options = ( OrderSupport.manage_options +
                       PortalFolderBase.manage_options[1:] )

    security.declareProtected(AddPortalFolders, 'manage_addPortalFolder')
    def manage_addPortalFolder(self, id, title='', REQUEST=None):
        """Add a new PortalFolder object with id *id*.
        """
        ob = PortalFolder(id, title)
        self._setObject(id, ob)
        if REQUEST is not None:
            return self.folder_contents( # XXX: ick!
                self, REQUEST, portal_status_message="Folder added")

InitializeClass(PortalFolder)


class ContentFilter:
    """
        Represent a predicate against a content object's metadata.
    """
    MARKER = []
    filterSubject = []
    def __init__( self
                , Title=MARKER
                , Creator=MARKER
                , Subject=MARKER
                , Description=MARKER
                , created=MARKER
                , created_usage='range:min'
                , modified=MARKER
                , modified_usage='range:min'
                , Type=MARKER
                , portal_type=MARKER
                , **Ignored
                ):

        self.predicates = []
        self.description = []

        if Title is not self.MARKER:
            self.predicates.append( lambda x, pat=re.compile( Title ):
                                      pat.search( x.Title() ) )
            self.description.append( 'Title: %s' % Title )

        if Creator and Creator is not self.MARKER:
            self.predicates.append( lambda x, creator=Creator:
                                    creator in x.listCreators() )
            self.description.append( 'Creator: %s' % Creator )

        if Subject and Subject is not self.MARKER:
            self.filterSubject = Subject
            self.predicates.append( self.hasSubject )
            self.description.append( 'Subject: %s' % ', '.join(Subject) )

        if Description is not self.MARKER:
            self.predicates.append( lambda x, pat=re.compile( Description ):
                                      pat.search( x.Description() ) )
            self.description.append( 'Description: %s' % Description )

        if created is not self.MARKER:
            if created_usage == 'range:min':
                self.predicates.append( lambda x, cd=created:
                                          cd <= x.created() )
                self.description.append( 'Created since: %s' % created )
            if created_usage == 'range:max':
                self.predicates.append( lambda x, cd=created:
                                          cd >= x.created() )
                self.description.append( 'Created before: %s' % created )

        if modified is not self.MARKER:
            if modified_usage == 'range:min':
                self.predicates.append( lambda x, md=modified:
                                          md <= x.modified() )
                self.description.append( 'Modified since: %s' % modified )
            if modified_usage == 'range:max':
                self.predicates.append( lambda x, md=modified:
                                          md >= x.modified() )
                self.description.append( 'Modified before: %s' % modified )

        if Type:
            if type( Type ) == type( '' ):
                Type = [ Type ]
            self.predicates.append( lambda x, Type=Type:
                                      x.Type() in Type )
            self.description.append( 'Type: %s' % ', '.join(Type) )

        if portal_type and portal_type is not self.MARKER:
            if type(portal_type) is type(''):
                portal_type = [portal_type]
            self.predicates.append( lambda x, pt=portal_type:
                                    hasattr(aq_base(x), 'getPortalTypeName')
                                    and x.getPortalTypeName() in pt )
            self.description.append( 'Portal Type: %s'
                                     % ', '.join(portal_type) )

    def hasSubject( self, obj ):
        """
        Converts Subject string into a List for content filter view.
        """
        for sub in obj.Subject():
            if sub in self.filterSubject:
                return 1
        return 0

    def __call__( self, content ):

        for predicate in self.predicates:

            try:
                if not predicate( content ):
                    return 0
            except (AttributeError, KeyError, IndexError, ValueError):
                # predicates are *not* allowed to throw exceptions
                return 0

        return 1

    def __str__( self ):
        """
            Return a stringified description of the filter.
        """
        return '; '.join(self.description)

manage_addPortalFolder = PortalFolder.manage_addPortalFolder.im_func
manage_addPortalFolderForm = DTMLFile( 'folderAdd', globals() )

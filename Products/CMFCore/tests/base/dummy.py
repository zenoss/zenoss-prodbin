##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Unit test dummies.

$Id: dummy.py 69189 2006-07-18 18:48:28Z tseaver $
"""

from Acquisition import Implicit, aq_base, aq_inner, aq_parent
from OFS.SimpleItem import Item

from Products.CMFCore.ActionProviderBase import ActionProviderBase
from Products.CMFCore.PortalContent import PortalContent
from security import OmnipotentUser

from DateTime import DateTime
from webdav.common import rfc1123_date

class DummyObject(Implicit):
    """
    A dummy callable object.
    Comes with getIcon and restrictedTraverse
    methods.
    """
    def __init__(self, id='dummy',**kw):
        self._id = id
        self.__dict__.update( kw )

    def __str__(self):
        return self._id

    def __call__(self):
        return self._id

    def restrictedTraverse( self, path ):
        return path and getattr( self, path ) or self

    def getIcon( self, relative=0 ):
        return 'Site: %s' % relative

    def getId(self):
        return self._id


class DummyType(DummyObject):
    """ A Dummy Type object """

    def __init__(self, id='Dummy Content', title='Dummy Content', actions=()):
        """ To fake out some actions, pass in a sequence of tuples where the
        first element represents the ID or alias of the action and the
        second element is the path to the object to be invoked, such as 
        a page template.
        """

        self.id = self._id = id
        self.title = title
        self._actions = {}

        self._setActions(actions)

    def _setActions(self, actions=()):
        for action_id, action_path in actions:
            self._actions[action_id] = action_path

    def Title(self):
        return self.title

    def queryMethodID(self, alias, default=None, context=None):
        return self._actions.get(alias, default)

    def allowDiscussion(self):
        return False

    def listActions(self, info=None, object=None):
        rs = []
        for k,v in self._actions.items():
           rs.append( DummyAction( k,v ) )
        return rs

class DummyAction:

    def __init__( self, id, target, permissions=() ):
        self._id = id
        self.target = target
        self.permissions = permissions

    def getId( self ):
        return self._id

    # can this be right? e.g. utils._getViewFor calls action
    # attribute directly, which is not part of API but no other way
    # to do it...
    def action( self, context ):
        return self.target

    def getPermissions( self ):
        return self.permissions

class DummyContent( PortalContent, Item ):
    """
    A Dummy piece of PortalContent
    """
    meta_type = 'Dummy'
    portal_type = 'Dummy Content'
    url = 'foo_url'
    after_add_called = before_delete_called = 0

    def __init__( self, id='dummy', *args, **kw ):
        self.id = id
        self._args = args
        self._kw = {}
        self._kw.update( kw )

        self.reset()
        self.catalog = kw.get('catalog',0)
        self.url = kw.get('url',None)

    def manage_afterAdd( self, item, container ):
        self.after_add_called = 1
        if self.catalog:
            PortalContent.manage_afterAdd( self, item, container )

    def manage_beforeDelete( self, item, container ):
        self.before_delete_called = 1
        if self.catalog:
            PortalContent.manage_beforeDelete( self, item, container )

    def absolute_url(self):
       return self.url

    def reset( self ):
        self.after_add_called = self.before_delete_called = 0

    # Make sure normal Database export/import stuff doesn't trip us up.
    def _getCopy(self, container):
        return DummyContent( self.id, catalog=self.catalog )

    def _safe_get(self,attr):
        if self.catalog:
            return getattr(self,attr,'')
        else:
            return getattr(self,attr)

    def Title( self ):
        return self.title

    def listCreators(self):
        return self._safe_get('creators')

    def Subject( self ):
        return self._safe_get('subject')

    def Description( self ):
        return self._safe_get('description')

    def created( self ):
        return self._safe_get('created_date')

    def modified( self ):
        return self._safe_get('modified_date')

    def Type( self ):
        return 'Dummy Content Title'


class DummyFactory:
    """
    Dummy Product Factory
    """
    def __init__( self, folder ):
        self._folder = folder

    def getId(self):
        return 'DummyFactory'

    def addFoo( self, id, *args, **kw ):
        if getattr(self._folder, '_prefix', None):
            id = '%s_%s' % ( self._folder._prefix, id )
        foo = DummyContent(id, *args, **kw)
        self._folder._setObject(id, foo)
        if getattr(self._folder, '_prefix', None):
            return id

    __roles__ = ( 'FooAdder', )
    __allow_access_to_unprotected_subobjects__ = { 'addFoo' : 1 }


class DummyFolder(DummyObject):
    """
        Dummy Container for testing
    """
    def __init__( self, id='dummy', fake_product=0, prefix='' ):
        self._prefix = prefix
        self._id = id

        if fake_product:
            self.manage_addProduct = { 'FooProduct' : DummyFactory( self ) }

    def _setOb(self, id, object):
        setattr(self, id, object)

    def _delOb(self, id):
        delattr(self, id)

    def _getOb( self, id ):
        return getattr(self, id)

    def _setObject(self, id, object):
        self._setOb(id, object)
        object = self._getOb(id)
        if hasattr(aq_base(object), 'manage_afterAdd'):
            object.manage_afterAdd(object, self)
        return object

    def _delObject(self, id):
        object = self._getOb(id)
        if hasattr(aq_base(object), 'manage_beforeDelete'):
            object.manage_beforeDelete(object, self)
        self._delOb(id)

    def getPhysicalPath(self):
        p = aq_parent(aq_inner(self))
        path = (self._id, )
        if p is not None:
            path = p.getPhysicalPath() + path
        return path

    def getId(self):
        return self._id

    def reindexObjectSecurity(self):
        pass

    def contentIds(self):
        return ('user_bar',)


class DummySite(DummyFolder):
    """ A dummy portal folder.
    """

    _domain = 'http://www.foobar.com'
    _path = 'bar'
    _isPortalRoot = 1

    def absolute_url(self, relative=0):
        return '/'.join( (self._domain, self._path, self._id) )

    def getPhysicalPath(self):
        return ('', self._path, self._id)

    def getPhysicalRoot(self):
        return self

    def unrestrictedTraverse(self, path, default=None, restricted=0):
        if path == ['acl_users']:
            return self.acl_users
        else:
            obj = self
            for id in path[3:]:
                obj = getattr(obj, id)
            return obj

    def userdefined_roles(self):
        return ('Member', 'Reviewer')


class DummyUser(Implicit):
    """ A dummy User.
    """

    def __init__(self, id='dummy'):
        self.id = id

    def getId(self):
        return self.id

    getUserName = getId

    def allowed(self, object, object_roles=None):
        if object_roles is None or 'Anonymous' in object_roles:
            return 1
        for role in object_roles:
            if role in self.getRolesInContext(object):
                return 1
        return 0

    def getRolesInContext(self, object):
        return ('Authenticated', 'Dummy', 'Member')

    def _check_context(self, object):
        return 1


class DummyUserFolder(Implicit):
    """ A dummy User Folder with 2 dummy Users.
    """

    id = 'acl_users'

    def __init__(self):
        setattr( self, 'user_foo', DummyUser(id='user_foo') )
        setattr( self, 'user_bar', DummyUser(id='user_bar') )
        setattr( self, 'all_powerful_Oz', OmnipotentUser() )

    def getUsers(self):
        pass

    def getUser(self, name):
        return getattr(self, name, None)

    def getUserById(self, id, default=None):
        return self.getUser(id)

    def userFolderDelUsers(self, names):
        for user_id in names:
            delattr(self, user_id)


class DummyTool(Implicit,ActionProviderBase):
    """
    This is a Dummy Tool that behaves as a
    a MemberShipTool, a URLTool and an
    Action Provider
    """

    root = 'DummyTool'

    view_actions = ( ('', 'dummy_view')
                   , ('view', 'dummy_view')
                   , ('(Default)', 'dummy_view')
                   )


    def __init__(self, anon=1):
        self.anon = anon

    def __call__( self ):
        return self.root

    getPortalPath = __call__

    def getPortalObject( self ):
        return aq_parent( aq_inner( self ) )

    def getIcon( self, relative=0 ):
        return 'Tool: %s' % relative

    # MembershipTool
    def getAuthenticatedMember(self):
        return DummyUser()

    def isAnonymousUser(self):
        return self.anon

    def checkPermission(self, permissionName, object, subobjectName=None):
        return True

    # TypesTool
    def listTypeInfo(self, container=None):
        typ = 'Dummy Content'
        return ( DummyType(typ, title=typ, actions=self.view_actions), )

    def getTypeInfo(self, contentType):
        typ = 'Dummy Content'
        return DummyType(typ, title=typ, actions=self.view_actions)

    # WorkflowTool
    test_notified = None

    def notifyCreated(self, ob):
        self.test_notified = ob

class DummyCachingManager:

    def getHTTPCachingHeaders( self, content, view_name, keywords, time=None ):
         return (
             ('foo', 'Foo'), ('bar', 'Bar'),
             ('test_path', '/'.join(content.getPhysicalPath())),
             )

    def getModTimeAndETag(self, content, view_method, keywords, time=None ):
         return (None, None, False)

    def getPhysicalPath(self):
        return ('baz',)


FAKE_ETAG = None # '--FAKE ETAG--'

class DummyCachingManagerWithPolicy(DummyCachingManager):

    # dummy fixture implementing a single policy:
    #  - always set the last-modified date if available
    #  - calculate the date using the modified method on content

    def getHTTPCachingHeaders( self, content, view_name, keywords, time=None ):

         # if the object has a modified method, add it as last-modified
         if hasattr(content, 'modified'):
             headers = ( ('Last-modified', rfc1123_date(content.modified()) ), )
         return headers

    def getModTimeAndETag(self, content, view_method, keywords, time=None ):
         modified_date = None
         if hasattr(content, 'modified'):
            modified_date = content.modified()
         set_last_modified = (modified_date is not None)
         return (modified_date, FAKE_ETAG, set_last_modified)


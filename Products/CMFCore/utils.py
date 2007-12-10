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
""" Utility functions.

$Id: utils.py 41229 2006-01-08 17:33:39Z yuppie $
"""

from os import path as os_path
from os.path import abspath
import re
from warnings import warn
from copy import deepcopy

from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from AccessControl import ModuleSecurityInfo
from AccessControl.Permission import Permission
from AccessControl.PermissionRole import rolesForPermissionOn
from AccessControl.Role import gather_permissions
from Acquisition import aq_base
from Acquisition import aq_get
from Acquisition import aq_inner
from Acquisition import aq_parent
from Acquisition import Implicit
from DateTime import DateTime
from ExtensionClass import Base
from Globals import HTMLFile
from Globals import ImageFile
from Globals import InitializeClass
from Globals import MessageDialog
from Globals import package_home
from Globals import UNIQUE
from OFS.misc_ import misc_ as misc_images
from OFS.misc_ import Misc_ as MiscImage
from OFS.PropertyManager import PropertyManager
from OFS.PropertySheets import PropertySheets
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.Expressions import getEngine
from Products.PageTemplates.Expressions import SecureModuleImporter
from StructuredText.StructuredText import HTML
from thread import allocate_lock

from exceptions import AccessControl_Unauthorized
from exceptions import NotFound

security = ModuleSecurityInfo( 'Products.CMFCore.utils' )

_dtmldir = os_path.join( package_home( globals() ), 'dtml' )
_wwwdir = os_path.join( package_home( globals() ), 'www' )

#
#   Simple utility functions, callable from restricted code.
#
_marker = []  # Create a new marker object.

security.declarePublic('getToolByName')
def getToolByName(obj, name, default=_marker):

    """ Get the tool, 'toolname', by acquiring it.

    o Application code should use this method, rather than simply
      acquiring the tool by name, to ease forward migration (e.g.,
      to Zope3).
    """
    try:
        tool = aq_get(obj, name, default, 1)
    except AttributeError:
        if default is _marker:
            raise
        return default
    else:
        if tool is _marker:
            raise AttributeError, name
        return tool

security.declarePublic('cookString')
def cookString(text):

    """ Make a Zope-friendly ID from 'text'.

    o Remove any spaces

    o Lowercase the ID.
    """
    rgx = re.compile(r'(^_|[^a-zA-Z0-9-_~\,\.])')
    cooked = re.sub(rgx, "",text).lower()
    return cooked

security.declarePublic('tuplize')
def tuplize( valueName, value ):

    """ Make a tuple from 'value'.

    o Use 'valueName' to generate appropriate error messages.
    """
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple( value )
    if isinstance(value, basestring):
        return tuple( value.split() )
    raise ValueError, "%s of unsupported type" % valueName

#
#   Security utilities, callable only from unrestricted code.
#
security.declarePrivate('_getAuthenticatedUser')
def _getAuthenticatedUser( self ):
    return getSecurityManager().getUser()

security.declarePrivate('_checkPermission')
def _checkPermission(permission, obj):
    """ Check if the current user has the permission on the given object.
    """
    # this code is ported from Zope 2.8's ZopeSecurityPolicy.checkPermission
    roles = rolesForPermissionOn(permission, obj)
    if isinstance(roles, basestring):
        roles = [roles]
    context = getSecurityManager()._context

    # check executable owner and proxy roles
    stack = context.stack
    if stack:
        eo = stack[-1]
        owner = eo.getOwner()
        if owner is not None:
            if not owner.allowed(obj, roles):
                return 0
            proxy_roles = getattr(eo, '_proxy_roles', None)
            if proxy_roles:
                owner = eo.getWrappedOwner()
                if owner is not None:
                    if obj is not aq_base(obj):
                        if not owner._check_context(obj):
                            return 0
                for r in proxy_roles:
                    if r in roles:
                        return 1
                return 0

    return context.user.allowed(obj, roles)

security.declarePrivate('_verifyActionPermissions')
def _verifyActionPermissions(obj, action):
    # _verifyActionPermissions is deprecated and will be removed in CMF 2.0.
    # This was only used by the deprecated _getViewFor function.
    pp = action.getPermissions()
    if not pp:
        return 1
    for p in pp:
        if _checkPermission(p, obj):
            return 1
    return 0

security.declarePublic( 'getActionContext' )
def getActionContext( self ):
    # getActionContext is deprecated and will be removed as soon as the
    # backwards compatibility code in TypeInformation._guessMethodAliases is
    # removed.
    data = { 'object_url'   : ''
           , 'folder_url'   : ''
           , 'portal_url'   : ''
           , 'object'       : None
           , 'folder'       : None
           , 'portal'       : None
           , 'nothing'      : None
           , 'request'      : getattr( self, 'REQUEST', None )
           , 'modules'      : SecureModuleImporter
           , 'member'       : None
           }
    return getEngine().getContext( data )

security.declarePrivate('_getViewFor')
def _getViewFor(obj, view='view'):
    warn('__call__() and view() methods using _getViewFor() as well as '
         '_getViewFor() itself are deprecated and will be removed in CMF 2.0. '
         'Bypass these methods by defining \'(Default)\' and \'view\' Method '
         'Aliases.',
         DeprecationWarning)
    ti = obj.getTypeInfo()

    if ti is not None:

        context = getActionContext( obj )
        actions = ti.listActions()

        for action in actions:
            if action.getId() == view:
                if _verifyActionPermissions( obj, action ):
                    target = action.action(context).strip()
                    if target.startswith('/'):
                        target = target[1:]
                    __traceback_info__ = ( ti.getId(), target )
                    return obj.restrictedTraverse( target )

        # "view" action is not present or not allowed.
        # Find something that's allowed.
        for action in actions:
            if _verifyActionPermissions(obj, action):
                target = action.action(context).strip()
                if target.startswith('/'):
                    target = target[1:]
                __traceback_info__ = ( ti.getId(), target )
                return obj.restrictedTraverse( target )

        raise AccessControl_Unauthorized( 'No accessible views available for '
                                    '%s' % '/'.join( obj.getPhysicalPath() ) )
    else:
        raise NotFound('Cannot find default view for "%s"' %
                            '/'.join(obj.getPhysicalPath()))


# If Zope ever provides a call to getRolesInContext() through
# the SecurityManager API, the method below needs to be updated.
security.declarePrivate('_limitGrantedRoles')
def _limitGrantedRoles(roles, context, special_roles=()):
    # Only allow a user to grant roles already possessed by that user,
    # with the exception that all special_roles can also be granted.
    user = _getAuthenticatedUser(context)
    if user is None:
        user_roles = ()
    else:
        user_roles = user.getRolesInContext(context)
    if 'Manager' in user_roles:
        # Assume all other roles are allowed.
        return
    for role in roles:
        if role not in special_roles and role not in user_roles:
            raise AccessControl_Unauthorized('Too many roles specified.')

limitGrantedRoles = _limitGrantedRoles  # XXX: Deprecated spelling

security.declarePrivate('_mergedLocalRoles')
def _mergedLocalRoles(object):
    """Returns a merging of object and its ancestors'
    __ac_local_roles__."""
    # Modified from AccessControl.User.getRolesInContext().
    merged = {}
    object = getattr(object, 'aq_inner', object)
    while 1:
        if hasattr(object, '__ac_local_roles__'):
            dict = object.__ac_local_roles__ or {}
            if callable(dict): dict = dict()
            for k, v in dict.items():
                if merged.has_key(k):
                    merged[k] = merged[k] + v
                else:
                    merged[k] = v
        if hasattr(object, 'aq_parent'):
            object=object.aq_parent
            object=getattr(object, 'aq_inner', object)
            continue
        if hasattr(object, 'im_self'):
            object=object.im_self
            object=getattr(object, 'aq_inner', object)
            continue
        break

    return deepcopy(merged)

mergedLocalRoles = _mergedLocalRoles    # XXX: Deprecated spelling

security.declarePrivate('_ac_inherited_permissions')
def _ac_inherited_permissions(ob, all=0):
    # Get all permissions not defined in ourself that are inherited
    # This will be a sequence of tuples with a name as the first item and
    # an empty tuple as the second.
    d = {}
    perms = getattr(ob, '__ac_permissions__', ())
    for p in perms: d[p[0]] = None
    r = gather_permissions(ob.__class__, [], d)
    if all:
       if hasattr(ob, '_subobject_permissions'):
           for p in ob._subobject_permissions():
               pname=p[0]
               if not d.has_key(pname):
                   d[pname]=1
                   r.append(p)
       r = list(perms) + r
    return r

security.declarePrivate('_modifyPermissionMappings')
def _modifyPermissionMappings(ob, map):
    """
    Modifies multiple role to permission mappings.
    """
    # This mimics what AccessControl/Role.py does.
    # Needless to say, it's crude. :-(
    something_changed = 0
    perm_info = _ac_inherited_permissions(ob, 1)
    for name, settings in map.items():
        cur_roles = rolesForPermissionOn(name, ob)
        if isinstance(cur_roles, basestring):
            cur_roles = [cur_roles]
        else:
            cur_roles = list(cur_roles)
        changed = 0
        for (role, allow) in settings.items():
            if not allow:
                if role in cur_roles:
                    changed = 1
                    cur_roles.remove(role)
            else:
                if role not in cur_roles:
                    changed = 1
                    cur_roles.append(role)
        if changed:
            data = ()  # The list of methods using this permission.
            for perm in perm_info:
                n, d = perm[:2]
                if n == name:
                    data = d
                    break
            p = Permission(name, data, ob)
            p.setRoles(tuple(cur_roles))
            something_changed = 1
    return something_changed


# Parse a string of etags from an If-None-Match header
# Code follows ZPublisher.HTTPRequest.parse_cookie
parse_etags_lock=allocate_lock()
def parse_etags( text
               , result=None
                # quoted etags (assumed separated by whitespace + a comma)
               , etagre_quote = re.compile('(\s*\"([^\"]*)\"\s*,{0,1})')
                # non-quoted etags (assumed separated by whitespace + a comma)
               , etagre_noquote = re.compile('(\s*([^,]*)\s*,{0,1})')
               , acquire=parse_etags_lock.acquire
               , release=parse_etags_lock.release
               ):

    if result is None: result=[]
    if not len(text):
        return result

    acquire()
    try:
        m = etagre_quote.match(text)
        if m:
            # Match quoted etag (spec-observing client)
            l     = len(m.group(1))
            value = m.group(2)
        else:
            # Match non-quoted etag (lazy client)
            m = etagre_noquote.match(text)
            if m:
                l     = len(m.group(1))
                value = m.group(2)
            else:
                return result
    finally: release()

    if value:
        result.append(value)
    return apply(parse_etags,(text[l:],result))


def _checkConditionalGET(obj, extra_context):
    """A conditional GET is done using one or both of the request
       headers:

       If-Modified-Since: Date
       If-None-Match: list ETags (comma delimited, sometimes quoted)

       If both conditions are present, both must be satisfied.
       
       This method checks the caching policy manager to see if
       a content object's Last-modified date and ETag satisfy
       the conditional GET headers.

       Returns the tuple (last_modified, etag) if the conditional
       GET requirements are met and None if not.

       It is possible for one of the tuple elements to be None.
       For example, if there is no If-None-Match header and
       the caching policy does not specify an ETag, we will
       just return (last_modified, None).
       """

    REQUEST = getattr(obj, 'REQUEST', None)
    if REQUEST is None:
        return False

    if_modified_since = REQUEST.get_header('If-Modified-Since', None)
    if_none_match = REQUEST.get_header('If-None-Match', None)

    if if_modified_since is None and if_none_match is None:
        # not a conditional GET
        return False

    manager = getToolByName(obj, 'caching_policy_manager', None)
    if manager is None:
        return False

    ret = manager.getModTimeAndETag(aq_parent(obj), obj.getId(), extra_context)
    if ret is None:
        # no appropriate policy or 304s not enabled
        return  False 

    (content_mod_time, content_etag, set_last_modified_header) = ret
    if content_mod_time:
        mod_time_secs = long(content_mod_time.timeTime())
    else:
        mod_time_secs = None
    
    if if_modified_since:
        # from CMFCore/FSFile.py:
        if_modified_since = if_modified_since.split(';')[0]
        # Some proxies seem to send invalid date strings for this
        # header. If the date string is not valid, we ignore it
        # rather than raise an error to be generally consistent
        # with common servers such as Apache (which can usually
        # understand the screwy date string as a lucky side effect
        # of the way they parse it).
        try:
            if_modified_since=long(DateTime(if_modified_since).timeTime())
        except:
            if_mod_since=None
                
    client_etags = None
    if if_none_match:
        client_etags = parse_etags(if_none_match)

    if not if_modified_since and not client_etags:
        # not a conditional GET, or headers are messed up
        return False

    if if_modified_since:
        if ( not content_mod_time or 
             mod_time_secs < 0 or 
             mod_time_secs > if_modified_since ):
            return False
        
    if client_etags:
        if ( not content_etag or 
             (content_etag not in client_etags and '*' not in client_etags) ):
            return False
    else:
        # If we generate an ETag, don't validate the conditional GET unless 
        # the client supplies an ETag
        # This may be more conservative than the spec requires, but we are 
        # already _way_ more conservative.
        if content_etag:
            return False

    response = REQUEST.RESPONSE
    if content_mod_time and set_last_modified_header:
        response.setHeader('Last-modified', str(content_mod_time))
    if content_etag:
        response.setHeader('ETag', content_etag, literal=1)
    response.setStatus(304)
            
    return True
    

security.declarePrivate('_setCacheHeaders')
def _setCacheHeaders(obj, extra_context):
    """Set cache headers according to cache policy manager for the obj."""
    REQUEST = getattr(obj, 'REQUEST', None)

    if REQUEST is not None:
        content = aq_parent(obj)
        manager = getToolByName(obj, 'caching_policy_manager', None)
        if manager is not None:
            view_name = obj.getId()
            headers = manager.getHTTPCachingHeaders(
                              content, view_name, extra_context
                              )
            RESPONSE = REQUEST['RESPONSE']
            for key, value in headers:
                if key == 'ETag':
                    RESPONSE.setHeader(key, value, literal=1)
                else:
                    RESPONSE.setHeader(key, value)
            if headers:
                RESPONSE.setHeader('X-Cache-Headers-Set-By',
                                   'CachingPolicyManager: %s' %
                                   '/'.join(manager.getPhysicalPath()))

class _ViewEmulator(Implicit):
    """Auxiliary class used to adapt FSFile and FSImage
    for caching_policy_manager
    """
    def __init__(self, view_name=''):
        self._view_name = view_name

    def getId(self):
        return self._view_name


#
#   Base classes for tools
#
class ImmutableId(Base):

    """ Base class for objects which cannot be renamed.
    """
    def _setId(self, id):

        """ Never allow renaming!
        """
        if id != self.getId():
            raise MessageDialog(
                title='Invalid Id',
                message='Cannot change the id of this object',
                action ='./manage_main',)

class UniqueObject (ImmutableId):

    """ Base class for objects which cannot be "overridden" / shadowed.
    """
    __replaceable__ = UNIQUE


class SimpleItemWithProperties (PropertyManager, SimpleItem):
    """
    A common base class for objects with configurable
    properties in a fixed schema.
    """
    manage_options = (
        PropertyManager.manage_options
        + SimpleItem.manage_options)


    security = ClassSecurityInfo()
    security.declarePrivate('manage_addProperty')
    security.declarePrivate('manage_delProperties')
    security.declarePrivate('manage_changePropertyTypes')

    def manage_propertiesForm(self, REQUEST, *args, **kw):
        """ An override that makes the schema fixed.
        """
        my_kw = kw.copy()
        my_kw['property_extensible_schema__'] = 0
        form = PropertyManager.manage_propertiesForm.__of__(self)
        return form(self, REQUEST, *args, **my_kw)

InitializeClass( SimpleItemWithProperties )


#
#   "Omnibus" factory framework for tools.
#
class ToolInit:

    """ Utility class for generating the factories for several tools.
    """
    __name__ = 'toolinit'

    security = ClassSecurityInfo()
    security.declareObjectPrivate()     # equivalent of __roles__ = ()

    def __init__(self, meta_type, tools, product_name=None, icon=None):
        self.meta_type = meta_type
        self.tools = tools
        if product_name is not None:
            warn("The product_name parameter of ToolInit is deprecated and "
                 "will be ignored in CMF 2.0: %s" % product_name,
                 DeprecationWarning, stacklevel=2)
        self.product_name = product_name
        self.icon = icon

    def initialize(self, context):
        # Add only one meta type to the folder add list.
        if self.product_name is None:
            productObject = context._ProductContext__prod
            self.product_name = productObject.id
        context.registerClass(
            meta_type = self.meta_type,
            # This is a little sneaky: we add self to the
            # FactoryDispatcher under the name "toolinit".
            # manage_addTool() can then grab it.
            constructors = (manage_addToolForm,
                            manage_addTool,
                            self,),
            icon = self.icon
            )

        if self.icon:
            icon = os_path.split(self.icon)[1]
        else:
            icon = None
        for tool in self.tools:
            tool.__factory_meta_type__ = self.meta_type
            tool.icon = 'misc_/%s/%s' % (self.product_name, icon)

InitializeClass( ToolInit )

addInstanceForm = HTMLFile('dtml/addInstance', globals())

def manage_addToolForm(self, REQUEST):

    """ Show the add tool form.
    """
    # self is a FactoryDispatcher.
    toolinit = self.toolinit
    tl = []
    for tool in toolinit.tools:
        tl.append(tool.meta_type)
    return addInstanceForm(addInstanceForm, self, REQUEST,
                           factory_action='manage_addTool',
                           factory_meta_type=toolinit.meta_type,
                           factory_product_name=toolinit.product_name,
                           factory_icon=toolinit.icon,
                           factory_types_list=tl,
                           factory_need_id=0)

def manage_addTool(self, type, REQUEST=None):

    """ Add the tool specified by name.
    """
    # self is a FactoryDispatcher.
    toolinit = self.toolinit
    obj = None
    for tool in toolinit.tools:
        if tool.meta_type == type:
            obj = tool()
            break
    if obj is None:
        raise NotFound(type)
    self._setObject(obj.getId(), obj)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST)


#
#   Now, do the same for creating content factories.
#
class ContentInit:

    """ Utility class for generating factories for several content types.
    """
    __name__ = 'contentinit'

    security = ClassSecurityInfo()
    security.declareObjectPrivate()

    def __init__( self
                , meta_type
                , content_types
                , permission=None
                , extra_constructors=()
                , fti=()
                ):
        self.meta_type = meta_type
        self.content_types = content_types
        self.permission = permission
        self.extra_constructors = extra_constructors
        self.fti = fti

    def initialize(self, context):
        # Add only one meta type to the folder add list.
        context.registerClass(
            meta_type = self.meta_type
            # This is a little sneaky: we add self to the
            # FactoryDispatcher under the name "contentinit".
            # manage_addContentType() can then grab it.
            , constructors = ( manage_addContentForm
                               , manage_addContent
                               , self
                               , ('factory_type_information', self.fti)
                               ) + self.extra_constructors
            , permission = self.permission
            )

        for ct in self.content_types:
            ct.__factory_meta_type__ = self.meta_type

InitializeClass( ContentInit )

def manage_addContentForm(self, REQUEST):

    """ Show the add content type form.
    """
    # self is a FactoryDispatcher.
    ci = self.contentinit
    tl = []
    for t in ci.content_types:
        tl.append(t.meta_type)
    return addInstanceForm(addInstanceForm, self, REQUEST,
                           factory_action='manage_addContent',
                           factory_meta_type=ci.meta_type,
                           factory_icon=None,
                           factory_types_list=tl,
                           factory_need_id=1)

def manage_addContent( self, id, type, REQUEST=None ):

    """ Add the content type specified by name.
    """
    # self is a FactoryDispatcher.
    contentinit = self.contentinit
    obj = None
    for content_type in contentinit.content_types:
        if content_type.meta_type == type:
            obj = content_type( id )
            break
    if obj is None:
        raise NotFound(type)
    self._setObject( id, obj )
    if REQUEST is not None:
        return self.manage_main(self, REQUEST)


def initializeBasesPhase1(base_classes, module):

    """ Execute the first part of initialization of ZClass base classes.

    Stuffs a _ZClass_for_x class in the module for each base.
    """
    rval = []
    for base_class in base_classes:
        d={}
        zclass_name = '_ZClass_for_%s' % base_class.__name__
        exec 'class %s: pass' % zclass_name in d
        Z = d[ zclass_name ]
        Z.propertysheets = PropertySheets()
        Z._zclass_ = base_class
        Z.manage_options = ()
        Z.__module__ = module.__name__
        setattr( module, zclass_name, Z )
        rval.append(Z)
    return rval

def initializeBasesPhase2(zclasses, context):

    """ Finishes ZClass base initialization.

    o 'zclasses' is the list returned by initializeBasesPhase1().

    o 'context' is a ProductContext object.
    """
    for zclass in zclasses:
        context.registerZClass(zclass)

def registerIcon(klass, iconspec, _prefix=None):

    """ Make an icon available for a given class.

    o 'klass' is the class being decorated.

    o 'iconspec' is the path within the product where the icon lives.
    """
    modname = klass.__module__
    pid = modname.split('.')[1]
    name = os_path.split(iconspec)[1]
    klass.icon = 'misc_/%s/%s' % (pid, name)
    icon = ImageFile(iconspec, _prefix)
    icon.__roles__=None
    if not hasattr(misc_images, pid):
        setattr(misc_images, pid, MiscImage(pid, {}))
    getattr(misc_images, pid)[name]=icon

security.declarePublic('format_stx')
def format_stx( text, level=1 ):
    """ Render STX to HTML.
    """
    warn('format_stx() will be removed in CMF 2.0. Please use '
         'StructuredText.StructuredText.HTML instead.',
         DeprecationWarning, stacklevel=2)
    return HTML(text, level=level, header=0)

#
#   Metadata Keyword splitter utilities
#
KEYSPLITRE = re.compile(r'[,;]')

security.declarePublic('keywordsplitter')
def keywordsplitter( headers
                   , names=('Subject', 'Keywords',)
                   , splitter=KEYSPLITRE.split
                   ):
    """ Split keywords out of headers, keyed on names.  Returns list.
    """
    out = []
    for head in names:
        keylist = splitter(headers.get(head, ''))
        keylist = map(lambda x: x.strip(), keylist)
        out.extend( [key for key in keylist if key] )
    return out

#
#   Metadata Contributors splitter utilities
#
CONTRIBSPLITRE = re.compile(r';')

security.declarePublic('contributorsplitter')
def contributorsplitter( headers
                       , names=('Contributors',)
                       , splitter=CONTRIBSPLITRE.split
                       ):
    """ Split contributors out of headers, keyed on names.  Returns list.
    """
    return keywordsplitter( headers, names, splitter )

#
#   Directory-handling utilities
#
security.declarePublic('normalize')
def normalize(p):
    # the first .replace is needed to help normpath when dealing with Windows
    # paths under *nix, the second to normalize to '/'
    return os_path.normpath(p.replace('\\','/')).replace('\\','/')

import Products
ProductsPath = [ abspath(ppath) for ppath in Products.__path__ ]

security.declarePublic('expandpath')
def expandpath(p):
    """ Convert minimal filepath to (expanded) filepath.

    The (expanded) filepath is the valid absolute path on the current platform
    and setup.
    """
    p = os_path.normpath(p)
    if os_path.isabs(p):
        return p

    for ppath in ProductsPath:
        abs = os_path.join(ppath, p)
        if os_path.exists(abs):
            return abs

    # return the last one, errors will happen else where as as result
    # and be caught
    return abs

security.declarePublic('minimalpath')
def minimalpath(p):
    """ Convert (expanded) filepath to minimal filepath.

    The minimal filepath is the cross-platform / cross-setup path stored in
    persistent objects and used as key in the directory registry.

    Returns a slash-separated path relative to the Products path. If it can't
    be found, a normalized path is returned.
    """
    p = abspath(p)
    for ppath in ProductsPath:
        if p.startswith(ppath):
            p = p[len(ppath)+1:]
            break
    return p.replace('\\','/')


class SimpleRecord:
    """ record-like class """

    def __init__(self, **kw):
        self.__dict__.update(kw)


# BBB: for Zope 2.7
class BBBTransaction:

    def begin(self):
        get_transaction().begin()

    def commit(self, sub=False):
        get_transaction().commit(sub)

    def abort(self, sub=False):
        get_transaction().abort(sub)

    def get(self):
        return get_transaction()

transaction = BBBTransaction()

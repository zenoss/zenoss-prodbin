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
""" Type registration tool.

$Id: TypesTool.py 40161 2005-11-16 17:13:16Z efge $
"""

from sys import exc_info
from warnings import warn

from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from Acquisition import aq_base
from Acquisition import aq_get
from Globals import DTMLFile
from Globals import InitializeClass
from OFS.Folder import Folder
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from zLOG import LOG, ERROR
import Products

from ActionProviderBase import ActionProviderBase
from exceptions import AccessControl_Unauthorized
from exceptions import BadRequest
from exceptions import zExceptions_Unauthorized
from interfaces.portal_types import ContentTypeInformation as ITypeInformation
from interfaces.portal_types import portal_types as ITypesTool
from permissions import AccessContentsInformation
from permissions import ManagePortal
from permissions import View
from utils import _checkPermission
from utils import _dtmldir
from utils import _wwwdir
from utils import cookString
from utils import getActionContext
from utils import SimpleItemWithProperties
from utils import UniqueObject


_marker = []  # Create a new marker.


class TypeInformation(SimpleItemWithProperties, ActionProviderBase):
    """
    Base class for information about a content type.
    """

    _isTypeInformation = 1

    manage_options = ( SimpleItemWithProperties.manage_options[:1]
                     + ( {'label':'Aliases',
                          'action':'manage_aliases'}, )
                     + ActionProviderBase.manage_options
                     + SimpleItemWithProperties.manage_options[1:]
                     )

    security = ClassSecurityInfo()

    security.declareProtected(ManagePortal, 'manage_editProperties')
    security.declareProtected(ManagePortal, 'manage_changeProperties')
    security.declareProtected(ManagePortal, 'manage_propertiesForm')

    _basic_properties = (
        {'id':'title', 'type': 'string', 'mode':'w',
         'label':'Title'},
        {'id':'description', 'type': 'text', 'mode':'w',
         'label':'Description'},
        {'id':'content_icon', 'type': 'string', 'mode':'w',
         'label':'Icon'},
        {'id':'content_meta_type', 'type': 'string', 'mode':'w',
         'label':'Product meta type'},
        )

    _advanced_properties = (
        {'id':'immediate_view', 'type': 'string', 'mode':'w',
         'label':'Initial view name'},
        {'id':'global_allow', 'type': 'boolean', 'mode':'w',
         'label':'Implicitly addable?'},
        {'id':'filter_content_types', 'type': 'boolean', 'mode':'w',
         'label':'Filter content types?'},
        {'id':'allowed_content_types'
         , 'type': 'multiple selection'
         , 'mode':'w'
         , 'label':'Allowed content types'
         , 'select_variable':'listContentTypes'
         },
        { 'id': 'allow_discussion', 'type': 'boolean', 'mode': 'w'
          , 'label': 'Allow Discussion?'
          },
        )

    title = ''
    description = ''
    content_meta_type = ''
    content_icon = ''
    immediate_view = ''
    filter_content_types = True
    allowed_content_types = ()
    allow_discussion = False
    global_allow = True

    def __init__(self, id, **kw):

        self.id = id

        if not kw:
            return

        kw = kw.copy()  # Get a modifiable dict.

        if (not kw.has_key('content_meta_type')
            and kw.has_key('meta_type')):
            kw['content_meta_type'] = kw['meta_type']

        if (not kw.has_key('content_icon')
            and kw.has_key('icon')):
            kw['content_icon'] = kw['icon']

        self.manage_changeProperties(**kw)

        actions = kw.get( 'actions', () )
        # make sure we have a copy
        _actions = []
        for action in actions:
            _actions.append( action.copy() )
        actions = tuple(_actions)
        # We don't know if actions need conversion, so we always add oldstyle
        # _actions and convert them.
        self._actions = actions
        self._convertActions()

        aliases = kw.get( 'aliases', _marker )
        if aliases is _marker:
            self._guessMethodAliases()
        else:
            self.setMethodAliases(aliases)

    #
    #   ZMI methods
    #
    security.declareProtected(ManagePortal, 'manage_aliases')
    manage_aliases = PageTemplateFile( 'typeinfoAliases.zpt', _wwwdir )

    security.declareProtected(ManagePortal, 'manage_setMethodAliases')
    def manage_setMethodAliases(self, REQUEST):
        """ Config method aliases.
        """
        form = REQUEST.form
        aliases = {}
        for k, v in form['aliases'].items():
            v = v.strip()
            if v:
                aliases[k] = v

        _dict = {}
        for k, v in form['methods'].items():
            if aliases.has_key(k):
                _dict[ aliases[k] ] = v
        self.setMethodAliases(_dict)
        REQUEST.RESPONSE.redirect('%s/manage_aliases' % self.absolute_url())

    #
    #   Accessors
    #
    security.declareProtected(View, 'Type')
    def Type(self):
        """ Deprecated. Use Title(). """
        warn('TypeInformation.Type() is deprecated, use Title().',
             DeprecationWarning)
        return self.Title()

    security.declareProtected(View, 'Title')
    def Title(self):
        """
            Return the "human readable" type name (note that it
            may not map exactly to the 'portal_type', e.g., for
            l10n/i18n or where a single content class is being
            used twice, under different names.
        """
        return self.title or self.getId()

    security.declareProtected(View, 'Description')
    def Description(self):
        """
            Textual description of the class of objects (intended
            for display in a "constructor list").
        """
        return self.description

    security.declareProtected(View, 'Metatype')
    def Metatype(self):
        """
            Returns the Zope 'meta_type' for this content object.
            May be used for building the list of portal content
            meta types.
        """
        return self.content_meta_type

    security.declareProtected(View, 'getIcon')
    def getIcon(self):
        """
            Returns the icon for this content object.
        """
        return self.content_icon

    security.declarePublic('allowType')
    def allowType( self, contentType ):
        """
            Can objects of 'contentType' be added to containers whose
            type object we are?
        """
        if not self.filter_content_types:
            ti = self.getTypeInfo( contentType )
            if ti is None or ti.globalAllow():
                return 1

        #If a type is enabled to filter and no content_types are allowed
        if not self.allowed_content_types:
            return 0

        if contentType in self.allowed_content_types:
            return 1

        return 0

    security.declarePublic('getId')
    def getId(self):
        return self.id

    security.declarePublic('allowDiscussion')
    def allowDiscussion( self ):
        """
            Can this type of object support discussion?
        """
        return self.allow_discussion

    security.declarePublic('globalAllow')
    def globalAllow(self):
        """
        Should this type be implicitly addable anywhere?
        """
        return self.global_allow

    security.declarePublic('listActions')
    def listActions(self, info=None, object=None):
        """ Return a sequence of the action info objects for this type.
        """
        if self._actions and isinstance(self._actions[0], dict):
            self._convertActions()

        return self._actions or ()

    security.declarePublic('getActionById')
    def getActionById( self, id, default=_marker ):
        """ Get method ID by action ID.
        """
        warn('getActionById() is deprecated and will be removed in CMF 2.0. '
             'Please use getActionInfo()[\'url\'] if you need an URL or '
             'queryMethodID() if you need a method ID.',
             DeprecationWarning)
        context = getActionContext( self )
        for action in self.listActions():

            __traceback_info__ = (self.getId(), action)

            if action.getId() == id:
                target = action.action(context).strip()
                if target.startswith('/'):
                    target = target[1:]
                return target
            else:
                # Temporary backward compatibility.
                if action.Title().lower() == id:
                    target = action.action(context).strip()
                    if target.startswith('/'):
                        target = target[1:]
                    return target

        if default is _marker:
            raise ValueError, ('No action "%s" for type "%s"'
                               % (id, self.getId()))
        else:
            return default

    security.declarePrivate( '_convertActions' )
    def _convertActions( self ):
        """ Upgrade dictionary-based actions.
        """
        aa, self._actions = self._actions, ()

        for action in aa:

            # Some backward compatibility stuff.
            if not 'id' in action:
                action['id'] = cookString(action['name'])

            if not 'title' in action:
                action['title'] = action.get('name', action['id'].capitalize())

            # historically, action['action'] is simple string
            actiontext = action.get('action').strip() or 'string:${object_url}'
            if actiontext[:7] not in ('python:', 'string:'):
                actiontext = 'string:${object_url}/%s' % actiontext

            self.addAction(
                  id=action['id']
                , name=action['title']
                , action=actiontext
                , condition=action.get('condition')
                , permission=action.get( 'permissions', () )
                , category=action.get('category', 'object')
                , visible=action.get('visible', True)
                )

    security.declarePublic('constructInstance')
    def constructInstance(self, container, id, *args, **kw):
        """Build an instance of the type.

        Builds the instance in 'container', using 'id' as its id.
        Returns the object.
        """
        if not self.isConstructionAllowed(container):
            raise AccessControl_Unauthorized('Cannot create %s' % self.getId())

        ob = self._constructInstance(container, id, *args, **kw)

        return self._finishConstruction(ob)

    security.declarePrivate('_finishConstruction')
    def _finishConstruction(self, ob):
        """
            Finish the construction of a content object.
            Set its portal_type, insert it into the workflows.
        """
        if hasattr(ob, '_setPortalTypeName'):
            ob._setPortalTypeName(self.getId())

        if hasattr(aq_base(ob), 'notifyWorkflowCreated'):
            ob.notifyWorkflowCreated()

        ob.reindexObject()
        return ob

    security.declareProtected(ManagePortal, 'getMethodAliases')
    def getMethodAliases(self):
        """ Get method aliases dict.
        """
        if not hasattr(self, '_aliases'):
            self._guessMethodAliases()
        aliases = self._aliases
        # for aliases created with CMF 1.5.0beta
        for key, method_id in aliases.items():
            if isinstance(method_id, tuple):
                aliases[key] = method_id[0]
                self._p_changed = True
        return aliases.copy()

    security.declareProtected(ManagePortal, 'setMethodAliases')
    def setMethodAliases(self, aliases):
        """ Set method aliases dict.
        """
        _dict = {}
        for k, v in aliases.items():
            v = v.strip()
            if v:
                _dict[ k.strip() ] = v
        if not getattr(self, '_aliases', None) == _dict:
            self._aliases = _dict
            return True
        else:
            return False

    security.declarePublic('queryMethodID')
    def queryMethodID(self, alias, default=None, context=None):
        """ Query method ID by alias.
        """
        if not hasattr(self, '_aliases'):
            self._guessMethodAliases()
        aliases = self._aliases
        method_id = aliases.get(alias, default)
        # for aliases created with CMF 1.5.0beta
        if isinstance(method_id, tuple):
            method_id = method_id[0]
        return method_id

    security.declarePrivate('_guessMethodAliases')
    def _guessMethodAliases(self):
        """ Guess and set Method Aliases. Used for upgrading old TIs.
        """
        context = getActionContext(self)
        actions = self.listActions()
        ordered = []
        _dict = {}
        viewmethod = ''

        # order actions and search 'mkdir' action
        for action in actions:
            if action.getId() == 'view':
                ordered.insert(0, action)
            elif action.getId() == 'mkdir':
                try:
                    mkdirmethod = action.action(context).strip()
                except AttributeError:
                    continue
                if mkdirmethod.startswith('/'):
                    mkdirmethod = mkdirmethod[1:]
                _dict['mkdir'] = mkdirmethod
            else:
                ordered.append(action)

        # search 'view' action
        for action in ordered:
            perms = action.getPermissions()
            if not perms or View in perms:
                try:
                    viewmethod = action.action(context).strip()
                except (AttributeError, TypeError):
                    break
                if viewmethod.startswith('/'):
                    viewmethod = viewmethod[1:]
                if not viewmethod:
                    viewmethod = '(Default)'
                break
        else:
            viewmethod = '(Default)'
        if viewmethod:
            _dict['view'] = viewmethod

        # search default action
        for action in ordered:
            try:
                defmethod = action.action(context).strip()
            except (AttributeError, TypeError):
                break
            if defmethod.startswith('/'):
                defmethod = defmethod[1:]
            if not defmethod:
                break
        else:
            if viewmethod:
                _dict['(Default)'] = viewmethod

        # correct guessed values if we know better
        if self.content_meta_type in ('Portal File', 'Portal Folder',
                                      'Portal Image'):
            _dict['(Default)'] = 'index_html'
            if viewmethod == '(Default)':
                _dict['view'] = 'index_html'
        if self.content_meta_type in ('Document', 'News Item'):
            _dict['gethtml'] = 'source_html'

        self.setMethodAliases(_dict)
        return 1

InitializeClass( TypeInformation )


class FactoryTypeInformation(TypeInformation):
    """
    Portal content factory.
    """

    __implements__ = ITypeInformation

    meta_type = 'Factory-based Type Information'
    security = ClassSecurityInfo()

    _properties = (TypeInformation._basic_properties + (
        {'id':'product', 'type': 'string', 'mode':'w',
         'label':'Product name'},
        {'id':'factory', 'type': 'string', 'mode':'w',
         'label':'Product factory method'},
        ) + TypeInformation._advanced_properties)

    product = ''
    factory = ''

    #
    #   Agent methods
    #
    def _getFactoryMethod(self, container, check_security=1):
        if not self.product or not self.factory:
            raise ValueError, ('Product factory for %s was undefined' %
                               self.getId())
        p = container.manage_addProduct[self.product]
        m = getattr(p, self.factory, None)
        if m is None:
            raise ValueError, ('Product factory for %s was invalid' %
                               self.getId())
        if not check_security:
            return m
        if getSecurityManager().validate(p, p, self.factory, m):
            return m
        raise AccessControl_Unauthorized( 'Cannot create %s' % self.getId() )

    def _queryFactoryMethod(self, container, default=None):

        if not self.product or not self.factory or container is None:
            return default

        # In case we aren't wrapped.
        dispatcher = getattr(container, 'manage_addProduct', None)

        if dispatcher is None:
            return default

        try:
            p = dispatcher[self.product]
        except AttributeError:
            LOG('Types Tool', ERROR, '_queryFactoryMethod raised an exception',
                error=exc_info())
            return default

        m = getattr(p, self.factory, None)

        if m:
            try:
                # validate() can either raise Unauthorized or return 0 to
                # mean unauthorized.
                if getSecurityManager().validate(p, p, self.factory, m):
                    return m
            except zExceptions_Unauthorized:  # Catch *all* Unauths!
                pass

        return default

    security.declarePublic('isConstructionAllowed')
    def isConstructionAllowed( self, container ):
        """
        a. Does the factory method exist?

        b. Is the factory method usable?

        c. Does the current user have the permission required in
        order to invoke the factory method?
        """
        m = self._queryFactoryMethod(container)
        return (m is not None)

    security.declarePrivate('_constructInstance')
    def _constructInstance(self, container, id, *args, **kw):
        """Build a bare instance of the appropriate type.

        Does not do any security checks.

        Returns the object without calling _finishConstruction().
        """
        m = self._getFactoryMethod(container, check_security=0)

        id = str(id)

        if getattr(aq_base(m), 'isDocTemp', 0):
            kw['id'] = id
            newid = m(m.aq_parent, self.REQUEST, *args, **kw)
        else:
            newid = m(id, *args, **kw)
        # allow factory to munge ID
        newid = newid or id

        return container._getOb(newid)

InitializeClass( FactoryTypeInformation )


class ScriptableTypeInformation( TypeInformation ):
    """
    Invokes a script rather than a factory to create the content.
    """

    __implements__ = ITypeInformation

    meta_type = 'Scriptable Type Information'
    security = ClassSecurityInfo()

    _properties = (TypeInformation._basic_properties + (
        {'id':'permission', 'type': 'string', 'mode':'w',
         'label':'Constructor permission'},
        {'id':'constructor_path', 'type': 'string', 'mode':'w',
         'label':'Constructor path'},
        ) + TypeInformation._advanced_properties)

    permission = ''
    constructor_path = ''

    #
    #   Agent methods
    #
    security.declarePublic('isConstructionAllowed')
    def isConstructionAllowed( self, container ):
        """
        Does the current user have the permission required in
        order to construct an instance?
        """
        permission = self.permission
        if permission and not _checkPermission( permission, container ):
            return 0
        return 1

    security.declarePrivate('_constructInstance')
    def _constructInstance(self, container, id, *args, **kw):
        """Build a bare instance of the appropriate type.

        Does not do any security checks.

        Returns the object without calling _finishConstruction().
        """
        constructor = self.restrictedTraverse( self.constructor_path )

        # make sure ownership is explicit before switching the context
        if not hasattr( aq_base(constructor), '_owner' ):
            constructor._owner = aq_get(constructor, '_owner')
        #   Rewrap to get into container's context.
        constructor = aq_base(constructor).__of__( container )

        id = str(id)
        return constructor(container, id, *args, **kw)

InitializeClass( ScriptableTypeInformation )


# Provide aliases for backward compatibility.
ContentFactoryMetadata = FactoryTypeInformation
ContentTypeInformation = ScriptableTypeInformation


typeClasses = [
    {'class':FactoryTypeInformation,
     'name':FactoryTypeInformation.meta_type,
     'action':'manage_addFactoryTIForm',
     'permission':ManagePortal},
    {'class':ScriptableTypeInformation,
     'name':ScriptableTypeInformation.meta_type,
     'action':'manage_addScriptableTIForm',
     'permission':ManagePortal},
    ]


allowedTypes = [
    'Script (Python)',
    'Python Method',
    'DTML Method',
    'External Method',
    ]


class TypesTool(UniqueObject, Folder, ActionProviderBase):
    """
        Provides a configurable registry of portal content types.
    """

    __implements__ = (ITypesTool, ActionProviderBase.__implements__)

    id = 'portal_types'
    meta_type = 'CMF Types Tool'

    security = ClassSecurityInfo()

    manage_options = ( Folder.manage_options[:1]
                     + ( {'label':'Aliases',
                          'action':'manage_aliases'}, )
                     + ActionProviderBase.manage_options
                     + ( {'label':'Overview',
                          'action':'manage_overview'}, )
                     + Folder.manage_options[1:]
                     )

    #
    #   ZMI methods
    #
    security.declareProtected(ManagePortal, 'manage_overview')
    manage_overview = DTMLFile( 'explainTypesTool', _dtmldir )

    security.declareProtected(ManagePortal, 'manage_aliases')
    manage_aliases = PageTemplateFile( 'typesAliases.zpt', _wwwdir )

    #
    #   ObjectManager methods
    #
    def all_meta_types(self):
        """Adds TypesTool-specific meta types."""
        all = TypesTool.inheritedAttribute('all_meta_types')(self)
        return tuple(typeClasses) + tuple(all)

    def filtered_meta_types(self, user=None):
        # Filters the list of available meta types.
        allowed = {}
        for tc in typeClasses:
            allowed[tc['name']] = 1
        for name in allowedTypes:
            allowed[name] = 1

        all = TypesTool.inheritedAttribute('filtered_meta_types')(self)
        return tuple( [ mt for mt in all if mt['name'] in allowed ] )

    #
    #   other methods
    #
    security.declareProtected(ManagePortal, 'listDefaultTypeInformation')
    def listDefaultTypeInformation(self):
        # Scans for factory_type_information attributes
        # of all products and factory dispatchers within products.
        res = []
        products = self.aq_acquire('_getProducts')()
        for product in products.objectValues():
            product_id = product.getId()

            if hasattr(aq_base(product), 'factory_type_information'):
                ftis = product.factory_type_information
            else:
                package = getattr(Products, product_id, None)
                dispatcher = getattr(package, '__FactoryDispatcher__', None)
                ftis = getattr(dispatcher, 'factory_type_information', None)

            if ftis is not None:
                if callable(ftis):
                    ftis = ftis()

                for fti in ftis:
                    mt = fti.get('meta_type', None)
                    id = fti.get('id', '')

                    if mt:
                        p_id = '%s: %s (%s)' % (product_id, id, mt)
                        res.append( (p_id, fti) )

        return res

    _addTIForm = DTMLFile( 'addTypeInfo', _dtmldir )

    security.declareProtected(ManagePortal, 'manage_addFactoryTIForm')
    def manage_addFactoryTIForm(self, REQUEST):
        ' '
        return self._addTIForm(
            self, REQUEST,
            add_meta_type=FactoryTypeInformation.meta_type,
            types=self.listDefaultTypeInformation())

    security.declareProtected(ManagePortal, 'manage_addScriptableTIForm')
    def manage_addScriptableTIForm(self, REQUEST):
        ' '
        return self._addTIForm(
            self, REQUEST,
            add_meta_type=ScriptableTypeInformation.meta_type,
            types=self.listDefaultTypeInformation())

    security.declareProtected(ManagePortal, 'manage_addTypeInformation')
    def manage_addTypeInformation(self, add_meta_type, id=None,
                                  typeinfo_name=None, RESPONSE=None):
        """
        Create a TypeInformation in self.
        """
        fti = None
        if typeinfo_name:
            info = self.listDefaultTypeInformation()

            # Nasty orkaround to stay backwards-compatible
            # This workaround will disappear in CMF 2.0
            if typeinfo_name.endswith(')'):
                # This is a new-style name. Proceed normally.
                for (name, ft) in info:
                    if name == typeinfo_name:
                        fti = ft
                        break
            else:
                # Attempt to work around the old way
                # This attempt harbors the problem that the first match on
                # meta_type will be used. There could potentially be more
                # than one TypeInformation sharing the same meta_type.
                warn('Please switch to the new format for typeinfo names '
                     '\"product_id: type_id (meta_type)\", the old '
                     'spelling will disappear in CMF 2.0', DeprecationWarning,
                     stacklevel=2)

                ti_prod, ti_mt = [x.strip() for x in typeinfo_name.split(':')]

                for name, ft in info:
                    if ( name.startswith(ti_prod) and
                         name.endswith('(%s)' % ti_mt) ):
                        fti = ft
                        break

            if fti is None:
                raise BadRequest('%s not found.' % typeinfo_name)
            if not id:
                id = fti.get('id', None)
        if not id:
            raise BadRequest('An id is required.')
        for mt in typeClasses:
            if mt['name'] == add_meta_type:
                klass = mt['class']
                break
        else:
            raise ValueError, (
                'Meta type %s is not a type class.' % add_meta_type)
        id = str(id)
        if fti is not None:
            fti = fti.copy()
            if fti.has_key('id'):
                del fti['id']
            ob = klass(id, **fti)
        else:
            ob = klass(id)
        self._setObject(id, ob)
        if RESPONSE is not None:
            RESPONSE.redirect('%s/manage_main' % self.absolute_url())

    security.declareProtected(ManagePortal, 'manage_setTIMethodAliases')
    def manage_setTIMethodAliases(self, REQUEST):
        """ Config method aliases.
        """
        form = REQUEST.form
        aliases = {}
        for k, v in form['aliases'].items():
            v = v.strip()
            if v:
                aliases[k] = v

        for ti in self.listTypeInfo():
            _dict = {}
            for k, v in form[ ti.getId() ].items():
                if aliases.has_key(k):
                    _dict[ aliases[k] ] = v
            ti.setMethodAliases(_dict)
        REQUEST.RESPONSE.redirect('%s/manage_aliases' % self.absolute_url())

    security.declareProtected(AccessContentsInformation, 'getTypeInfo')
    def getTypeInfo( self, contentType ):
        """
            Return an instance which implements the
            TypeInformation interface, corresponding to
            the specified 'contentType'.  If contentType is actually
            an object, rather than a string, attempt to look up
            the appropriate type info using its portal_type.
        """
        if not isinstance(contentType, basestring):
            if hasattr(aq_base(contentType), 'getPortalTypeName'):
                contentType = contentType.getPortalTypeName()
                if contentType is None:
                    return None
            else:
                return None
        ob = getattr( self, contentType, None )
        if getattr(aq_base(ob), '_isTypeInformation', 0):
            return ob
        else:
            return None

    security.declareProtected(AccessContentsInformation, 'listTypeInfo')
    def listTypeInfo( self, container=None ):
        """
            Return a sequence of instances which implement the
            TypeInformation interface, one for each content
            type registered in the portal.
        """
        rval = []
        for t in self.objectValues():
            # Filter out things that aren't TypeInformation and
            # types for which the user does not have adequate permission.
            if not getattr(aq_base(t), '_isTypeInformation', 0):
                continue
            if not t.getId():
                # XXX What's this used for ?
                # Not ready.
                continue
            # check we're allowed to access the type object
            if container is not None:
                if not t.isConstructionAllowed(container):
                    continue
            rval.append(t)
        return rval

    security.declareProtected(AccessContentsInformation, 'listContentTypes')
    def listContentTypes( self, container=None, by_metatype=0 ):
        """
            Return list of content types.

        o Passing 'by_metatype' is deprecated (type information may not
          correspond 1:1 to an underlying meta_type).
        """
        typenames = {}
        for t in self.listTypeInfo( container ):

            if by_metatype:
                warn('TypeInformation.listContentTypes(by_metatype=1) is '
                     'deprecated.',
                     DeprecationWarning)
                name = t.Metatype()
            else:
                name = t.getId()

            if name:
                typenames[ name ] = None

        result = typenames.keys()
        result.sort()
        return result

    security.declarePublic('constructContent')
    def constructContent( self
                        , type_name
                        , container
                        , id
                        , RESPONSE=None
                        , *args
                        , **kw
                        ):
        """
            Build an instance of the appropriate content class in
            'container', using 'id'.
        """
        info = self.getTypeInfo( type_name )
        if info is None:
            raise ValueError('No such content type: %s' % type_name)

        ob = info.constructInstance(container, id, *args, **kw)

        if RESPONSE is not None:
            immediate_url = '%s/%s' % ( ob.absolute_url()
                                      , info.immediate_view )
            RESPONSE.redirect( immediate_url )

        return ob.getId()

    security.declarePrivate( 'listActions' )
    def listActions(self, info=None, object=None):
        """ List all the actions defined by a provider.
        """
        actions = list( self._actions )

        if object is None and info is not None:
            object = info.object
        if object is not None:
            type_info = self.getTypeInfo(object)
            if type_info is not None:
                actions.extend( type_info.listActions() )

        return actions

    security.declareProtected(ManagePortal, 'listMethodAliasKeys')
    def listMethodAliasKeys(self):
        """ List all defined method alias names.
        """
        _dict = {}
        for ti in self.listTypeInfo():
            aliases = ti.getMethodAliases()
            for k, v in aliases.items():
                _dict[k] = 1
        rval = _dict.keys()
        rval.sort()
        return rval

InitializeClass( TypesTool )

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
""" Basic portal catalog.

$Id: CatalogTool.py 38289 2005-09-03 13:40:17Z yuppie $
"""

from AccessControl import ClassSecurityInfo
from AccessControl.PermissionRole import rolesForPermissionOn
from DateTime import DateTime
from Globals import DTMLFile
from Globals import InitializeClass
from Products.ZCatalog.ZCatalog import LOG
from Products.ZCatalog.ZCatalog import ZCatalog
from Products.ZCTextIndex.HTMLSplitter import HTMLWordSplitter
from Products.ZCTextIndex.Lexicon import CaseNormalizer
from Products.ZCTextIndex.Lexicon import Splitter
from Products.ZCTextIndex.Lexicon import StopWordRemover
from Products.ZCTextIndex.ZCTextIndex import PLexicon

from ActionProviderBase import ActionProviderBase
from interfaces.portal_catalog \
        import IndexableObjectWrapper as IIndexableObjectWrapper
from interfaces.portal_catalog import portal_catalog as ICatalogTool
from permissions import AccessInactivePortalContent
from permissions import ManagePortal
from permissions import View
from utils import _checkPermission
from utils import _dtmldir
from utils import _getAuthenticatedUser
from utils import _mergedLocalRoles
from utils import getToolByName
from utils import SimpleRecord
from utils import UniqueObject


class IndexableObjectWrapper:

    __implements__ = IIndexableObjectWrapper

    def __init__(self, vars, ob):
        self.__vars = vars
        self.__ob = ob

    def __getattr__(self, name):
        vars = self.__vars
        if vars.has_key(name):
            return vars[name]
        return getattr(self.__ob, name)

    def allowedRolesAndUsers(self):
        """
        Return a list of roles and users with View permission.
        Used by PortalCatalog to filter out items you're not allowed to see.
        """
        ob = self.__ob
        allowed = {}
        for r in rolesForPermissionOn(View, ob):
            allowed[r] = 1
        localroles = _mergedLocalRoles(ob)
        for user, roles in localroles.items():
            for role in roles:
                if allowed.has_key(role):
                    allowed['user:' + user] = 1
        if allowed.has_key('Owner'):
            del allowed['Owner']
        return list(allowed.keys())


class CatalogTool(UniqueObject, ZCatalog, ActionProviderBase):
    """ This is a ZCatalog that filters catalog queries.
    """

    __implements__ = (ICatalogTool, ZCatalog.__implements__,
                      ActionProviderBase.__implements__)

    id = 'portal_catalog'
    meta_type = 'CMF Catalog'
    _actions = ()

    security = ClassSecurityInfo()

    manage_options = ( ZCatalog.manage_options +
                      ActionProviderBase.manage_options +
                      ({ 'label' : 'Overview', 'action' : 'manage_overview' }
                     ,
                     ))

    def __init__(self):
        ZCatalog.__init__(self, self.getId())
        self._initIndexes()

    #
    #   Subclass extension interface
    #
    security.declarePublic( 'enumerateIndexes' ) # Subclass can call
    def enumerateIndexes( self ):
        #   Return a list of ( index_name, type, extra ) tuples for the initial
        #   index set.
        #   Creator is deprecated and may go away, use listCreators!
        #   meta_type is deprecated and may go away, use portal_type!
        plaintext_extra = SimpleRecord( lexicon_id='plaintext_lexicon'
                                      , index_type='Okapi BM25 Rank'
                                      )
        htmltext_extra = SimpleRecord( lexicon_id='htmltext_lexicon'
                                     , index_type='Okapi BM25 Rank'
                                     )

        return ( ('Title', 'ZCTextIndex', plaintext_extra)
               , ('Subject', 'KeywordIndex', None)
               , ('Description', 'ZCTextIndex', plaintext_extra)
               , ('Creator', 'FieldIndex', None)
               , ('listCreators', 'KeywordIndex', None)
               , ('SearchableText', 'ZCTextIndex', htmltext_extra)
               , ('Date', 'DateIndex', None)
               , ('Type', 'FieldIndex', None)
               , ('created', 'DateIndex', None)
               , ('effective', 'DateIndex', None)
               , ('expires', 'DateIndex', None)
               , ('modified', 'DateIndex', None)
               , ('allowedRolesAndUsers', 'KeywordIndex', None)
               , ('review_state', 'FieldIndex', None)
               , ('in_reply_to', 'FieldIndex', None)
               , ('meta_type', 'FieldIndex', None)
               , ('getId', 'FieldIndex', None)
               , ('path', 'PathIndex', None)
               , ('portal_type', 'FieldIndex', None)
               )

    security.declarePublic('enumerateLexicons')
    def enumerateLexicons(self):
        return (
                 ( 'plaintext_lexicon'
                 , Splitter()
                 , CaseNormalizer()
                 , StopWordRemover()
                 )
               , ( 'htmltext_lexicon'
                 , HTMLWordSplitter()
                 , CaseNormalizer()
                 , StopWordRemover()
                 )
               )

    security.declarePublic( 'enumerateColumns' )
    def enumerateColumns( self ):
        #   Return a sequence of schema names to be cached.
        #   Creator is deprecated and may go away, use listCreators!
        return ( 'Subject'
               , 'Title'
               , 'Description'
               , 'Type'
               , 'review_state'
               , 'Creator'
               , 'listCreators'
               , 'Date'
               , 'getIcon'
               , 'created'
               , 'effective'
               , 'expires'
               , 'modified'
               , 'CreationDate'
               , 'EffectiveDate'
               , 'ExpirationDate'
               , 'ModificationDate'
               , 'getId'
               , 'portal_type'
               )

    def _initIndexes(self):
        # ZCTextIndex lexicons
        for id, splitter, normalizer, sw_remover in self.enumerateLexicons():
            lexicon = PLexicon(id, '', splitter, normalizer, sw_remover)
            self._setObject(id, lexicon)

        # Content indexes
        self._catalog.indexes.clear()
        for index_name, index_type, extra in self.enumerateIndexes():
            self.addIndex(index_name, index_type, extra=extra)

        # Cached metadata
        self._catalog.names = ()
        self._catalog.schema.clear()
        for column_name in self.enumerateColumns():
            self.addColumn(column_name)

    #
    #   ZMI methods
    #
    security.declareProtected(ManagePortal, 'manage_overview')
    manage_overview = DTMLFile( 'explainCatalogTool', _dtmldir )

    #
    #   'portal_catalog' interface methods
    #

    def _listAllowedRolesAndUsers( self, user ):
        result = list( user.getRoles() )
        result.append( 'Anonymous' )
        result.append( 'user:%s' % user.getId() )
        return result

    def _convertQuery(self, kw):
        # Convert query to modern syntax
        for k in 'effective', 'expires':
            kusage = k+'_usage'
            if not kw.has_key(kusage):
                continue
            usage = kw[kusage]
            if not usage.startswith('range:'):
                raise ValueError("Incorrect usage %s" % `usage`)
            kw[k] = {'query': kw[k], 'range': usage[6:]}
            del kw[kusage]

    # searchResults has inherited security assertions.
    def searchResults(self, REQUEST=None, **kw):
        """
            Calls ZCatalog.searchResults with extra arguments that
            limit the results to what the user is allowed to see.
        """
        user = _getAuthenticatedUser(self)
        kw[ 'allowedRolesAndUsers' ] = self._listAllowedRolesAndUsers( user )

        if not _checkPermission( AccessInactivePortalContent, self ):
            now = DateTime()

            self._convertQuery(kw)

            # Intersect query restrictions with those implicit to the tool
            for k in 'effective', 'expires':
                if kw.has_key(k):
                    range = kw[k]['range'] or ''
                    query = kw[k]['query']
                    if not isinstance(query, (tuple, list)):
                        query = (query,)
                else:
                    range = ''
                    query = None
                if range.find('min') > -1:
                    lo = min(query)
                else:
                    lo = None
                if range.find('max') > -1:
                    hi = max(query)
                else:
                    hi = None
                if k == 'effective':
                    if hi is None or hi > now:
                        hi = now
                    if lo is not None and hi < lo:
                        return ()
                else: # 'expires':
                    if lo is None or lo < now:
                        lo = now
                    if hi is not None and hi < lo:
                        return ()
                # Rebuild a query
                if lo is None:
                    query = hi
                    range = 'max'
                elif hi is None:
                    query = lo
                    range = 'min'
                else:
                    query = (lo, hi)
                    range = 'min:max'
                kw[k] = {'query': query, 'range': range}

        return ZCatalog.searchResults(self, REQUEST, **kw)

    __call__ = searchResults

    security.declarePrivate('unrestrictedSearchResults')
    def unrestrictedSearchResults(self, REQUEST=None, **kw):
        """Calls ZCatalog.searchResults directly without restrictions.

        This method returns every also not yet effective and already expired
        objects regardless of the roles the caller has.

        CAUTION: Care must be taken not to open security holes by
        exposing the results of this method to non authorized callers!

        If you're in doubt if you should use this method or
        'searchResults' use the latter.
        """
        return ZCatalog.searchResults(self, REQUEST, **kw)

    def __url(self, ob):
        return '/'.join( ob.getPhysicalPath() )

    manage_catalogFind = DTMLFile( 'catalogFind', _dtmldir )

    def catalog_object(self, obj, uid=None, idxs=None, update_metadata=1,
                       pghandler=None):
        # Wraps the object with workflow and accessibility
        # information just before cataloging.
        wftool = getToolByName(self, 'portal_workflow', None)
        if wftool is not None:
            vars = wftool.getCatalogVariablesFor(obj)
        else:
            vars = {}
        w = IndexableObjectWrapper(vars, obj)
        try:
            ZCatalog.catalog_object(self, w, uid, idxs, update_metadata,
                                    pghandler)
        except TypeError:
            # BBB: for Zope 2.7
            ZCatalog.catalog_object(self, w, uid, idxs, update_metadata)

    security.declarePrivate('indexObject')
    def indexObject(self, object):
        '''Add to catalog.
        '''
        url = self.__url(object)
        self.catalog_object(object, url)

    security.declarePrivate('unindexObject')
    def unindexObject(self, object):
        '''Remove from catalog.
        '''
        url = self.__url(object)
        self.uncatalog_object(url)

    security.declarePrivate('reindexObject')
    def reindexObject(self, object, idxs=[], update_metadata=1, uid=None):
        """Update catalog after object data has changed.

        The optional idxs argument is a list of specific indexes
        to update (all of them by default).

        The update_metadata flag controls whether the object's
        metadata record is updated as well.

        If a non-None uid is passed, it will be used as the catalog uid
        for the object instead of its physical path.
        """
        if uid is None:
            uid = self.__url(object)
        if idxs != []:
            # Filter out invalid indexes.
            valid_indexes = self._catalog.indexes.keys()
            idxs = [i for i in idxs if i in valid_indexes]
        self.catalog_object(object, uid, idxs, update_metadata)

    # BBB: for Zope 2.8.0
    # copied from revision 31005 of ZCatalog.py
    def manage_convertIndexes(self, REQUEST=None, RESPONSE=None, URL1=None):
        """Recreate indexes derived from UnIndex because the implementation of
           __len__ changed in Zope 2.8. Pre-Zope 2.7 installation used to implement
           __len__ as persistent attribute of the index instance which is totally
           incompatible with the new extension class implementation based on new-style
           classes. 
        """

        LOG.info('Start migration of indexes for %s' % self.absolute_url(1))
        
        reindex_ids = []

        for idx in self.Indexes.objectValues():
            bases = [str(name) for name in idx.__class__.__bases__]
            found = False

            if idx.meta_type  == 'PathIndex':
                found = True
            else:
                for base in bases:
                    if 'UnIndex' in base:
                        found = True
                        break

            if found:
                idx_type = idx.meta_type
                idx_id = idx.getId()
                LOG.info('processing index %s' % idx_id)

                indexed_attrs = getattr(idx, 'indexed_attrs', None)

                if idx.meta_type == 'DateRangeIndex':
                    since_field = getattr(idx, '_since_field', None)
                    until_field = getattr(idx, '_until_field', None)

                self.delIndex(idx.getId())
                self.addIndex(idx_id, idx_type)
                new_idx = self.Indexes[idx_id]

                if indexed_attrs:
                    setattr(new_idx, 'indexed_attrs', indexed_attrs)
                if idx.meta_type == 'DateRangeIndex':
                    setattr(new_idx, '_since_field',  since_field)
                    setattr(new_idx, '_until_field', until_field)
                reindex_ids.append(idx_id)
        
        if reindex_ids:
            LOG.info('Reindexing %s' % ', '.join(reindex_ids))
            self.manage_reindexIndex(reindex_ids, REQUEST)

        self._migrated_280 = True
        LOG.info('Finished migration of indexes for %s' % self.absolute_url(1))

        if RESPONSE:
            RESPONSE.redirect( URL1 +
            '/manage_main?manage_tabs_message=Indexes%20converted%20and%20reindexed')

InitializeClass(CatalogTool)

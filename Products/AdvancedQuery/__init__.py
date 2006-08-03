# Copyright (C) 2003 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: __init__.py,v 1.5 2006/06/25 19:11:24 dieter Exp $
'''Advanced Query

see 'AdvancedQuery.html' for documentation.
'''

from AccessControl import allow_module as _allow_module, ClassSecurityInfo
from Globals import InitializeClass

from AdvancedQuery import Eq, In, Le, Ge, \
     MatchGlob, MatchRegexp, \
     Between, Not, And, Or, Generic, Indexed, \
     _CompositeQuery, LiteralResultSet

from eval import eval as _eval

from ranking import RankByQueries_Sum, RankByQueries_Max


############################################################################
## Security
_allow_module('Products.AdvancedQuery')
_s = ClassSecurityInfo(); _s.declarePublic('addSubquery')
_CompositeQuery._s = _s; InitializeClass(_CompositeQuery)


############################################################################
## ZCatalog extension
def _makeAdvancedQuery(self,catalogSearchSpec):
  '''advanced query corresponding to *catalogSearchSpec* (a dictionary).'''
  q = And(); get = catalogSearchSpec.get
  for i in self.Indexes.objectIds():
    vi = get(i)
    if vi is None or vi == '': continue
    if not (isinstance(vi, dict) and vi.get('query') is not None
            or getattr(vi, 'query', None) is not None):
      usage = get(i+'_usage')
      if usage is not None:
        if not usage.startswith('range:'):
          raise ValueError, 'unsupported usage spec: %s' % usage
        vi = {'query' : vi, 'range' : usage[6:]}
    q.addSubquery(Generic(i,vi))
  return q

from Products.ZCatalog.ZCatalog import ZCatalog
ZCatalog.evalAdvancedQuery = _eval
ZCatalog.makeAdvancedQuery = _makeAdvancedQuery
del ZCatalog


############################################################################
## CatalogTool extension
try: from Products.CMFCore.CatalogTool import CatalogTool
except ImportError: CatalogTool= None
if CatalogTool:

  from Products.CMFCore.CatalogTool import _getAuthenticatedUser, _checkPermission, AccessInactivePortalContent

  def _evalAdvancedQuery(self,query,sortSpecs=()):
    '''evaluate *query* for 'CatalogTool' and sort results according to *sortSpec*.'''
    query = query._clone()

    # taken from 'CatalogTool.searchResults'
    user = _getAuthenticatedUser(self)
    query &= In('allowedRolesAndUsers',self._listAllowedRolesAndUsers(user))
    if not _checkPermission(AccessInactivePortalContent,self):
      now= self.ZopeTime()
      if 'ValidityRange' in self.Indexes.objectIds():
        query &= Eq('ValidityRange', now)
      else:
        query &= Le('effective',now)
        query &= Ge('expires',now)
    return _eval(self,query,sortSpecs)

  CatalogTool.evalAdvancedQuery= _evalAdvancedQuery
del CatalogTool




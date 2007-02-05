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
""" Catalog tool interface.

$Id: portal_catalog.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class portal_catalog(Interface):
    '''This tool interacts with a customized ZCatalog.
    '''
    id = Attribute('id', 'Must be set to "portal_catalog"')

    # searchResults inherits security assertions from ZCatalog.
    def searchResults(REQUEST=None, **kw):
        '''Calls ZCatalog.searchResults() with extra arguments that
        limit the results to what the user is allowed to see.
        '''

    # __call__ inherits security assertions from ZCatalog.
    def __call__(REQUEST=None, **kw):
        '''Same as searchResults().'''

    def unrestrictedSearchResults(REQUEST=None, **kw):
        '''Calls ZCatalog.searchResults() without any CMF specific
        processing.

        Permission -- Python only
        '''

    def indexObject(object):
        """ Add to catalog.

        Permission -- Python only
        """

    def unindexObject(object):
        """ Remove from catalog.

        Permission -- Python only
        """

    def reindexObject(object, idxs=[], update_metadata=1):
        """ Update entry in catalog.

        The optional idxs argument is a list of specific indexes
        to update (all of them by default).

        Permission -- Python only
        """


class IndexableObjectWrapper(Interface):
    """ Indexable object wrapper interface.
    """

    def allowedRolesAndUsers():
        """
        Return a list of roles and users with View permission.
        Used by PortalCatalog to filter out items you're not allowed to see.
        """

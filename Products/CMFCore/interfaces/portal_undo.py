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
""" Undo tool interface.

$Id: portal_undo.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class portal_undo(Interface):
    '''Provides access to Zope undo functions.
    '''
    id = Attribute('id', 'Must be set to "portal_undo"')

    # permission: 'Undo changes'
    def listUndoableTransactionsFor(object,
                                    first_transaction=None,
                                    last_transaction=None,
                                    PrincipiaUndoBatchSize=None):
        '''Lists all transaction IDs the user is allowed to undo.
        '''

    # permission: 'Undo changes'
    def undo(object, transaction_info):
        '''Performs an undo operation.
        '''

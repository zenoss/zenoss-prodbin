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
""" Expressions in a web-configurable workflow.

$Id: Expression.py 36510 2004-09-03 17:18:18Z jens $
"""

from AccessControl import ClassSecurityInfo
from Acquisition import aq_base, aq_inner, aq_parent
from Globals import InitializeClass
from Globals import Persistent
from Products.PageTemplates.Expressions import getEngine
from Products.PageTemplates.Expressions import SecureModuleImporter

from utils import getToolByName


class Expression (Persistent):
    text = ''
    _v_compiled = None

    security = ClassSecurityInfo()

    def __init__(self, text):
        self.text = text
        self._v_compiled = getEngine().compile(text)

    def __call__(self, econtext):
        compiled = self._v_compiled
        if compiled is None:
            compiled = self._v_compiled = getEngine().compile(self.text)
        # ?? Maybe expressions should manipulate the security
        # context stack.
        res = compiled(econtext)
        if isinstance(res, Exception):
            raise res
        #print 'returning %s from %s' % (`res`, self.text)
        return res

InitializeClass(Expression)


def getExprContext(context, object=None):
    request = getattr(context, 'REQUEST', None)
    if request:
        cache = request.get('_ec_cache', None)
        if cache is None:
            request['_ec_cache'] = cache = {}
        ec = cache.get( id(object), None )
    else:
        ec = None
    if ec is None:
        utool = getToolByName(context, 'portal_url')
        portal = utool.getPortalObject()
        if object is None or not hasattr(object, 'aq_base'):
            folder = portal
        else:
            folder = object
            # Search up the containment hierarchy until we find an
            # object that claims it's a folder.
            while folder is not None:
                if getattr(aq_base(folder), 'isPrincipiaFolderish', 0):
                    # found it.
                    break
                else:
                    folder = aq_parent(aq_inner(folder))
        ec = createExprContext(folder, portal, object)
        if request:
            cache[ id(object) ] = ec
    return ec


def createExprContext(folder, portal, object):
    '''
    An expression context provides names for TALES expressions.
    '''
    pm = getToolByName(portal, 'portal_membership')
    if object is None:
        object_url = ''
    else:
        object_url = object.absolute_url()
    if pm.isAnonymousUser():
        member = None
    else:
        member = pm.getAuthenticatedMember()
    data = {
        'object_url':   object_url,
        'folder_url':   folder.absolute_url(),
        'portal_url':   portal.absolute_url(),
        'object':       object,
        'folder':       folder,
        'portal':       portal,
        'nothing':      None,
        'request':      getattr( object, 'REQUEST', None ),
        'modules':      SecureModuleImporter,
        'member':       member,
        'here':         object,
        }
    return getEngine().getContext(data)


#############################################################################
#
# Copyright (c) 2007 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################

"""Hotfix_20070319

Protect security methods against GET requests.

"""

import inspect
from zExceptions import Forbidden
from ZPublisher.HTTPRequest import HTTPRequest

def _buildFacade(spec, docstring):
    """Build a facade function, matching the decorated method in signature.
    
    Note that defaults are replaced by None, and _curried will reconstruct
    these to preserve mutable defaults.
    
    """
    args = inspect.formatargspec(formatvalue=lambda v: '=None', *spec)
    callargs = inspect.formatargspec(formatvalue=lambda v: '', *spec)
    return 'def _facade%s:\n    """%s"""\n    return _curried%s' % (
        args, docstring, callargs)

def postonly(callable):
    """Only allow callable when request method is POST."""
    spec = inspect.getargspec(callable)
    args, defaults = spec[0], spec[3]
    try:
        r_index = args.index('REQUEST')
    except ValueError:
        raise ValueError('No REQUEST parameter in callable signature')
    
    arglen = len(args)
    if defaults is not None:
        defaults = zip(args[arglen - len(defaults):], defaults)
        arglen -= len(defaults)
            
    def _curried(*args, **kw):
        request = None
        if len(args) > r_index:
            request = args[r_index]
            
        if isinstance(request, HTTPRequest):
            if request.get('REQUEST_METHOD', 'GET').upper() != 'POST':
                raise Forbidden('Request must be POST')

        # Reconstruct keyword arguments
        if defaults is not None:
            args, kwparams = args[:arglen], args[arglen:]
            for positional, (key, default) in zip(kwparams, defaults):
                if positional is None:
                    kw[key] = default
                else:
                    kw[key] = positional
                    
        return callable(*args, **kw)
    
    facade_globs = dict(_curried=_curried)
    exec _buildFacade(spec, callable.__doc__) in facade_globs
    return facade_globs['_facade']

# Add REQUEST to BasicUserFolder.userFolder* methods as well as protect them
from AccessControl.User import BasicUserFolder

_original_ufAddUser = BasicUserFolder.userFolderAddUser
def ufAddUser(self, name, password, roles, domains, REQUEST=None, **kw):
    return _original_ufAddUser(self, name, password, roles, domains, **kw)
ufAddUser.__doc__ = _original_ufAddUser.__doc__
BasicUserFolder.userFolderAddUser = postonly(ufAddUser)

_original_ufEditUser = BasicUserFolder.userFolderEditUser
def ufEditUser(self, name, password, roles, domains, REQUEST=None, **kw):
    return _original_ufEditUser(self, name, password, roles, domains, **kw)
ufEditUser.__doc__ = _original_ufEditUser.__doc__
BasicUserFolder.userFolderEditUser = postonly(ufEditUser)

_original_ufDelUsers = BasicUserFolder.userFolderDelUsers
def ufDelUsers(self, names, REQUEST=None):
    return _original_ufDelUsers(self, names)
ufDelUsers.__doc__ = _original_ufDelUsers.__doc__
BasicUserFolder.userFolderDelUsers = postonly(ufDelUsers)

BasicUserFolder.manage_setUserFolderProperties = postonly(
    BasicUserFolder.manage_setUserFolderProperties)
BasicUserFolder._addUser = postonly(BasicUserFolder._addUser)
BasicUserFolder._changeUser = postonly(BasicUserFolder._changeUser)
BasicUserFolder._delUsers = postonly(BasicUserFolder._delUsers)

from AccessControl.Owned import Owned
Owned.manage_takeOwnership = postonly(Owned.manage_takeOwnership)
Owned.manage_changeOwnershipType = postonly(Owned.manage_changeOwnershipType)

from AccessControl.PermissionMapping import RoleManager as PMRM
PMRM.manage_setPermissionMapping = postonly(PMRM.manage_setPermissionMapping)

from AccessControl.Role import RoleManager as RMRM
RMRM.manage_acquiredPermissions = postonly(RMRM.manage_acquiredPermissions)
RMRM.manage_permission = postonly(RMRM.manage_permission)
RMRM.manage_changePermissions = postonly(RMRM.manage_changePermissions)
RMRM.manage_addLocalRoles = postonly(RMRM.manage_addLocalRoles)
RMRM.manage_setLocalRoles = postonly(RMRM.manage_setLocalRoles)
RMRM.manage_delLocalRoles = postonly(RMRM.manage_delLocalRoles)
RMRM._addRole = postonly(RMRM._addRole)
RMRM._delRoles = postonly(RMRM._delRoles)

from OFS.DTMLMethod import DTMLMethod
DTMLMethod.manage_proxy = postonly(DTMLMethod.manage_proxy)

from Products.PythonScripts.PythonScript import PythonScript
PythonScript.manage_proxy = postonly(PythonScript.manage_proxy)

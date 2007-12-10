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
""" Customizable Python scripts that come from the filesystem.

$Id: FSPythonScript.py 41759 2006-02-23 13:59:08Z mj $
"""

import new

from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from ComputedAttribute import ComputedAttribute
from Globals import DTMLFile
from Globals import InitializeClass
from OFS.Cache import Cacheable
from Products.PythonScripts.PythonScript import PythonScript
from Shared.DC.Scripts.Script import Script

from DirectoryView import registerFileExtension
from DirectoryView import registerMetaType
from FSObject import FSObject
from permissions import FTPAccess
from permissions import View
from permissions import ViewManagementScreens
from utils import _dtmldir
from utils import expandpath

_marker = []


class bad_func_code:
    co_varnames = ()
    co_argcount = 0


class FSPythonScript (FSObject, Script):
    """FSPythonScripts act like Python Scripts but are not directly
    modifiable from the management interface."""

    meta_type = 'Filesystem Script (Python)'
    _params = _body = ''
    _v_f = None
    _proxy_roles = ()

    _owner = None  # Unowned

    manage_options=(
        (
            {'label':'Customize', 'action':'manage_main'},
            {'label':'Test',
             'action':'ZScriptHTML_tryForm',
             'help': ('PythonScripts', 'PythonScript_test.stx')},
            )
            + Cacheable.manage_options
        )

    # Use declarative security
    security = ClassSecurityInfo()
    security.declareObjectProtected(View)
    security.declareProtected(View, 'index_html',)
    # Prevent the bindings from being edited TTW
    security.declarePrivate('ZBindings_edit','ZBindingsHTML_editForm',
                            'ZBindingsHTML_editAction')

    security.declareProtected(ViewManagementScreens, 'manage_main')
    manage_main = DTMLFile('custpy', _dtmldir)

    def _createZODBClone(self):
        """Create a ZODB (editable) equivalent of this object."""
        obj = PythonScript(self.getId())
        obj.write(self.read())
        return obj

    def _readFile(self, reparse):
        """Read the data from the filesystem.

        Read the file (indicated by exandpath(self._filepath), and parse the
        data if necessary.
        """
        fp = expandpath(self._filepath)
        file = open(fp, 'rU')
        try: data = file.read()
        finally: file.close()
        if reparse:
            self._write(data, reparse)

    def _validateProxy(self, roles=None):
        pass

    def __render_with_namespace__(self, namespace):
        '''Calls the script.'''
        self._updateFromFS()
        return Script.__render_with_namespace__(self, namespace)

    def __call__(self, *args, **kw):
        '''Calls the script.'''
        self._updateFromFS()
        return Script.__call__(self, *args, **kw)

    #### The following is mainly taken from PythonScript.py ###

    def _exec(self, bound_names, args, kw):
        """Call a Python Script

        Calling a Python Script is an actual function invocation.
        """
        # do caching
        keyset = None
        if self.ZCacheable_isCachingEnabled():
            # Prepare a cache key.
            keyset = kw.copy()
            asgns = self.getBindingAssignments()
            name_context = asgns.getAssignedName('name_context', None)
            if name_context:
                keyset[name_context] = self.aq_parent.getPhysicalPath()
            name_subpath = asgns.getAssignedName('name_subpath', None)
            if name_subpath:
                keyset[name_subpath] = self._getTraverseSubpath()
            # Note: perhaps we should cache based on name_ns also.
            keyset['*'] = args
            result = self.ZCacheable_get(keywords=keyset, default=_marker)
            if result is not _marker:
                # Got a cached value.
                return result

        # Prepare the function.
        f = self._v_f
        if f is None:
            # The script has errors.
            __traceback_supplement__ = (
                FSPythonScriptTracebackSupplement, self, 0)
            raise RuntimeError, '%s has errors.' % self._filepath

        # Updating func_globals directly is not thread safe here.
        # In normal PythonScripts, every thread has its own
        # copy of the function.  But in FSPythonScripts
        # there is only one copy.  So here's another way.
        new_globals = f.func_globals.copy()
        new_globals['__traceback_supplement__'] = (
            FSPythonScriptTracebackSupplement, self)
        new_globals['__file__'] = self._filepath
        if bound_names:
            new_globals.update(bound_names)
        if f.func_defaults:
            f = new.function(f.func_code, new_globals, f.func_name,
                             f.func_defaults)
        else:
            f = new.function(f.func_code, new_globals, f.func_name)

        # Execute the function in a new security context.
        security=getSecurityManager()
        security.addContext(self)
        try:
            result = f(*args, **kw)
            if keyset is not None:
                # Store the result in the cache.
                self.ZCacheable_set(result, keywords=keyset)
            return result
        finally:
            security.removeContext(self)

    security.declareProtected(ViewManagementScreens, 'getModTime')
    # getModTime defined in FSObject

    security.declareProtected(ViewManagementScreens, 'ZScriptHTML_tryForm')
    # ZScriptHTML_tryForm defined in Shared.DC.Scripts.Script.Script

    def ZScriptHTML_tryParams(self):
        """Parameters to test the script with."""
        param_names = []
        for name in self._params.split(','):
            name = name.strip()
            if name and name[0] != '*':
                param_names.append( name.split('=', 1)[0] )
        return param_names

    security.declareProtected(ViewManagementScreens, 'read')
    def read(self):
        self._updateFromFS()
        return self._source

    security.declareProtected(ViewManagementScreens, 'document_src')
    def document_src(self, REQUEST=None, RESPONSE=None):
        """Return unprocessed document source."""

        if RESPONSE is not None:
            RESPONSE.setHeader('Content-Type', 'text/plain')
        return self._source

    security.declareProtected(ViewManagementScreens, 'PrincipiaSearchSource')
    def PrincipiaSearchSource(self):
        "Support for searching - the document's contents are searched."
        return "%s\n%s" % (self._params, self._body)

    security.declareProtected(ViewManagementScreens, 'params')
    def params(self): return self._params

    security.declareProtected(ViewManagementScreens, 'manage_haveProxy')
    manage_haveProxy = PythonScript.manage_haveProxy.im_func

    security.declareProtected(ViewManagementScreens, 'body')
    def body(self): return self._body

    security.declareProtected(ViewManagementScreens, 'get_size')
    def get_size(self): return len(self.read())

    security.declareProtected(FTPAccess, 'manage_FTPget')
    def manage_FTPget(self):
        "Get source for FTP download"
        self.REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
        return self.read()

    def _write(self, text, compile):
        '''
        Parses the source, storing the body, params, title, bindings,
        and source in self.  If compile is set, compiles the
        function.
        '''
        ps = PythonScript(self.id)
        ps.write(text)
        if compile:
            ps._makeFunction(1)
            self._v_f = f = ps._v_f
            if f is not None:
                self.func_code = f.func_code
                self.func_defaults = f.func_defaults
            else:
                # There were errors in the compile.
                # No signature.
                self.func_code = bad_func_code()
                self.func_defaults = None
        self._body = ps._body
        self._params = ps._params
        self.title = ps.title
        self._setupBindings(ps.getBindingAssignments().getAssignedNames())
        self._source = ps.read()  # Find out what the script sees.

    def func_defaults(self):
        # This ensures func_code and func_defaults are
        # set when the code hasn't been compiled yet,
        # just in time for mapply().  Truly odd, but so is mapply(). :P
        self._updateFromFS()
        return self.__dict__.get('func_defaults', None)
    func_defaults = ComputedAttribute(func_defaults, 1)

    def func_code(self):
        # See func_defaults.
        self._updateFromFS()
        return self.__dict__.get('func_code', None)
    func_code = ComputedAttribute(func_code, 1)

    def title(self):
        # See func_defaults.
        self._updateFromFS()
        return self.__dict__.get('title', None)
    title = ComputedAttribute(title, 1)

    def getBindingAssignments(self):
        # Override of the version in Bindings.py.
        # This version ensures that bindings get loaded on demand.
        if not hasattr(self, '_bind_names'):
            # Set a default first to avoid recursion
            self._setupBindings()
            # Now do it for real
            self._updateFromFS()
        return self._bind_names

InitializeClass(FSPythonScript)


class FSPythonScriptTracebackSupplement:
    """Implementation of ITracebackSupplement

    Makes script-specific info available in exception tracebacks.
    """
    def __init__(self, script, line=-1):
        self.object = script
        # If line is set to -1, it means to use tb_lineno.
        self.line = line


registerFileExtension('py', FSPythonScript)
registerMetaType('Script (Python)', FSPythonScript)

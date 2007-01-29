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
""" Customizable page templates that come from the filesystem.

$Id: FSPageTemplate.py 65899 2006-03-10 12:38:33Z mj $
"""

import re, sys

import Globals
from DocumentTemplate.DT_Util import html_quote
from AccessControl import getSecurityManager, ClassSecurityInfo
from OFS.Cache import Cacheable
from Shared.DC.Scripts.Script import Script
from Products.PageTemplates.PageTemplate import PageTemplate
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate, Src

from permissions import FTPAccess
from permissions import View
from permissions import ViewManagementScreens
from DirectoryView import registerFileExtension
from DirectoryView import registerMetaType
from FSObject import FSObject
from utils import _setCacheHeaders, _checkConditionalGET
from utils import expandpath

xml_detect_re = re.compile('^\s*<\?xml\s+(?:[^>]*?encoding=["\']([^"\'>]+))?')
_marker = []  # Create a new marker object.


class FSPageTemplate(FSObject, Script, PageTemplate):
    "Wrapper for Page Template"

    meta_type = 'Filesystem Page Template'

    _owner = None  # Unowned

    manage_options=(
        (
            {'label':'Customize', 'action':'manage_main'},
            {'label':'Test', 'action':'ZScriptHTML_tryForm'},
            )
            +Cacheable.manage_options
        )

    security = ClassSecurityInfo()
    security.declareObjectProtected(View)

    security.declareProtected(ViewManagementScreens, 'manage_main')
    manage_main = Globals.DTMLFile('dtml/custpt', globals())

    # Declare security for unprotected PageTemplate methods.
    security.declarePrivate('pt_edit', 'write')

    def __init__(self, id, filepath, fullname=None, properties=None):
        FSObject.__init__(self, id, filepath, fullname, properties)
        self.ZBindings_edit(self._default_bindings)

    def _createZODBClone(self):
        """Create a ZODB (editable) equivalent of this object."""
        obj = ZopePageTemplate(self.getId(), self._text, self.content_type)
        obj.expand = 0
        obj.write(self.read())
        return obj

#    def ZCacheable_isCachingEnabled(self):
#        return 0

    def _readFile(self, reparse):
        fp = expandpath(self._filepath)
        file = open(fp, 'rU')    # not 'rb', as this is a text file!
        try:
            data = file.read()
        finally:
            file.close()

        if reparse:
            # If we already have a content_type set it must come from a
            # .metadata file and we should always honor that. The content
            # type is initialized as text/html by default, so we only
            # attempt further detection if the default is encountered.
            # One previous misbehavior remains: It is not possible to
            # force a text./html type if parsing detects it as XML.
            if getattr(self, 'content_type', 'text/html') == 'text/html':
                xml_info = xml_detect_re.match(data)
                if xml_info:
                    # Smells like xml
                    # set "content_type" from the XML declaration
                    encoding = xml_info.group(1) or 'utf-8'
                    self.content_type = 'text/xml; charset=%s' % encoding

            self.write(data)

    security.declarePrivate('read')
    def read(self):
        # Tie in on an opportunity to auto-update
        self._updateFromFS()
        return FSPageTemplate.inheritedAttribute('read')(self)

    ### The following is mainly taken from ZopePageTemplate.py ###

    expand = 0

    func_defaults = None
    func_code = ZopePageTemplate.func_code
    _default_bindings = ZopePageTemplate._default_bindings

    security.declareProtected(View, '__call__')

    def pt_macros(self):
        # Tie in on an opportunity to auto-reload
        self._updateFromFS()
        return FSPageTemplate.inheritedAttribute('pt_macros')(self)

    def pt_render(self, source=0, extra_context={}):
        self._updateFromFS()  # Make sure the template has been loaded.

        if not source:
            # If we have a conditional get, set status 304 and return
            # no content
            if _checkConditionalGET(self, extra_context):
                return ''
        
        result = FSPageTemplate.inheritedAttribute('pt_render')(
                                self, source, extra_context
                                )
        if not source:
            _setCacheHeaders(self, extra_context)
        return result

    security.declareProtected(ViewManagementScreens, 'pt_source_file')
    def pt_source_file(self):

        """ Return a file name to be compiled into the TAL code.
        """
        return 'file:%s' % self._filepath

    security.declarePrivate( '_ZPT_exec' )
    _ZPT_exec = ZopePageTemplate._exec.im_func

    security.declarePrivate( '_exec' )
    def _exec(self, bound_names, args, kw):
        """Call a FSPageTemplate"""
        try:
            response = self.REQUEST.RESPONSE
        except AttributeError:
            response = None
        # Read file first to get a correct content_type default value.
        self._updateFromFS()

        if not kw.has_key('args'):
            kw['args'] = args
        bound_names['options'] = kw

        try:
            response = self.REQUEST.RESPONSE
            if not response.headers.has_key('content-type'):
                response.setHeader('content-type', self.content_type)
        except AttributeError:
            pass

        security=getSecurityManager()
        bound_names['user'] = security.getUser()

        # Retrieve the value from the cache.
        keyset = None
        if self.ZCacheable_isCachingEnabled():
            # Prepare a cache key.
            keyset = {
                      # Why oh why?
                      # All this code is cut and paste
                      # here to make sure that we
                      # dont call _getContext and hence can't cache
                      # Annoying huh?
                      'here': self.aq_parent.getPhysicalPath(),
                      'bound_names': bound_names}
            result = self.ZCacheable_get(keywords=keyset)
            if result is not None:
                # Got a cached value.
                return result

        # Execute the template in a new security context.
        security.addContext(self)
        try:
            result = self.pt_render(extra_context=bound_names)
            if keyset is not None:
                # Store the result in the cache.
                self.ZCacheable_set(result, keywords=keyset)
            return result
        finally:
            security.removeContext(self)

        return result

    # Copy over more methods
    security.declareProtected(FTPAccess, 'manage_FTPget')
    manage_FTPget = ZopePageTemplate.manage_FTPget.im_func

    security.declareProtected(View, 'get_size')
    get_size = ZopePageTemplate.get_size.im_func
    getSize = get_size

    security.declareProtected(ViewManagementScreens, 'PrincipiaSearchSource')
    PrincipiaSearchSource = ZopePageTemplate.PrincipiaSearchSource.im_func

    security.declareProtected(ViewManagementScreens, 'document_src')
    document_src = ZopePageTemplate.document_src.im_func

    pt_getContext = ZopePageTemplate.pt_getContext.im_func

    ZScriptHTML_tryParams = ZopePageTemplate.ZScriptHTML_tryParams.im_func

    source_dot_xml = Src()

setattr(FSPageTemplate, 'source.xml',  FSPageTemplate.source_dot_xml)
setattr(FSPageTemplate, 'source.html', FSPageTemplate.source_dot_xml)
Globals.InitializeClass(FSPageTemplate)

registerFileExtension('pt', FSPageTemplate)
registerFileExtension('zpt', FSPageTemplate)
registerFileExtension('html', FSPageTemplate)
registerFileExtension('htm', FSPageTemplate)
registerMetaType('Page Template', FSPageTemplate)

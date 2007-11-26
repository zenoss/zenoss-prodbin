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
""" Customizable image objects that come from the filesystem.

$Id: FSFile.py 68537 2006-06-09 13:40:32Z efge $
"""

import codecs
import Globals
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from OFS.Cache import Cacheable
from OFS.Image import File
try:
    from zope.contenttype import guess_content_type
except ImportError:
    # BBB: for Zope < 2.10
    try:
        from zope.app.content_types import guess_content_type
    except ImportError:
        # BBB: for Zope < 2.9
        from OFS.content_types import guess_content_type

from DirectoryView import registerFileExtension
from DirectoryView import registerMetaType
from FSObject import FSObject
from permissions import FTPAccess
from permissions import View
from permissions import ViewManagementScreens
from utils import _dtmldir
from utils import _setCacheHeaders, _ViewEmulator
from utils import expandpath, _FSCacheHeaders, _checkConditionalGET


class FSFile(FSObject):
    """FSFiles act like images but are not directly
    modifiable from the management interface."""
    # Note that OFS.Image.File is not a base class because it is mutable.

    meta_type = 'Filesystem File'

    manage_options=(
        {'label':'Customize', 'action':'manage_main'},
        ) + Cacheable.manage_options

    security = ClassSecurityInfo()
    security.declareObjectProtected(View)

    def __init__(self, id, filepath, fullname=None, properties=None):
        id = fullname or id # Use the whole filename.
        FSObject.__init__(self, id, filepath, fullname, properties)

    security.declareProtected(ViewManagementScreens, 'manage_main')
    manage_main = Globals.DTMLFile('custfile', _dtmldir)
    content_type = 'unknown/unknown'

    def _createZODBClone(self):
        return File(self.getId(), '', self._readFile(1))

    def _get_content_type(self, file, body, id, content_type=None):
        # Consult self.content_type first, this is either
        # the default (unknown/unknown) or it got a value from a
        # .metadata file
        default_type = 'unknown/unknown'
        if getattr(self, 'content_type', default_type) != default_type:
            return self.content_type

        # Next, look at file headers
        headers=getattr(file, 'headers', None)
        if headers and headers.has_key('content-type'):
            content_type=headers['content-type']
        else:
            # Last resort: Use the (imperfect) content type guessing
            # mechanism from OFS.Image, which ultimately uses the
            # Python mimetypes module.
            if not isinstance(body, basestring):
                body = body.data
            content_type, enc=guess_content_type(
                getattr(file, 'filename',id), body, content_type)
            if (enc is None
                and (content_type.startswith('text/') or
                     content_type.startswith('application/'))
                and body.startswith(codecs.BOM_UTF8)):
                content_type += '; charset=utf-8'

        return content_type

    def _readFile(self, reparse):
        fp = expandpath(self._filepath)
        file = open(fp, 'rb')
        try: data = file.read()
        finally: file.close()
        if reparse or self.content_type == 'unknown/unknown':
            self.ZCacheable_invalidate()
            self.content_type=self._get_content_type(file, data, self.id)
        return data

    #### The following is mainly taken from OFS/File.py ###

    def __str__(self):
        self._updateFromFS()
        return str( self._readFile( 0 ) )

    def modified(self):
        return self.getModTime()

    security.declareProtected(View, 'index_html')
    def index_html(self, REQUEST, RESPONSE):
        """
        The default view of the contents of a File or Image.

        Returns the contents of the file or image.  Also, sets the
        Content-Type HTTP header to the objects content type.
        """
        self._updateFromFS()
        view = _ViewEmulator().__of__(self)

        # If we have a conditional get, set status 304 and return
        # no content
        if _checkConditionalGET(view, extra_context={}):
            return ''

        RESPONSE.setHeader('Content-Type', self.content_type)

        # old-style If-Modified-Since header handling.
        if self._setOldCacheHeaders():
            # Make sure the CachingPolicyManager gets a go as well
            _setCacheHeaders(view, extra_context={})
            return ''

        data = self._readFile(0)
        data_len = len(data)
        RESPONSE.setHeader('Content-Length', data_len)

        #There are 2 Cache Managers which can be in play....
        #need to decide which to use to determine where the cache headers
        #are decided on.
        if self.ZCacheable_getManager() is not None:
            self.ZCacheable_set(None)
        else:
            _setCacheHeaders(view, extra_context={})
        return data

    def _setOldCacheHeaders(self):
        # return False to disable this simple caching behaviour
        return _FSCacheHeaders(self)

    security.declareProtected(View, 'getContentType')
    def getContentType(self):
        """Get the content type of a file or image.

        Returns the content type (MIME type) of a file or image.
        """
        self._updateFromFS()
        return self.content_type

    security.declareProtected(FTPAccess, 'manage_FTPget')
    manage_FTPget = index_html

Globals.InitializeClass(FSFile)

registerFileExtension('doc', FSFile)
registerFileExtension('pdf', FSFile)
registerFileExtension('swf', FSFile)
registerFileExtension('jar', FSFile)
registerFileExtension('cab', FSFile)
registerFileExtension('ico', FSFile)
registerFileExtension('js', FSFile)
registerFileExtension('css', FSFile)
registerMetaType('File', FSFile)

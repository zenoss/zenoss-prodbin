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

$Id: FSImage.py 37972 2005-08-16 20:54:10Z jens $
"""

import Globals
from DateTime import DateTime
from AccessControl import ClassSecurityInfo
from webdav.common import rfc1123_date
from OFS.Cache import Cacheable
from OFS.Image import Image, getImageInfo

from permissions import FTPAccess
from permissions import View
from permissions import ViewManagementScreens
from DirectoryView import registerFileExtension
from DirectoryView import registerMetaType
from FSObject import FSObject
from utils import _dtmldir
from utils import _setCacheHeaders, _ViewEmulator
from utils import expandpath


class FSImage(FSObject):
    """FSImages act like images but are not directly
    modifiable from the management interface."""
    # Note that OFS.Image.Image is not a base class because it is mutable.

    meta_type = 'Filesystem Image'

    _data = None

    manage_options=(
        {'label':'Customize', 'action':'manage_main'},
        ) + Cacheable.manage_options

    security = ClassSecurityInfo()
    security.declareObjectProtected(View)

    def __init__(self, id, filepath, fullname=None, properties=None):
        id = fullname or id # Use the whole filename.
        FSObject.__init__(self, id, filepath, fullname, properties)

    security.declareProtected(ViewManagementScreens, 'manage_main')
    manage_main = Globals.DTMLFile('custimage', _dtmldir)
    content_type = 'unknown/unknown'

    def _createZODBClone(self):
        return Image(self.getId(), '', self._readFile(1))

    def _readFile(self, reparse):
        fp = expandpath(self._filepath)
        file = open(fp, 'rb')
        try:
            data = self._data = file.read()
        finally:
            file.close()
        if reparse or self.content_type == 'unknown/unknown':
            self.ZCacheable_invalidate()
            ct, width, height = getImageInfo( data )
            self.content_type = ct
            self.width = width
            self.height = height
        return data

    #### The following is mainly taken from OFS/Image.py ###

    __str__ = Image.__str__.im_func

    _image_tag = Image.tag.im_func
    security.declareProtected(View, 'tag')
    def tag(self, *args, **kw):
        # Hook into an opportunity to reload metadata.
        self._updateFromFS()
        return self._image_tag(*args, **kw)

    security.declareProtected(View, 'index_html')
    def index_html(self, REQUEST, RESPONSE):
        """
        The default view of the contents of a File or Image.

        Returns the contents of the file or image.  Also, sets the
        Content-Type HTTP header to the objects content type.
        """
        self._updateFromFS()
        data = self._data
        data_len = len(data)
        last_mod = self._file_mod_time
        status = 200
        # HTTP If-Modified-Since header handling.
        header = REQUEST.get_header('If-Modified-Since', None)
        if header is not None:
            header = header.split(';')[0]
            # Some proxies seem to send invalid date strings for this
            # header. If the date string is not valid, we ignore it
            # rather than raise an error to be generally consistent
            # with common servers such as Apache (which can usually
            # understand the screwy date string as a lucky side effect
            # of the way they parse it).
            try:
                mod_since = long(DateTime(header).timeTime())
            except:
                mod_since = None

            if mod_since is not None:
                if last_mod > 0 and last_mod <= mod_since:
                    status = 304
                    data = ''

        #Last-Modified will get stomped on by a cache policy it there is
        #one set....
        RESPONSE.setStatus(status)
        RESPONSE.setHeader('Last-Modified', rfc1123_date(last_mod))
        RESPONSE.setHeader('Content-Type', self.content_type)

        if status != 304:
            # Avoid setting content-length for a 304. See RFC 2616.
            # Zope might still, for better or for worse, set a
            # content-length header with value "0". 
            RESPONSE.setHeader('Content-Length', data_len)

        #There are 2 Cache Managers which can be in play....
        #need to decide which to use to determine where the cache headers
        #are decided on.
        if self.ZCacheable_getManager() is not None:
            self.ZCacheable_set(None)
        else:
            _setCacheHeaders(_ViewEmulator().__of__(self), extra_context={})
        return data

    security.declareProtected(View, 'getContentType')
    def getContentType(self):
        """Get the content type of a file or image.

        Returns the content type (MIME type) of a file or image.
        """
        self._updateFromFS()
        return self.content_type

    security.declareProtected(View, 'get_size')
    def get_size( self ):
        """
            Return the size of the image.
        """
        self._updateFromFS()
        return self._data and len( self._data ) or 0

    security.declareProtected(FTPAccess, 'manage_FTPget')
    manage_FTPget = index_html

Globals.InitializeClass(FSImage)

registerFileExtension('gif', FSImage)
registerFileExtension('jpg', FSImage)
registerFileExtension('jpeg', FSImage)
registerFileExtension('png', FSImage)
registerFileExtension('bmp', FSImage)
registerMetaType('Image', FSImage)

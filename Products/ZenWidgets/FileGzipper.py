###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
#   Copyright (c) 2004 Zentinel Systems. All rights reserved.

""" FileGzipper

A monkey patch that enables gzip compression on static files

"""

from Products.CMFCore.utils import _setCacheHeaders, _ViewEmulator
from DateTime import DateTime
from webdav.common import rfc1123_date
from Products.CMFCore.FSFile import FSFile
def index_html(self, REQUEST, RESPONSE):
    """ Modified default view for files to enable
        gzip compression on js and css files.
    """
    self._updateFromFS()
    data = self._readFile(0)
    data_len = len(data)
    last_mod = self._file_mod_time
    status = 200
    # HTTP If-Modified-Since header handling.
    header=REQUEST.get_header('If-Modified-Since', None)
    if header is not None:
        header = header.split(';')[0]
        try:
            mod_since=long(DateTime(header).timeTime())
        except:
            mod_since=None
            
        if mod_since is not None:
            if last_mod > 0 and last_mod <= mod_since:
                status = 304
                data = ''
    RESPONSE.setStatus(status)
    RESPONSE.setHeader('Last-Modified', rfc1123_date(last_mod))
    RESPONSE.setHeader('Content-Type', self.content_type)

    # The key line!
    RESPONSE.enableHTTPCompression(force=1)

    if status != 304:
        RESPONSE.setHeader('Content-Length', data_len)
    if self.ZCacheable_getManager() is not None:
        self.ZCacheable_set(None)
    else:
        _setCacheHeaders(_ViewEmulator().__of__(self), extra_context={})
    return data

FSFile.index_html = index_html

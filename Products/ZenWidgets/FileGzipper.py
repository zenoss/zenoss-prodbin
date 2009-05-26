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

""" FileGzipper

A monkey patch that enables gzip compression on static files

"""

from Products.CMFCore.utils import _setCacheHeaders, _ViewEmulator
from Products.CMFCore.utils import _checkConditionalGET
from DateTime import DateTime
from webdav.common import rfc1123_date
from Products.CMFCore.FSFile import FSFile
from Products.CMFCore.FSImage import FSImage
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

    ###### ZENOSS PATCH #####
    # Patch to ensure a static charset
    if ";" not in self.content_type:
        self.content_type += "; charset=utf-8"
    #########################
    RESPONSE.setHeader('Content-Type', self.content_type)


    # old-style If-Modified-Since header handling.
    if self._setOldCacheHeaders():
        # Make sure the CachingPolicyManager gets a go as well
        _setCacheHeaders(view, extra_context={})
        return ''

    data = self._readFile(0)
    data_len = len(data)
    RESPONSE.setHeader('Content-Length', data_len)

    ###### ZENOSS PATCH #####
    # Patch to use gzip compression
    RESPONSE.enableHTTPCompression(force=1)
    #########################

    #There are 2 Cache Managers which can be in play....
    #need to decide which to use to determine where the cache headers
    #are decided on.
    if self.ZCacheable_getManager() is not None:
        self.ZCacheable_set(None)
    else:
        _setCacheHeaders(view, extra_context={})
    return data

FSFile.index_html = index_html
FSImage.index_html = index_html

###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import base64
import cPickle
import logging
from urllib import urlencode
import urllib2
import zlib

from Products.ZenCallHome.transport import CallHome

POST_CHECKIN_URL = 'http://callhome.zenoss.com/callhome/v1/post'
_URL_TIMEOUT=5

logger = logging.getLogger('zen.callhome')

def direct_post(dmd):
    callhome = CallHome(dmd)
    if not callhome.attempt('directpost'):
        return
    
    payload = callhome.get_payload()
    if not payload:
        logger.warning('Error getting or encrypting payload for direct-post')
        return
    payload = base64.urlsafe_b64encode(payload)
    
    params = urlencode({'enc': payload})
    
    try:
        httpreq = urllib2.urlopen(POST_CHECKIN_URL, params, _URL_TIMEOUT)
        returnPayload = httpreq.read()
    except Exception as e:
        logger.warning('Error retrieving data from callhome server %s', e)
    else:
        callhome.save_return_payload(returnPayload)
    
    return

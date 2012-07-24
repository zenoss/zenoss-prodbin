##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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

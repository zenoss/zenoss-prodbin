##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import cPickle
import logging
import time
from urllib import urlencode
import urllib2

from Products.ZenUtils.Version import Version

VERSION_CHECK_URL = 'http://callhome.zenoss.com/callhome/v1/versioncheck'
_URL_TIMEOUT=5
logger = logging.getLogger('zen.callhome')

def version_check(dmd):
    params = urlencode({'product': dmd.getProductName()})
    try:
        httpreq = urllib2.urlopen(VERSION_CHECK_URL, params, _URL_TIMEOUT)
        returnPayload = cPickle.loads(httpreq.read())
    except Exception as e:
        logger.warning('Error retrieving version from callhome server: %s', e)
    else:
        available = Version.parse('Zenoss ' + returnPayload['latest'])
        version  = available.short()
        dmd.lastVersionCheck = long(time.time())
        if getattr(dmd, 'availableVersion', '') != version:
            dmd.availableVersion = version

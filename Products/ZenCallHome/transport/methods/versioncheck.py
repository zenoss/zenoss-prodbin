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




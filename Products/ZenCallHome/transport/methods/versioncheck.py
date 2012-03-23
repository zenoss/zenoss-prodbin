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
import urllib

from Products.ZenUtils.Version import Version

VERSION_CHECK_URL = 'http://callhome.zenoss.com/callhome/v1/versioncheck'

logger = logging.getLogger('zen.callhome')

def version_check(dmd):
    params = urllib.urlencode({'product': dmd.getProductName()})
    
    try:
        httpreq = urllib.urlopen(VERSION_CHECK_URL, params)
        returnPayload = cPickle.loads(httpreq.read())
    except:
        logger.warning('Error retrieving version from callhome server')
    else:
        dmd.lastVersionCheck = long(time.time())
        available = Version.parse('Zenoss ' + returnPayload['latest'])
        if getattr(dmd, 'availableVersion', '') != available.short():
            dmd.availableVersion = available.short()
    
    return
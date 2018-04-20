##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

_CSE_CONFIG = {
        'vhost': None,
        'virtualroot': None,
        'zing-host': None
    }

def getCSEConf():
    """Return a dictionary containing CSE configuration 
    """
    global _CSE_CONFIG
    if _CSE_CONFIG is not None and not all(_CSE_CONFIG.values()):
        d = {}
        config = getGlobalConfiguration()
        for k in _CSE_CONFIG:
            d[k] = config.get('cse-' + k)
        _CSE_CONFIG = d if all(d.values()) else {}
    return _CSE_CONFIG

def getZenossURI(request):
    # if we aren't running as a cse, get uri from request
    cse_conf = getCSEConf()
    zenoss_uri = "https://"
    if cse_conf and all(cse_conf.values()):
        zenoss_uri += cse_conf['vhost'] + '.' + cse_conf['zing-host'] + cse_conf.get('virtualroot', '/')
    else:
        # HTTP_X_FORWARDED_HOST should handle vhost
        zenoss_uri += request.environ.get("HTTP_X_FORWARDED_HOST") or \
                      request.environ.get("HTTP_HOST")
    return zenoss_uri

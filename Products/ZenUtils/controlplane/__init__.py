##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from .data import *
from .client import *
from servicetree import ServiceTree
from Products.ZenUtils.GlobalConfig import globalConfToDict
import os


def getConnectionSettings(options=None):
    if options is None:
        o = globalConfToDict()
    else:
        o = options
    settings = {
        "host": o.get("controlplane-host"),
        "port": o.get("controlplane-port"),
        "user": o.get("controlplane-user", "zenoss"),
        "password": o.get("controlplane-password", "zenoss"),
        }
    # allow these to be set from the global.conf for development but
    # give preference to the environment variables
    settings["user"] = os.environ.get('CONTROLPLANE_SYSTEM_USER', settings['user'])
    settings["password"] = os.environ.get('CONTROLPLANE_SYSTEM_PASSWORD', settings['password'])
    return settings
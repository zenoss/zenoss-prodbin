##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
IHost* control-plane implementations.
"""

import logging
import os
from zope.interface import implementer

from Products.ZenUtils.GlobalConfig import globalConfToDict

from .client import ControlPlaneClient
from Products.ZenUtils.host import IHostManager
LOG = logging.getLogger("zen.controlplane")


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


@implementer(IHostManager)
class HostLookup(object):
    """
    Query the control-plane for hosts.
    """

    # The class of the Control Plane client
    clientClass = ControlPlaneClient

    def __init__(self):
        settings = getConnectionSettings()
        self._client = self.clientClass(**settings)

    def query(self):
        """
        Returns a sequence of IHost objects.
        """

        # Retrieve hosts according to name and tags.
        result = self._client.queryHosts()
        if not result:
            return ()

        return tuple(result.values())

    def get(self, id, default=None):
        """
        Retrieve the IApplication object of the identified application.
        The default argument is returned if the application doesn't exist.
        """
        host = self._client.getHost(id)
        if not host:
            return default

        return host

__all__ = (
    "HostLookup"
)

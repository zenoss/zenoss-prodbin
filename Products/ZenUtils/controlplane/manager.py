##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
from fnmatch import fnmatch

from zope.interface import implementer

from .interfaces import IControlPlaneClient
from .data import json2ServiceApplication, ServiceApplication
from .data import _app1, _app2, _apps


@implementer(IControlPlaneClient)
class ControlPlaneClient(object):
    """
    """

    def queryServices(self, name="*", **kwargs):
        """
        """
        results = json.loads(_apps, object_hook=json2ServiceApplication)
        return [app for app in results if fnmatch(app.name, name)]

    def getService(self, instanceId):
        """
        """
        # get data from url
        if instanceId == "app-name":
            return json.loads(_app1, object_hook=json2ServiceApplication)
        elif instanceId == "app2-name":
            return json.loads(_app2, object_hook=json2ServiceApplication)
        else:
            return default

    def updateService(self, instance):
        """
        """

    def getServiceLog(self, uri, start=0, end=None):
        """
        """

    def getServiceConfiguration(self, uri):
        """
        """

    def updateServiceConfiguration(self, uri, config):
        """
        """

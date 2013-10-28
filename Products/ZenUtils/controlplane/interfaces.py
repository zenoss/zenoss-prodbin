##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Interface


class IControlPlaneClient(Interface):
    ""
    ""

    def queryServices(**kwargs):
        """
        """

    def getService(instanceId):
        """
        """

    def updateService(instance):
        """
        """

    def getServiceLog(uri, start=0, end=None):
        """
        """

    def getServiceConfiguration(uri):
        """
        """

    def updateServiceConfiguration(uri, config):
        """
        """

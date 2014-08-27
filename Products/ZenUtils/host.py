##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Host related stuff.
"""

from zope.interface import Interface, Attribute

class IHost(Interface):
    """
    For inspecting Zenoss hosts.
    """

    id = Attribute("Unique application identifier")
    name = Attribute("Name of the application")
    poolId = Attribute("Name of the host on which the instance is running")
    ipAddr = Attribute("Brief description of the application's function")
    cores = Attribute("True if the application will run on startup")
    memory = Attribute("Current running state of the application")
    privateNetwork = Attribute("When the application was started")
    createdAt = Attribute("The IApplicationLog object")
    updatedAt = Attribute("The list of application configurations")
    kernelVersion = Attribute("The list of application configurations")
    kernelRelease = Attribute("The list of application configurations")



class IHostManager(Interface):
    """
    For identifying and locating Zenoss hosts.
    """

    def query(self):
        """
        Returns a sequence of IHost objects
        """

    def get(id, default=None):
        """
        Retrieve the IHost object of the identified host.
        The default argument is returned if the host doesn't exist.

        :param string id: The host ID (not its name).
        :param object default: Alternate return value
        """

__all__ = (
    "IHostManager", "IHost"
)

##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Attribute
from Products.Zuul.interfaces import IFacade, IInfo


class IApplicationInfo(IInfo):
    """
    Read-only set of attributes describing a Zenoss application.
    """

    description = Attribute("Brief description of the application's function")
    autostart = Attribute("True if the application will run on startup")
    state = Attribute("Current running state of the application")


class IApplicationLogInfo(IInfo):
    """
    Read-only set of attributes describing a Zenoss application's log.
    """

    lines = Attribute("Sequence containing the entire log")


class IApplicationLog(IFacade):
    """
    Interface for reading an applications's log.
    """

    def last(count):
        """
        Returns a sequence containing the last count lines of the log.

        :rtype IApplicationLogInfo: The log data.
        """


class IApplication(IFacade):
    """
    Interface for controlling and inspecting Zenoss applications.
    """

    name = Attribute("Name of the application")
    description = Attribute("Brief description of the application's function")
    autostart = Attribute("True if the application will run on startup")
    log = Attribute("The IApplicationLog facade")
    config = Attribute("The application configuration object")

    def start():
        """
        Starts the named application.
        """

    def stop():
        """
        Stops the named application.
        """

    def restart(name):
        """
        Restarts the named application.
        """


class IApplicationManager(IFacade):
    """
    Interface for locating Zenoss applications.
    """

    def query(name=None):
        """
        Returns a sequence of IApplication objects.
        """

    def get(id, default=None):
        """
        Retrieve the IApplication object of the identified application.
        The default argument is returned if the application doesn't exist.
        """

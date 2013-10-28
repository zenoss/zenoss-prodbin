##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Attribute, Interface
from Products.Zuul.interfaces import IFacade, IInfo


class IApplicationInfo(IInfo):
    """
    Read-only set of attributes describing a Zenoss application.
    """

    description = Attribute("Brief description of the application's function")
    enabled = Attribute("True if the application will run on startup")
    processId = Attribute("The process ID (pid) of the running application")


class IApplicationLogInfo(IInfo):
    """
    """

    lines = Attribute("Sequence containing the entire log")


class IApplicationLog(IFacade):
    """
    """

    def first(count):
        """
        Returns a sequence containing the first count lines of the log.

        :rtype IApplicationLogInfo: The log data.
        """

    def last(count):
        """
        Returns a sequence containing the last count lines of the log.

        :rtype IApplicationLogInfo: The log data.
        """

    def slice(start, end):
        """
        Returns a sequence of lines from start line to end line in the log.

        :rtype IApplicationLogInfo: The log data.
        """


class IApplication(IFacade):
    """
    """

    name = Attribute("Name of the application")
    description = Attribute("Brief description of the application's function")
    enabled = Attribute("True if the application will run on startup")
    processId = Attribute("The process ID (pid) of the running application")

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

    def getLog(name):
        """
        Retrieves the log of the named application.

        :rtype: An IApplicationLog object.
        """

    def getConfig(name):
        """
        Retrieves the configuration of the named application.

        :rtype: The configuration object.
        """

    def setConfig(name, config):
        """
        Sets the config of the named application.

        :param config: The configuration object.
        """


class IApplicationManager(IFacade):
    """
    Implements management of Zenoss applications.
    """

    def query():
        """
        Returns a sequence of IApplicationInfo objects.
        """

    def get(name):
        """
        Returns the IApplicationInfo object of the named application.
        """

##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from ..form.schema import TextLine, Bool
from ..utils import ZuulMessageFactory as _t
from . import IInfo, IFacade


class IApplicationInfo(IInfo):
    """
    Read-only set of attributes describing a Zenoss application.
    """

    id = TextLine(
        title=_t("ID"),
        description=_t("Identifier of the running service"),
        readonly=True
    )

    description = TextLine(
        title=_t("Description"),
        description=_t("Brief description of the application's function"),
        readonly=True
    )

    autostart = TextLine(
        title=_t("AutoStart"),
        description=_t("True if the application will run on startup"),
        readonly=True
    )

    state = TextLine(
        title=_t("State"),
        description=_t("Current running state of the application"),
        readonly=True
    )

    poolId = TextLine(
        title=_t("Pool ID"),
        description=_t("The resource pool this daemon is running under."),
        readonly=True
    )

    text = TextLine(
        title=_t("Text"), description=_t("Synonym for name."), readonly=True
    )

    qtip = TextLine(
        title=_t("QTip"), description=_t("Synonym for description."),
        readonly=True
    )

    isRestarting = Bool(
        title=_t("Restarting"),
        description=_t("True if the application is restarting."),
        readonly=True
    )

    uptime = TextLine(
        title=_t("Uptime"),
        description=_t("How long the application been running."),
        readonly=True
    )


class IApplicationFacade(IFacade):
    """
    Interface for managing Zenoss applications.
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

    def start(appId):
        """
        Starts the identified application.
        """

    def stop(appId):
        """
        Stops the identified application.
        """

    def restart(appId):
        """
        Restarts the identified application.
        """

__all__ = ("IApplicationFacade", "IApplicationInfo")

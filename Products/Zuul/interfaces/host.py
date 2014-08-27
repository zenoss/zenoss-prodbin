##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from ..form.schema import Text, TextLine, Int
from ..utils import ZuulMessageFactory as _t
from . import IFacade, IInfo


class IHostInfo(IInfo):
    """
    Read-only set of attributes describing a Zenoss application.
    """

    id = TextLine(
        title=_t("ID"),
        description=_t("Identifier of the running service"),
        readonly=True
    )

    name = TextLine(
        title=_t("Name"),
        description=_t("Brief description of the application's function"),
        readonly=True
    )

    poolId = TextLine(
        title=_t("PoolID"),
        description=_t("True if the application will run on startup"),
        readonly=True
    )

    ipAddr = TextLine(
        title=_t("IPAddr"),
        description=_t("Current running state of the application"),
        readonly=True
    )

    cores = Int(
        title=_t("Cores"),
        description=_t("Synonym for name."),
        readonly=True
    )

    memory = Int(
        title=_t("Memory"),
        description=_t("True if the application is restarting."),
        readonly=True
    )

    privateNetwork = TextLine(
        title=_t("Private Network"),
        description=_t("How long the application been running."),
        readonly=True
    )

    createdAt = TextLine(
        title=_t("Created At"),
        description=_t("How long the application been running."),
        readonly=True
    )

    updatedAt = TextLine(
        title=_t("Updated At"),
        description=_t("How long the application been running."),
        readonly=True
    )

    kernelVersion = TextLine(
        title=_t("Kernel Version"),
        description=_t("How long the application been running."),
        readonly=True
    )

    kernelRelease = TextLine(
        title=_t("Kernel Release"),
        description=_t("How long the application been running."),
        readonly=True
    )


class IHostFacade(IFacade):
    """
    Interface for managing Zenoss applications.
    """

    def query(self):
        """
        Returns a sequence of IApplication objects.
        """


__all__ = ("IHostFacade", "IHostInfo")

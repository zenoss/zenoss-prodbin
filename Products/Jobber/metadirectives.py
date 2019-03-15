##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from zope.interface import Interface
from zope.configuration.fields import GlobalObject
from zope.schema import TextLine


class IJob(Interface):
    """Registers a ZenJobs Job class."""

    class_ = GlobalObject(
        title=u"Job Class",
        description=u"The class of the job to register",
    )

    name = TextLine(
        title=u"Name",
        description=u"Optional name of the job",
        required=False,
    )

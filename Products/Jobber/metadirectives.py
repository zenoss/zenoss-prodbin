##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, unicode_literals

import six

from zope.configuration.fields import GlobalObject
from zope.interface import Interface
from zope.schema import TextLine


class IJob(Interface):
    """Registers a ZenJobs Job class."""

    class_ = GlobalObject(
        title=six.u("Job Class"),
        description=six.u("The class of the job to register"),
    )

    name = TextLine(
        title=six.u("Name"),
        description=six.u("Optional name of the job"),
        required=False,
    )


class ICelerySignal(Interface):
    """Registers a Celery signal handler."""

    name = TextLine(
        title=six.u("Name"),
        description=six.u("The signal receiving a handler"),
    )

    handler = TextLine(
        title=six.u("Handler"),
        description=six.u("Classpath to the function handling the signal"),
    )

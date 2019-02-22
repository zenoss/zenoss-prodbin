##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Interface, Attribute


class IAsyncDispatch(Interface):
    """Interface for classes that implement code that can execute jobs
    on hub services.

    The 'routes' attribute should be a sequence of service/method pairs
    the identify the services and methods an IAsyncDispatch implementation
    supports.  E.g.

        routes = (
            ("EventService", "sendEvent"),
            ("EventService", "sendEvents"),
        )

    is what a dispatcher would declare to specify that it handles jobs
    that want to execute the sendEvent and sendEvents methods on the
    EventService service.
    """

    routes = Attribute("Sequence of service-name/method-name pairs.")

    def submit(job):
        """Asynchronously executes the job.

        @param job {ServiceCallJob} job to execute
        @returns {Deferred}
        """

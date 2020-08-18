##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import contextlib
import transaction

from AccessControl.SecurityManagement import (
    getSecurityManager, newSecurityManager, noSecurityManager,
)
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer
from ZODB.transact import transact

from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Products.ZenUtils.Utils import getObjByPath

from ..config import ZenJobs
from ..utils.log import get_task_logger, inject_logger


class DMD(object):
    """Attaches a ZODB dataroot object to the task instance.

    The dataroot object is accessable to the task via the 'dmd' property.
    """

    def __call__(self, *args, **kwargs):
        """Override to attach a zodb root object to the task."""
        # NOTE: work-around for Celery >= 4.0
        # userid = getattr(self.request, "userid", None)
        userid = self.request.headers.get("userid")
        if userid is None:
            userid = getSecurityManager().getUser().getId()
        with zodb(self.app.db, userid, self.log) as dmd:
            self.__dmd = dmd
            try:
                retries = ZenJobs.get("zodb-max-retries", 5)
                f = transact(super(DMD, self).__call__, retries=retries)
                return f(*args, **kwargs)
            finally:
                self.__dmd = None

    @property
    def dmd(self):
        """Return the current dmd instance."""
        return self.__dmd


@contextlib.contextmanager
def zodb(db, userid, log):
    """Return the DMD context via contextmanager protocol.

    :param db: ZODB database connection.
    :param str userid: The ID of the user to authenticate with.
    """
    session = db.open()
    try:
        log.debug("Started ZODB session")
        root = session.root()
        application = _getContext(root["Application"])
        dataroot = getObjByPath(application, "/zport/dmd")
        _login(dataroot, name=userid)
        setDescriptors(dataroot)
        log.info("Authenticated as user %s", userid)
        try:
            yield dataroot
            transaction.commit()
        except:  # noqa
            transaction.abort()
            raise  # reraise the exception
        finally:
            noSecurityManager()
    finally:
        session.close()
        log.debug("Finished ZODB session")


def _getContext(app):
    resp = HTTPResponse(stdout=None)
    env = {
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "REQUEST_METHOD": "GET",
    }
    req = HTTPRequest(None, env, resp)
    return app.__of__(RequestContainer(REQUEST=req))


@inject_logger(log=get_task_logger)
def _login(log, context, name="admin", userfolder=None):
    """Authenticate user and configure credentials."""
    if userfolder is None:
        userfolder = context.getPhysicalRoot().acl_users
    user = userfolder.getUserById(name)
    if user is None:
        log.warn("No user specified with job.  Using the default user")
        return
    if not hasattr(user, "aq_base"):
        user = user.__of__(userfolder)
    newSecurityManager(None, user)
    log.debug("Logged in as user '%s'", user)
    return user

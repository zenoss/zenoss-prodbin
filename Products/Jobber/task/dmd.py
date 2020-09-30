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
import logging
import transaction

from AccessControl.SecurityManagement import (
    newSecurityManager, noSecurityManager,
)
from Products.CMFCore.utils import getToolByName
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Products.ZenUtils.Utils import getObjByPath

from ..config import ZenJobs
from ..utils.log import get_logger, get_task_logger, inject_logger

from .utils import transact, backoff

mlog = get_logger("zen.zenjobs.task.dmd")

# Can't get users when using Auth0 currently, so use zenoss_system.
_default_user = "zenoss_system"


class DMD(object):
    """Attaches a ZODB dataroot object to the task instance.

    The dataroot object is accessable to the task via the 'dmd' property.
    """

    def __call__(self, *args, **kwargs):
        """Override to attach a zodb root object to the task."""
        # NOTE: work-around for Celery >= 4.0
        # userid = getattr(self.request, "userid", None)
        userid = self.request.headers.get("userid")
        with zodb(self.app.db, userid, self.log) as dmd:
            self.__dmd = dmd
            try:
                retries = ZenJobs.get("zodb-max-retries", 5)
                limit = ZenJobs.get("zodb-retry-interval-limit", 30)
                backoff_generator = backoff(limit)
                f = transact(
                    super(DMD, self).__call__, retries, backoff_generator,
                )
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
        mlog.debug("Started ZODB session")
        root = session.root()
        application = _getContext(root["Application"])
        dataroot = getObjByPath(application, "/zport/dmd")
        user = _login(dataroot, userid=userid)
        setDescriptors(dataroot)
        log_mesg = ("Authenticated as user %s", user.getUserName())
        log.info(*log_mesg)
        mlog.debug(*log_mesg)
        try:
            yield dataroot
            # No transaction.commit() because the DMD class defined
            # elsewhere handles commits using the transact decorator.
        except:  # noqa
            transaction.abort()
            raise  # reraise the exception
        finally:
            noSecurityManager()
    finally:
        session.close()
        mlog.debug("Finished ZODB session")


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
def _login(log, context, userid=_default_user):
    """Authenticate user and configure credentials."""
    if userid is None:
        log.warn("No user ID specified with job.")
        userid = _default_user
        log_mesg = ("Using default user '%s' instead.", userid)
        if mlog.isEnabledFor(logging.DEBUG):
            mlog.warn(*log_mesg)

    user = _getUser(context, userid)
    newSecurityManager(None, user)
    mlog.debug("Logged in as user '%s'", user)
    return user


@inject_logger(log=get_task_logger)
def _getUser(log, context, userid):
    root = context.getPhysicalRoot()
    tool = getToolByName(root, "acl_users")

    user = tool.getUserById(userid)
    if user is None:
        # Try a different tool.
        tool = getToolByName(root.zport, "acl_users")
        user = tool.getUserById(userid)

        if user is None:
            log_mesg = ("User '%s' is not a valid user.", userid)
            log.warn(*log_mesg)
            if mlog.isEnabledFor(logging.DEBUG):
                mlog.warn(*log_mesg)
            log_mesg = ("Using default user '%s' instead.", _default_user)
            log.warn(*log_mesg)
            if mlog.isEnabledFor(logging.DEBUG):
                mlog.warn(*log_mesg)
            user = tool.getUserById(_default_user)

    if not hasattr(user, "aq_base"):
        user = user.__of__(tool)

    return user

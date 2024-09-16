##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from twisted.internet import defer

log = logging.getLogger("zen.zentrap.users")


class CreateAllUsers(object):
    """
    Create all users task.
    """

    def __init__(self, app, receiver):
        self._app = app
        self._receiver = receiver

    @defer.inlineCallbacks
    def task(self):
        try:
            service = yield self._app.getRemoteConfigServiceProxy()
            users = yield service.callRemote("createAllUsers")
            self._receiver.create_users(users)
        except Exception:
            log.exception("failed to retrieve trap filters")

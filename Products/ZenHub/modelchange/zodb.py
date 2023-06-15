##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import contextlib
import os

import ZODB.config

from AccessControl.SecurityManagement import (
    newSecurityManager,
    noSecurityManager,
)
from Products.CMFCore.utils import getToolByName
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Products.ZenUtils.GlobalConfig import globalConfToDict
from Products.ZenUtils.Utils import getObjByPath

_zodb_config_template = """
%import relstorage
<zodb>
  cache-size {cachesize}

  <relstorage>
    cache-local-mb 512
    cache-local-object-max {cache-max-object-size}
    keep-history false
    <mysql>
      host   {host}
      port   {port}
      user   {user}
      passwd {password}
      db     {db}
    </mysql>
  </relstorage>
</zodb>
"""

_zodb_connection_defaults = type(
    "_zodb_connection_defaults",
    (object,),
    {
        "host": "localhost",
        "user": "zenoss",
        "password": "zenoss",
        "db": "zodb",
        "port": 3306,
        "cachesize": 1000,
        "cache_max_object_size": 1048576,
    },
)()


def getDB(config_file=None):
    """
    Returns a connection to the ZODB database.

    If specified, the `config_file` should be a file containing the ZODB
    connection configuration in the ZConfig format.

    :param config_file: path to a file containing ZODB connection config
    :type config_file: str | None
    :rtype: :class:`ZODB.DB.DB`
    """
    if config_file and os.path.isfile(config_file):
        url = "file://%s" % config_file
        return ZODB.config.databaseFromURL(url)
    config = _getConfigString()
    return ZODB.config.databaseFromString(config)


def _getConfigString():
    """
    Returns a ZConfig string to connect to ZODB.

    :rtype: str
    """
    values = _getConfigValues()
    return _zodb_config_template.format(**values)


def _getConfigValues():
    """
    Returns the ZODB connection and config parameters.

    :rtype: dict
    """
    gconf = globalConfToDict()
    return {
        "host": gconf.get("zodb-host", _zodb_connection_defaults.host),
        "port": gconf.get("zodb-port", _zodb_connection_defaults.port),
        "user": gconf.get("zodb-user", _zodb_connection_defaults.user),
        "password": gconf.get(
            "zodb-password", _zodb_connection_defaults.password
        ),
        "db": gconf.get("zodb-db", _zodb_connection_defaults.db),
        "cachesize": gconf.get(
            "zodb-cachesize", _zodb_connection_defaults.cachesize
        ),
        "cache-max-object-size": gconf.get(
            "zodb-cache-max-object-size",
            _zodb_connection_defaults.cache_max_object_size,
        ),
    }


@contextlib.contextmanager
def dataroot(session):
    """
    Context manager returning the root Zenoss ZODB object from the session.

    The data root is commonly known as the "dmd" object.

    :param session: An active ZODB connection (session) object.
    :type session: :class:`ZODB.Connection.Connection`
    :rtype: :class:`Products.ZenModel.DataRoot.DataRoot`
    """
    root = session.root()
    application = _getContext(root["Application"])
    dataroot = getObjByPath(application, "/zport/dmd")
    _ = _login(dataroot)
    setDescriptors(dataroot)
    try:
        yield dataroot
    finally:
        noSecurityManager()


def _getContext(app):
    resp = HTTPResponse(stdout=None)
    env = {
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "REQUEST_METHOD": "GET",
    }
    req = HTTPRequest(None, env, resp)
    return app.__of__(RequestContainer(REQUEST=req))


_default_user = "zenoss_system"


def _login(context, userid=_default_user):
    """Authenticate user and configure credentials."""
    if userid is None:
        userid = _default_user

    user = _getUser(context, userid)
    newSecurityManager(None, user)
    return user


def _getUser(context, userid):
    root = context.getPhysicalRoot()
    tool = getToolByName(root, "acl_users")

    user = tool.getUserById(userid)
    if user is None:
        # Try a different tool.
        tool = getToolByName(root.zport, "acl_users")
        user = tool.getUserById(userid)

        if user is None:
            user = tool.getUserById(_default_user)

    if not hasattr(user, "aq_base"):
        user = user.__of__(tool)

    return user

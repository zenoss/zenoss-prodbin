##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import contextlib
import logging
import os

import transaction
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
from Products.ZenUtils.Utils import getObjByPath, zenPath

_log = logging.getLogger("zen.zodb")

_zodb_config_template = """\
%import relstorage
<zodb>
  cache-size {zodb-cachesize}

  <relstorage>
    cache-local-mb {zodb-max-cache-mb}
    cache-local-object-max {zodb-cache-max-object-size}
    keep-history false
    <mysql>
      host   {zodb-host}
      port   {zodb-port}
      user   {zodb-user}
      passwd {zodb-password}
      db     {zodb-db}
    </mysql>
  </relstorage>
</zodb>
"""

_default_config_file = os.path.join(zenPath("etc"), "zodb.conf")
_default_user = "zenoss_system"


class _ZODBConnectionDefaults:
    host = "localhost"
    user = "zenoss"
    password = "zenoss"  # noqa S105
    db = "zodb"
    port = 3306
    cachesize = 1000
    cache_max_object_size = 1048576
    commit_lock_timeout = 30
    max_cache_mb = 512


def add_zodb_arguments(parser):
    """Add ZODB CLI arguments to `parser`."""
    group = parser.add_argument_group("ZODB Options")
    group.add_argument(
        "--zodb-config-file",
        default=_default_config_file,
        help="ZODB connection config file",
    )
    group.add_argument(
        "--zodb-cachesize",
        default=_ZODBConnectionDefaults.cachesize,
        type=int,
        help="Maximum number of objects kept in the cache",
    )
    group.add_argument(
        "--zodb-host",
        default=_ZODBConnectionDefaults.host,
        help="Hostname of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-port",
        type=int,
        default=_ZODBConnectionDefaults.port,
        help="Port of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-user",
        default=_ZODBConnectionDefaults.user,
        help="User of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-password",
        default=_ZODBConnectionDefaults.password,
        help="Password of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-db",
        default=_ZODBConnectionDefaults.db,
        help="Name of database for MySQL object store",
    )
    group.add_argument(
        "--zodb-cache-max-object-size",
        default=_ZODBConnectionDefaults.cache_max_object_size,
        type=int,
        help="Maximum size of an object stored in the cache (bytes)",
    )
    group.add_argument(
        "--zodb-commit-lock-timeout",
        default=_ZODBConnectionDefaults.commit_lock_timeout,
        type=float,
        help=(
            "Specify the number of seconds a database connection will "
            "wait to acquire a database 'commit' lock before failing."
        ),
    )
    group.add_argument(
        "--zodb-max-cache-mb",
        default=_ZODBConnectionDefaults.max_cache_mb,
        type=int,
        help="Maximum size of the cache (megabytes)",
    )


@contextlib.contextmanager
def zodb_from_dict(config, userid=_default_user, log=_log):
    """
    Context manager managing the connection to ZODB.

    The context yields a tuple containing objects of:

        (
            ZODB.DB.DB,
            ZODB.Connection.Connection,
            Products.ZenModel.DataRoot.DataRoot  # aka 'dmd'
        )

    :param config: cotains the ZODB configuration.
    :type config: dict
    :param userid: The name of the user to log into ZODB.  This user is
        defined in Zope/ZODB, not MySQL.
    :type userid: str
    """
    with contextlib.closing(_get_db_from_dict(config, log=log)) as db:
        with zodb(db, userid=userid, log=log) as (connection, dmd):
            yield (db, connection, dmd)

@contextlib.contextmanager
def zodb_from_args(args, userid=_default_user, log=_log):
    """
    Context manager managing the connection to ZODB.

    The context yields a tuple containing objects of:

        (
            ZODB.DB.DB,
            ZODB.Connection.Connection,
            Products.ZenModel.DataRoot.DataRoot  # aka 'dmd'
        )

    :param filepath: Path of the file containing the ZODB configuration.
    :type filepath: str
    :param userid: The name of the user to log into ZODB.  This user is
        defined in Zope/ZODB, not MySQL.
    :type userid: str
    """
    with contextlib.closing(_get_db_from_args(args, log=log)) as db:
        with zodb(db, userid=userid, log=log) as (connection, dmd):
            yield (db, connection, dmd)


@contextlib.contextmanager
def zodb(db, userid=_default_user, log=_log):
    """
    Context manager managing the connection to ZODB.

    The context yields a tuple containing objects of:

        (
            ZODB.Connection.Connection,
            Products.ZenModel.DataRoot.DataRoot  # aka 'dmd'
        )

    @type db: ZODB.DB.DB
    @type userid: str
    @type log: logging.Logger
    """
    try:
        with contextlib.closing(db.open()) as connection:
            log.debug("started ZODB connection")
            try:
                with dataroot(connection, userid=userid, log=log) as dmd:
                    yield (connection, dmd)
            finally:
                transaction.abort()
    finally:
        log.debug("finished ZODB connection")


@contextlib.contextmanager
def dataroot(connection, userid=_default_user, log=_log):
    """
    Context manager returning the root Zenoss ZODB object from the connection.

    The data root is commonly known as the "dmd" object.

    :param connection: An active ZODB connection object.
    :type connection: :class:`ZODB.Connection.Connection`
    :rtype: :class:`Products.ZenModel.DataRoot.DataRoot`
    """
    root = connection.root()
    application = _getContext(root["Application"])
    dataroot = getObjByPath(application, "/zport/dmd")
    _ = _login(dataroot, userid=userid, log=log)
    setDescriptors(dataroot)
    try:
        yield dataroot
    finally:
        noSecurityManager()


def _get_db_from_dict(config, log=_log):
    """
    Returns a connection to the ZODB database.

    if `args.zodb_config_file` is a valid path to a file, it will be used
    to create and configure a ZODB database.  The other zodb related
    arguments are ignored.

    If `args.zodb_config_file` is not a valid path to a file, then a
    ZODB database is created and configured from the other zodb related
    arguments.

    :param args: result from ArgumentParser.parse_args()
    :param filepath: Path of the file containing the ZODB configuration.
    :type filepath: str
    :rtype: :class:`ZODB.DB.DB`
    """
    configfile = config.get("zodb-config-file")
    if configfile and os.path.isfile(configfile):
        log.debug("using ZODB config file  file=%s", configfile)
        url = "file://%s" % configfile
        return ZODB.config.databaseFromURL(url)
    log.debug("using ZODB configuration options")
    return ZODB.config.databaseFromString(_getConfigString(config))


def _get_db_from_args(args, log=_log):
    """
    Returns a connection to the ZODB database.

    if `args.zodb_config_file` is a valid path to a file, it will be used
    to create and configure a ZODB database.  The other zodb related
    arguments are ignored.

    If `args.zodb_config_file` is not a valid path to a file, then a
    ZODB database is created and configured from the other zodb related
    arguments.

    :param args: result from ArgumentParser.parse_args()
    :param filepath: Path of the file containing the ZODB configuration.
    :type filepath: str
    :rtype: :class:`ZODB.DB.DB`
    """
    configfile = args.zodb_config_file
    if configfile and os.path.isfile(configfile):
        log.debug("using ZODB config file  file=%s", configfile)
        url = "file://%s" % configfile
        return ZODB.config.databaseFromURL(url)
    log.debug("using ZODB command-line arguments")
    zodb_config = _getConfigString(
        {
            "zodb-cachesize": args.zodb_cachesize,
            "zodb-max-cache-mb": args.zodb_max_cache_mb,
            "zodb-cache-max-object-size": args.zodb_cache_max_object_size,
            "zodb-host": args.zodb_host,
            "zodb-port": args.zodb_port,
            "zodb-user": args.zodb_user,
            "zodb-password": args.zodb_password,
            "zodb-db": args.zodb_db,
        }
    )
    return ZODB.config.databaseFromString(zodb_config)


def _getConfigString(config):
    """
    Returns a ZConfig string to connect to ZODB.

    :rtype: str
    """
    return _zodb_config_template.format(**config)


def _getContext(app):
    resp = HTTPResponse(stdout=None)
    env = {
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "REQUEST_METHOD": "GET",
    }
    req = HTTPRequest(None, env, resp)
    return app.__of__(RequestContainer(REQUEST=req))


def _login(context, userid=_default_user, log=_log):
    """Authenticate user and configure credentials."""
    if userid is None:
        userid = _default_user

    user = _getUser(context, userid, log=log)
    newSecurityManager(None, user)
    log.debug("authenticated as user '%s'", user.getUserName())
    return user


def _getUser(context, userid, log=_log):
    root = context.getPhysicalRoot()
    tool = getToolByName(root, "acl_users")

    user = tool.getUserById(userid)
    if user is None:
        # Try a different tool.
        tool = getToolByName(root.zport, "acl_users")
        user = tool.getUserById(userid)

        if user is None:
            log.debug("invalid user '%s'", userid)
            log.debug("using default system user")
            user = tool.getUserById(_default_user)

    if not hasattr(user, "aq_base"):
        user = user.__of__(tool)

    return user


__all__ = ("zodb", "zodb_from_dict", "zodb_from_args", "dataroot")

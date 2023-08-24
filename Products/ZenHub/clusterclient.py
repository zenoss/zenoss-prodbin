##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from twisted.internet import defer
from zope.interface import implementer

from .cluster import IClusterCoordinatorClient, NoNodeError


class ClusterCoordinatorClient(object):
    """
    Manages the connection to the cluster coordiator service.
    """

    _remote_service_name = "ClusterCoordinatorService"

    def __init__(self, zenhub):
        """Initialize a ClusterCoordinatorClient instance.

        :param zenhub: A reference to a cluster coordination service
        :type zenhub: twisted.spread.pb.Reference
        """


@implementer(IClusterCoordinatorClient)
class ClusterCoordinatorSession(object):
    """
    An active session to the cluster coordination service.
    """

    def __init__(self, service):
        """Initialize a RemoteClusterClient instance.

        :param zenhub: A reference to a cluster coordination service
        :type zenhub: twisted.spread.pb.Reference
        """
        self.__service = service

    @defer.inlineCallbacks
    def start(self):
        """Activate the connection to the cluster coordination service."""

    @defer.inlineCallbacks
    def create(self, path, value="", ephemeral=False):
        """
        Create a node having the given path and stores the given value.

        If the `ephemeral` argument is set to True, then the node is
        deleted when the client disconnects.

        :param path: Pathname of the node.
        :type path: pathlib2.Path
        :param value: The value to store on the node.
        :type value: Any serializable value.
        :param ephemeral: Set True to delete node when client disconnects.
        :type ephemeral: boolean
        :rtype: None
        :raises NodeExistError: if the node already exists.
        """
        yield self.__service.call("create", path, value, ephemeral=ephemeral)

    @defer.inlineCallbacks
    def exists(self, path):
        """
        Returns True if `path` exists.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :rtype: boolean
        """
        result = yield self.__service.call("exists", path)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def delete(self, path):
        """
        Delete `path`.  This will succeed if `path` doesn't exist.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :rtype: None
        """
        yield self.__service.call("delete", path)

    @defer.inlineCallbacks
    def get(self, path, default=None):
        """
        Return the value stored on `path`.  If `path` doesn't exist or if
        there is no value, the `default` value is returned.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :param default: The alternate return value
        :type default: Any
        :rtype: Any | `default`
        """
        try:
            result = yield self.__service.call("get", path)
            defer.returnValue(result)
        except NoNodeError:
            defer.returnValue(default)

    @defer.inlineCallbacks
    def get_children(self, path):
        """
        Returns the names of the child nodes of `path`.  If there are no
        child nodes, an empty tuple is returned.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :rtype: Tuple[str]
        """
        result = yield self.__service.call("get_children", path)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def set(self, path, value):
        """
        Set the value of a node.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :param value: The new data value.
        :type value: Any serializable value.
        :rtype: None
        :raises NoNodeError: If the node doesn't exist.
        """
        yield self.__service.call("set", path, value)

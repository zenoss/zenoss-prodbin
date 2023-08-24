##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component.interfaces import Interface


class NodeExistsError(Exception):
    """Raised on the attempt to create a node that already exists."""


class NoNodeError(Exception):
    """Raised on the attempt to set a value on a non-existent node."""


class IClusterCoordinatorClient(Interface):
    """
    An interface a client may use to communicate with a cluster
    coordination service.
    """

    def create(path, value="", ephemeral=False):
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
        :raises NodeExistsError: if the node already exists.
        """

    def exists(path):
        """
        Returns True if `path` exists.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :rtype: boolean
        """

    def delete(path):
        """
        Delete `path`.  This will succeed if `path` doesn't exist.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :rtype: None
        """

    def get(path, default=None):
        """
        Return the value stored on `path`.  If `path` doesn't exist or if
        there is no value, the `default` value is returned.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :param default: The alternate return value
        :type default: Any
        :rtype: Any | `default`
        """

    def get_children(path):
        """
        Returns the names of the child nodes of `path`.  If there are no
        child nodes, an empty tuple is returned.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :rtype: Tuple[str]
        """

    def set(path, value):
        """
        Set the value of a node.

        :param path: Pathname of the node
        :type path: pathlib2.Path
        :param value: The new data value.
        :type value: Any serializable value.
        :rtype: None
        :raises NoNodeError: If the node doesn't exist.
        """

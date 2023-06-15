##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from relstorage.storage import RelStorage
from zope.component import adapter
from zope.interface import implementer

from .interfaces import InvalidationPoller


@adapter(RelStorage)
@implementer(InvalidationPoller)
class RelStorageInvalidationPoller(object):
    """
    Wraps a :class:`relstorage.storage.RelStorage` object to provide an
    API to return the latest database invalidations.
    """

    def __init__(self, storage):
        """
        Initialize a PollInvalidations instance.

        :param storage: relstorage storage object
        :type storage: :class:`relstorage.storage.RelStorage`
        """
        self._storage = storage

    def poll(self):
        self._storage.sync()
        return self._storage.poll_invalidations()

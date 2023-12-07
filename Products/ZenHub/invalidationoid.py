##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zope.interface import implementer
from zope.component import adapter

from Products.ZenRelations.PrimaryPathObjectManager import (
    PrimaryPathObjectManager,
)

from .interfaces import IInvalidationOid

log = logging.getLogger("zen.{}".format(__name__.split(".")[-1].lower()))


@adapter(PrimaryPathObjectManager)
@implementer(IInvalidationOid)
class DefaultOidTransform(object):

    def __init__(self, obj):
        self._obj = obj

    def transformOid(self, oid):
        return oid

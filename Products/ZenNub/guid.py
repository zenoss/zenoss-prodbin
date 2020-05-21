##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# This set of adapters implements a minimal version of the GUID manager feature.
# It doesn't store any actual index, or truly provide GUIDs, it just encodes
# the dimensions of the component as base64, which is reversable to get back
# to the dimensions without a need to search.   This should be "good enough"
# for internal use when computing impact relationships, but is not intended to
# be a true UUID implementation.


from zope.interface import implements
from zope.component import adapts
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable, IGlobalIdentifier, IGUIDManager

import json
from base64 import b64encode, b64decode

from .db import get_nub_db

class GlobalIdentifier(object):
    adapts(IGloballyIdentifiable)
    implements(IGlobalIdentifier)

    def __init__(self, context):
        self.context = context

    def getGUID(self):
        return b64encode(json.dumps(self.context.dimensions()))

    def setGUID(self, value):
        pass

    guid = property(getGUID, setGUID)

    def create(self, force=False, update_global_catalog=True):
        return self.guid


class GUIDManager(object):
    implements(IGUIDManager)

    def __init__(self, context):
        self.context = context
        self.db = get_nub_db()

    def getPath(self, guid):
        return guid

    def getObject(self, guid):
        dimensions = json.loads(b64decode(guid))

        return self.db.get_zobject(
            device=dimensions.get('device'),
            component=dimensions.get('component'))

    def setPath(self, guid, path):
        pass

    def setObject(self, guid, object):
        pass

    def remove(self, guid):
        pass

    def register(self, context):
        pass


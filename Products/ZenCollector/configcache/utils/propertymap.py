##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

log = logging.getLogger("zen.configcache.propertymap")


class DevicePropertyMap(object):
    """
    This class accepts a mapping of ZODB paths to a value.

    Users can interrogate the class instance by providing a path and
    expecting the value from the mapping that best matches the given path.

    A 'best match' means the path with the longest match starting from the
    left end of the path.
    """

    @classmethod
    def from_organizer(cls, obj, propname, default, relName="devices"):
        return cls(getPropertyValues(obj, propname, default, relName=relName))

    def __init__(self, values):
        self.__values = tuple((p.split("/")[1:], v) for p, v in values.items())

    def smallest_value(self):
        try:
            return min(self.__values, key=lambda item: item[1])[1]
        except ValueError:
            return None

    def get(self, request_uid):
        # Split the request into its parts
        req_parts = request_uid.split("/")[1:]
        # Find all the path parts that match the request
        matches = (
            (len(parts), value)
            for parts, value in self.__values
            if req_parts[0 : len(parts)] == parts
        )
        try:
            # Return the value associated with the path parts having
            # the longest match with the request.
            return max(matches, key=lambda item: item[0])[1]
        except ValueError:
            log.exception("failed looking for value")
            # No path parts matched the request.
            return None


def getPropertyValues(obj, propname, default, relName="devices"):
    """
    Returns a mapping of UID -> property-value for the given z-property.
    """
    values = {obj.getPrimaryId(): _getValue(obj, propname, default)}
    values.update(
        (inst.getPrimaryId(), _getValue(inst, propname, default))
        for inst in obj.getSubInstances(relName)
        if inst.isLocal(propname)
    )
    values.update(
        (inst.getPrimaryId(), _getValue(inst, propname, default))
        for inst in obj.getOverriddenObjects(propname)
    )
    if not values or any(v is None for v in values.values()):
        raise RuntimeError(
            "one or more values are None or z-property is missing  "
            "z-property=%s" % (propname,)
        )
    return values


def _getValue(obj, propname, default):
    value = obj.getZ(propname)
    if value is None:
        return default
    return value

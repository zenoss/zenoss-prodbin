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
from zope.interface import implementer

from Products.ZenHub.interfaces import (
    ICollectorEventTransformer,
    TRANSFORM_CONTINUE,
    TRANSFORM_DROP,
)

from .filterspec import countOidLevels

log = logging.getLogger("zen.zentrap.trapfilter")


@implementer(ICollectorEventTransformer)
class TrapFilter(object):
    """
    Interface used to perform filtering of events at the collector.
    This could be used to drop events, transform event content, etc.

    These transformers are run sequentially before a fingerprint is generated
    for the event, so they can set fields which are used by an
    ICollectorEventFingerprintGenerator.

    The priority of the event transformer (the transformers are executed in
    ascending order using the weight of each filter).
    """

    # implements ICollectorEventTransformer
    weight = 1

    def __init__(self, app, spec):
        self._app = app
        self._filterspec = spec
        self._checksum = None
        self._genericTraps = frozenset([0, 1, 2, 3, 4, 5])

    # implements ICollectorEventTransformer
    def transform(self, event):
        """
        Performs any transforms of the specified event at the collector.

        @param event: The event to transform.
        @type event: dict
        @return: Returns TRANSFORM_CONTINUE if this event should be
            forwarded on to the next transformer in the sequence,
            TRANSFORM_STOP if no further transformers should be performed on
            this event, and TRANSFORM_DROP if the event should be dropped.
        @rtype: int
        """
        result = TRANSFORM_CONTINUE
        snmpVersion = event.get("snmpVersion", None)
        if snmpVersion and self._filterspec.defined:
            log.debug("Filtering V%s event %s", snmpVersion, event)
            if self._dropEvent(event):
                log.debug("Dropping event %s", event)
                self._app.counters["eventFilterDroppedCount"] += 1
                result = TRANSFORM_DROP
        else:
            log.debug(
                "filter skipped  snmp-version=%s filters-defined=%s event=%s",
                snmpVersion,
                self._filterspec.defined,
                event,
            )
        return result

    @defer.inlineCallbacks
    def task(self):
        log.debug("retrieving trap filters")
        try:
            service = yield self._app.getRemoteConfigServiceProxy()
            checksum, trapfilters = yield service.callRemote(
                "getTrapFilters", self._checksum
            )
            if checksum is None:
                log.debug("no update on trap filters")
                defer.returnValue(None)

            trapfilters = trapfilters if trapfilters is not None else ""
            events = self._filterspec.update_from_string(trapfilters)
            for event in events:
                self._app.sendEvent(event)

            state = "updated" if self._checksum is not None else "initial"
            log.info("applied %s trap filters", state)
            self._checksum = checksum
        except Exception:
            log.exception("failed to retrieve trap filters")

    def _dropEvent(self, event):
        """
        Determine if an event should be dropped.
        Assumes there are some filters defined, so the default if no matching
        filter is found should be True; i.e. the event did not match any
        existing filter that would include it, so therefore we should drop it.

        @param event: The event to drop or keep.
        @return: Returns True if the event should be dropped;
            False if the event be kept.
        @rtype: boolean
        """
        result = True
        snmpVersion = event.get("snmpVersion", None)

        if snmpVersion == "1":
            result = self._dropV1Event(event)
        elif snmpVersion == "2" or snmpVersion == "3":
            result = self._dropV2Event(event)
        else:
            log.error(
                "Unknown snmp version %s, Dropping event:%r",
                snmpVersion,
                event,
            )

        return result

    def _dropV1Event(self, event):
        genericTrap = event.get("snmpV1GenericTrapType", None)
        if genericTrap is not None and genericTrap in self._genericTraps:
            filterDefinition = self._filterspec.v1traps.get(genericTrap, None)
            if filterDefinition is None:
                return True
            return filterDefinition.action == "exclude"

        if genericTrap != 6:
            log.error(
                "Generic trap '%s' is invalid for V1 event: %s",
                genericTrap,
                event,
            )
            return True

        enterpriseOID = event.get("snmpV1Enterprise", None)
        if enterpriseOID is None:
            log.error(
                "No OID found for enterprise-specific trap for V1 event: %s",
                event,
            )
            return True

        specificTrap = event.get("snmpV1SpecificTrap", None)
        if specificTrap is not None:
            key = "".join([enterpriseOID, "-", str(specificTrap)])
            filterDefinition = self._findFilterByLevel(
                key, self._filterspec.v1filters
            )
            if filterDefinition is not None:
                log.debug(
                    "_dropV1Event: matched definition %s", filterDefinition
                )
                return filterDefinition.action == "exclude"

        key = "".join([enterpriseOID, "-", "*"])
        filterDefinition = self._findFilterByLevel(
            key, self._filterspec.v1filters
        )
        if filterDefinition is not None:
            log.debug("_dropV1Event: matched definition %s", filterDefinition)
            return filterDefinition.action == "exclude"

        filterDefinition = self._findClosestGlobbedFilter(
            enterpriseOID, self._filterspec.v1filters
        )
        if filterDefinition is None:
            log.debug("_dropV1Event: no matching definitions found")
            return True

        log.debug("_dropV1Event: matched definition %s", filterDefinition)
        return filterDefinition.action == "exclude"

    def _dropV2Event(self, event):
        oid = event["oid"]

        # First, try an exact match on the OID
        filterDefinition = self._findFilterByLevel(
            oid, self._filterspec.v2filters
        )
        if filterDefinition is not None:
            log.debug("_dropV2Event: matched definition %s", filterDefinition)
            return filterDefinition.action == "exclude"

        # Convert the OID to its globbed equivalent and try that
        filterDefinition = self._findClosestGlobbedFilter(
            oid, self._filterspec.v2filters
        )
        if filterDefinition is None:
            log.debug("_dropV2Event: no matching definitions found")
            return True

        log.debug("_dropV2Event: matched definition %s", filterDefinition)
        return filterDefinition.action == "exclude"

    def _findClosestGlobbedFilter(self, oid, filtersByLevel):
        filterDefinition = None
        globbedValue = oid
        while globbedValue != "*":
            globbedValue = getNextHigherGlobbedOid(globbedValue)
            filterDefinition = self._findFilterByLevel(
                globbedValue, filtersByLevel
            )
            if filterDefinition:
                break
        return filterDefinition

    def _findFilterByLevel(self, oid, filtersByLevel):
        filterDefinition = None
        oidLevels = countOidLevels(oid)
        filtersByOid = filtersByLevel.get(oidLevels, None)
        if filtersByOid is not None and len(filtersByOid) > 0:
            filterDefinition = filtersByOid.get(oid, None)
        return filterDefinition


def getNextHigherGlobbedOid(oid):
    """
    Gets the next highest globbed OID based on OID hierarchy.
    For instance, given an oid of or "1.2.3.4" or 1.2.3.4.*", return "1.2.3.*".

    @return: The next highest globbed OID up to just "*"
    @rtype: string
    """
    dotIndex = oid.rfind(".")
    if dotIndex != -1 and oid[dotIndex:] == ".*":
        dotIndex = oid.rfind(".", 0, dotIndex)

    if dotIndex < 1 or dotIndex == len(oid) - 1:
        nextGlobbedOID = "*"
    else:
        nextGlobbedOID = "".join([oid[0:dotIndex], ".*"])
    return nextGlobbedOID

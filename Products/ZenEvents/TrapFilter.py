##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """zentrap

Filters SNMP traps.
"""

import sys
import logging
import os.path
import re

import zope.interface
import zope.component

from zope.interface import implements

from Products.ZenCollector.interfaces import ICollector, IEventService
from Products.ZenHub.interfaces import ICollectorEventTransformer, \
    TRANSFORM_CONTINUE, \
    TRANSFORM_DROP
from Products.ZenUtils.Utils import unused, zenPath

log = logging.getLogger("zen.zentrap")

def countOidLevels(oid):
    """
    @return: The number of levels in an OID
    @rtype: int
    """
    return oid.count(".") + 1 if oid else 0

def getNextHigherGlobbedOid(oid):
    """
    Gets the next highest globbed OID based on OID hierarchy.
    For instance, given an oid of or "1.2.3.4" or 1.2.3.4.*", return "1.2.3.*".

    @return: The next highest globbed OID up to just "*"
    @rtype: string
    """
    dotIndex = oid.rfind(".")
    if dotIndex != -1 and oid[dotIndex:] == ".*":
        dotIndex = oid.rfind('.', 0, dotIndex)

    if dotIndex < 1 or dotIndex == len(oid)-1:
        nextGlobbedOID = "*"
    else:
        nextGlobbedOID = ''.join([oid[0:dotIndex], ".*"])
    return nextGlobbedOID

class BaseFilterDefinition(object):
    def __init__(self, lineNumber=None, action=None, collectorRegex=None):
        self.lineNumber =  lineNumber
        self.action = action
        self.collectorRegex = collectorRegex

class GenericTrapFilterDefinition(BaseFilterDefinition):
    def __init__(self, lineNumber=None, action=None, genericTrap=None, collectorRegex=None):
        BaseFilterDefinition.__init__(self, lineNumber, action, collectorRegex)
        self.genericTrap = genericTrap

    def __eq__(self, other):
        if isinstance(other, GenericTrapFilterDefinition):
            return self.genericTrap == other.genericTrap
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.genericTrap)

class OIDBasedFilterDefinition(BaseFilterDefinition):
    def __init__(self, lineNumber=None, action=None, oid=None, collectorRegex=None):
        BaseFilterDefinition.__init__(self, lineNumber, action, collectorRegex)
        self.oid = oid

    def levels(self):
        return countOidLevels(self.oid)

    def __eq__(self, other):
        if isinstance(other, OIDBasedFilterDefinition):
            return self.oid == other.oid
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.oid)

class V1FilterDefinition(OIDBasedFilterDefinition):
    def __init__(self, lineNumber=None, action=None, oid=None, collectorRegex=None):
        OIDBasedFilterDefinition.__init__(self, lineNumber, action, oid, collectorRegex)
        self.specificTrap = None

class V2FilterDefinition(OIDBasedFilterDefinition):
    def __init__(self, lineNumber=None, action=None, oid=None, collectorRegex=None):
        OIDBasedFilterDefinition.__init__(self, lineNumber, action, oid, collectorRegex)

class TrapFilter(object):
    implements(ICollectorEventTransformer)
    """
    Interface used to perform filtering of events at the collector. This could be
    used to drop events, transform event content, etc.

    These transformers are run sequentially before a fingerprint is generated for
    the event, so they can set fields which are used by an ICollectorEventFingerprintGenerator.

    The priority of the event transformer (the transformers are executed in
    ascending order using the weight of each filter).
    """
    weight = 1
    def __init__(self):
        self._daemon = None
        self._eventService = None

        self._genericTraps = frozenset([0, 1, 2, 3, 4, 5])

        self._initialized = False
        self._resetFilters()

    def _resetFilters(self):
        # Map of SNMP V1 Generic Trap filters where key is the generic trap number and
        # value is a GenericTrapFilterDefinition
        self._v1Traps = dict()

        # Map of SNMP V1 enterprise-specific traps where key is the count of levels in an OID, and
        # value is a map of unique V1FilterDefinition objects for that number of OID levels.
        # The map of V1FilterDefinition objects is keyed by "OID[-specificTrap]"
        self._v1Filters = dict()

        # Map of SNMP V2 enterprise-specific traps where key is the count of levels in an OID, and
        # value is a map of unique V2FilterDefinition objects for that number of OID levels.
        # The map of V2FilterDefinition objects is keyed by OID
        self._v2Filters = dict()
        self._filtersDefined = False

    def _parseFilterDefinition(self, line, lineNumber):
        """
           Parse an SNMP filter definition of the format:
            [COLLECTOR REGEX] include|exclude v1|v2 <version-specific options>

        @param line: The filter definition to parse
        @type line: string
        @param lineNumber: The line number of the filter defintion within the file
        @type line: int
        @return: Returns None on success, or an error message on failure
        @rtype: string
        """
        tokens = line.split()
        if len(tokens) < 3:
            return "Incomplete filter definition"
            
        if re.search('include|exclude', tokens[0], re.IGNORECASE):
            collectorRegex = ".*"
            action = tokens[0].lower()
            snmpVersion = tokens[1].lower()
            remainingTokens = tokens[2:]
        else:
            collectorRegex = tokens[0]
            action = tokens[1].lower()
            snmpVersion = tokens[2].lower()
            remainingTokens = tokens[3:]
        if action != "include" and action != "exclude":
            return "Invalid action '%s'; the only valid actions are 'include' or 'exclude'" % tokens[0]
        elif snmpVersion != "v1" and snmpVersion != "v2":
            return "Invalid SNMP version '%s'; the only valid versions are 'v1' or 'v2'" % tokens[1]

        # Do not parse if CollectorRegex does not match collector name
        try:
            if not re.search(collectorRegex, self._daemon.options.monitor):
                return
        except Exception as ex:
            # TODO send error event as well
            log.error('Could not compile collector expression %r on line %d', collectorRegex, lineNumber)
            return

        if snmpVersion == "v1":
            return self._parseV1FilterDefinition(lineNumber, action, remainingTokens, collectorRegex)

        return self._parseV2FilterDefinition(lineNumber, action, remainingTokens, collectorRegex)

    def _parseDefConflictShouldOverride(self, definition, previousDefinition):
        """
        Routine to determine if a TrapFilterDefinition should get overridden.
        Basic overiding rules: 
        1. new collectorRegex is not default value '.*' & prev is
        2. new collectorRegex is not a regex & prev is (exact collector name match)
        """
        if definition.collectorRegex == previousDefinition.collectorRegex:
            return False
        override = False
        isNotRegex = re.compile('^[\w-]+$')
        if definition.collectorRegex != '.*' and previousDefinition.collectorRegex == '.*':
            override = True
        elif isNotRegex.match(definition.collectorRegex) and \
             not isNotRegex.match(previousDefinition.collectorRegex):
            override = True

        if override:
            log.debug(
                'Trap Filter definition conflict override, collector '
                'expression is more exacting. new:%r, prev:%r',
                definition.collectorRegex,
                previousDefinition.collectorRegex)
            return True
        return False

    def _parseV1FilterDefinition(self, lineNumber, action, remainingTokens, collectorRegex):
        """
           Parse an SNMP V1 filter definition.
           Valid definitions have one of the following formats:
                [COLLECTOR REGEX] v1 include|exclude TRAP_TYPE
                [COLLECTOR REGEX] v1 include|exclude GLOBBED_OID
                [COLLECTOR REGEX] v1 include|exclude OID *|SPECIFIC_TRAP
            where
                COLLECTOR REGEX is a regular expression pattern applied against the
                                collector zentrap is running under
                TRAP_TYPE       is a generic trap type in the rage [0-5]
                GLOBBED_OID     is an OID ending with ".*"
                OID             is an valid OID
                SPECIFIC_TRAP   is any specific trap type (any non-negative integer)
            Note that the last two cases are used for enterprise-specific traps (i.e.
            where the generic trap type is 6).

        @param lineNumber: The line number of the filter defintion within the file
        @type line: int
        @param action: The action for this line (include or exclude)
        @type line: string
        @param remainingTokens: The remaining (unparsed) tokens from the filter definition
        @type line: string array
        @return: Returns None on success, or an error message on failure
        @rtype: string
        """
        if len(remainingTokens) > 2:
            return "Too many fields found; at most 4 fields allowed for V1 filters"

        oidOrGenericTrap = ""
        if len(remainingTokens) > 0:
            oidOrGenericTrap = remainingTokens[0].strip(".")
        if len(oidOrGenericTrap) == 1 and oidOrGenericTrap != "*":
            if not oidOrGenericTrap.isdigit() or oidOrGenericTrap not in "012345":
                return "Invalid generic trap '%s'; must be one of 0-5" % (oidOrGenericTrap)

            genericTrapType = oidOrGenericTrap
            genericTrapDefinition = GenericTrapFilterDefinition(lineNumber, action, genericTrapType, collectorRegex)
            if genericTrapType in self._v1Traps:
                previousDefinition = self._v1Traps[genericTrapType]
                if self._parseDefConflictShouldOverride(genericTrapDefinition, previousDefinition) is False:
                    return "Generic trap '%s' conflicts with previous definition at line %d" % (genericTrapType, previousDefinition.lineNumber)
            self._v1Traps[genericTrapType] = genericTrapDefinition
            return None

        result = self._validateOID(oidOrGenericTrap)
        if result:
            return "'%s' is not a valid OID: %s" % (oidOrGenericTrap, result)

        oid = oidOrGenericTrap
        filterDef = V1FilterDefinition(lineNumber, action, oid, collectorRegex)
        if oid.endswith("*"):
            if len(remainingTokens) == 2:
                return "Specific trap not allowed with globbed OID"
        else:
            if len(remainingTokens) == 2:
                filterDef.specificTrap = remainingTokens[1]
                if filterDef.specificTrap != "*" and not filterDef.specificTrap.isdigit():
                    return "Specific trap '%s' invalid; must be non-negative integer" % filterDef.specificTrap
            else:
                return "Missing specific trap number or '*'"

        key = oid
        if filterDef.specificTrap != None:
            key = ''.join([oid, "-", filterDef.specificTrap])

        filtersByLevel = self._v1Filters.get(filterDef.levels(), None)
        if filtersByLevel == None:
            filtersByLevel = {key: filterDef}
            self._v1Filters[filterDef.levels()] = filtersByLevel
        elif key in filtersByLevel:
            previousDefinition = filtersByLevel[key]
            if self._parseDefConflictShouldOverride(filterDef, previousDefinition) is False:
                return "OID '%s' conflicts with previous definition at line %d" % (oid, previousDefinition.lineNumber)
            filtersByLevel[key] = filterDef
        return None

    def _parseV2FilterDefinition(self, lineNumber, action, remainingTokens, collectorRegex):
        """
           Parse an SNMP V2 filter definition
           Valid definitions have one of the following formats:
                [COLLECTOR REGEX] v2 include|exclude OID
                [COLLECTOR REGEX] v2 include|exclude GLOBBED_OID
            where
                COLLECTOR  REGEX is a regular expression pattern applied against the
                                 collector zentrap is running under
                OID              is an valid OID
                GLOBBED_OID      is an OID ending with ".*"

        @param lineNumber: The line number of the filter defintion within the file
        @type line: int
        @param action: The action for this line (include or exclude)
        @type line: string
        @param remainingTokens: The remaining (unparsed) tokens from the filter definition
        @type line: string array
        @return: Returns None on success, or an error message on failure
        @rtype: string
        """
        if len(remainingTokens) > 1:
            return "Too many fields found; at most 3 fields allowed for V2 filters"

        oid = ""
        if len(remainingTokens) > 0:
            oid = remainingTokens[0].strip(".")
        result = self._validateOID(oid)
        if result:
            return "'%s' is not a valid OID: %s" % (oid, result)

        filterDef = V2FilterDefinition(lineNumber, action, oid, collectorRegex)

        filtersByLevel = self._v2Filters.get(filterDef.levels(), None)
        if filtersByLevel == None:
            filtersByLevel = {oid: filterDef}
            self._v2Filters[filterDef.levels()] = filtersByLevel
        elif oid in filtersByLevel:
            previousDefinition = filtersByLevel[oid]
            if self._parseDefConflictShouldOverride(filterDef, previousDefinition) is False:
                return "OID '%s' conflicts with previous definition at line %d" % (oid, previousDefinition.lineNumber)
            filtersByLevel[oid] = filterDef
        return None

    def _validateOID(self, oid):
        """
        Simplistic SNMP OID validation. Not trying to enforce some RFC spec -
        just weed out some of the more obvious mistakes
        """
        if oid == "*":
            return None

        if not oid:
            return "Empty OID is invalid"

        validChars = set('0123456789.*')
        if not all((char in validChars) for char in oid):
            return "Invalid character found; only digits, '.' and '*' allowed"

        globCount = oid.count("*")
        if globCount > 1 or oid.startswith(".*") or (globCount == 1 and not oid.endswith(".*")):
            return "When using '*', only a single '*' at the end of OID is allowed"

        if ".." in oid:
            return "Consecutive '.'s not allowed"

        if "." not in oid:
            return "At least one '.' required"
        return None

    def _readFilters(self, trapFilters):
        for lineNumber, line in enumerate(trapFilters.split('\n')):
            if line.startswith('#'):
                continue

            # skip blank lines
            line = line.strip()
            if not line:
                continue;

            errorMessage = self._parseFilterDefinition(line, lineNumber)
            if errorMessage:
                errorMessage = "Failed to parse filter definition at line %d: %s" % (lineNumber, errorMessage)
                log.warn(errorMessage)
                self._eventService.sendEvent({
                    'device': '127.0.0.1',
                    'eventClass': '/App/Zenoss',
                    'severity': 4,
                    'eventClassKey': '',
                    'summary': 'SNMP Trap Filter processing issue',
                    'component': 'zentrap',
                    'message': errorMessage,
                    'eventKey': "SnmpTrapFilter.{}".format(lineNumber)
                })
                continue
        numFiltersDefined = len(self._v1Traps) + len(self._v1Filters) + len(self._v2Filters)
        self._filtersDefined = 0 != numFiltersDefined
        if self._filtersDefined:
            log.info(
                "Finished reading filter configuration. Lines parsed:%s, "
                "Filters defined:%s [v1Traps:%d, v1Filters:%d, "
                "v2Filters:%d]", lineNumber, numFiltersDefined,
                len(self._v1Traps), len(self._v1Filters), len(self._v2Filters))
        else:
            log.warn("No zentrap filters defined.")

    def initialize(self, trapFilters):
        self._daemon = zope.component.getUtility(ICollector)
        self._eventService = zope.component.queryUtility(IEventService)
        self._initialized = True

    def updateFilter(self, trapFilters):
        if trapFilters != None:
            self._readFilters(trapFilters)

    def transform(self, event):
        """
        Performs any transforms of the specified event at the collector.

        @param event: The event to transform.
        @type event: dict
        @return: Returns TRANSFORM_CONTINUE if this event should be forwarded on
                 to the next transformer in the sequence, TRANSFORM_STOP if no
                 further transformers should be performed on this event, and
                 TRANSFORM_DROP if the event should be dropped.
        @rtype: int
        """
        result = TRANSFORM_CONTINUE
        snmpVersion = event.get('snmpVersion', None)
        if snmpVersion and self._filtersDefined:
            log.debug("Filtering V%s event %s", snmpVersion, event)
            if self._dropEvent(event):
                log.debug("Dropping event %s", event)
                self._daemon.counters['eventFilterDroppedCount'] += 1
                self._daemon.counters["eventCount"] -= 1
                result = TRANSFORM_DROP
        else:
            log.debug("Skipping filter for event=%s, filtersDefined=%s",
                      event, self._filtersDefined)
        return result

    def _dropEvent(self, event):
        """
        Determine if an event should be dropped. Assumes there are some filters defined, so the
        default if no matching filter is found should be True; i.e. the event did not match any
        existing filter that would include it, so therefore we should drop it.

        @param event: The event to drop or keep.
        @return: Returns True if the event should be dropped; False if the event be kept.
        @rtype: boolean
        """
        result = True
        snmpVersion = event.get('snmpVersion', None)

        if snmpVersion == "1":
            result = self._dropV1Event(event)
        elif snmpVersion == "2":
            result = self._dropV2Event(event)

        return result

    def _dropV1Event(self, event):
        genericTrap = event.get("snmpV1GenericTrapType", None)
        if genericTrap != None and genericTrap in self._genericTraps:
            filterDefinition = self._v1Traps.get(genericTrap, None)
            if filterDefinition == None:
                return True
            return filterDefinition.action == "exclude"

        if genericTrap != 6:
            log.error("Generic trap '%s' is invalid for V1 event: %s", genericTrap, event)
            return True

        enterpriseOID = event.get("snmpV1Enterprise", None)
        if enterpriseOID == None:
            log.error("No OID found for enterprise-specific trap for V1 event: %s", event)
            return True

        specificTrap = event.get("snmpV1SpecificTrap", None)
        if specificTrap != None:
            key = ''.join([enterpriseOID, "-", str(specificTrap)])
            filterDefinition = self._findFilterByLevel(key, self._v1Filters)
            if filterDefinition != None:
                log.debug("_dropV1Event: matched definition %s", filterDefinition)
                return filterDefinition.action == "exclude"

        key = ''.join([enterpriseOID, "-", "*"])
        filterDefinition = self._findFilterByLevel(key, self._v1Filters)
        if filterDefinition != None:
            log.debug("_dropV1Event: matched definition %s", filterDefinition)
            return filterDefinition.action == "exclude"

        filterDefinition = self.findClosestGlobbedFilter(enterpriseOID, self._v1Filters)
        if filterDefinition == None:
            log.debug("_dropV1Event: no matching definitions found")
            return True

        log.debug("_dropV1Event: matched definition %s", filterDefinition)
        return filterDefinition.action == "exclude"

    def _dropV2Event(self, event):
        oid = event["oid"]

        # First, try an exact match on the OID
        filterDefinition = self._findFilterByLevel(oid, self._v2Filters)
        if filterDefinition != None:
            log.debug("_dropV2Event: matched definition %s", filterDefinition)
            return filterDefinition.action == "exclude"

        # Convert the OID to its globbed equivalent and try that
        filterDefinition = self.findClosestGlobbedFilter(oid, self._v2Filters)
        if filterDefinition == None:
            log.debug("_dropV2Event: no matching definitions found")
            return True

        log.debug("_dropV2Event: matched definition %s", filterDefinition)
        return filterDefinition.action == "exclude"

    def findClosestGlobbedFilter(self, oid, filtersByLevel):
        filterDefinition = None
        globbedValue = oid
        while globbedValue != "*":
            globbedValue = getNextHigherGlobbedOid(globbedValue)
            filterDefinition = self._findFilterByLevel(globbedValue, filtersByLevel)
            if filterDefinition:
                break
        return filterDefinition

    def _findFilterByLevel(self, oid, filtersByLevel):
        filterDefinition = None
        oidLevels = countOidLevels(oid)
        filtersByOid = filtersByLevel.get(oidLevels, None)
        if filtersByOid != None and len(filtersByOid) > 0:
            filterDefinition = filtersByOid.get(oid, None)
        return filterDefinition


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
    def __init__(self, lineNumber=None, action=None):
        self.lineNumber =  lineNumber
        self.action = action

class GenericTrapFilterDefinition(BaseFilterDefinition):
    def __init__(self, lineNumber=None, action=None, genericTrap=None):
        BaseFilterDefinition.__init__(self, lineNumber, action)
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
    def __init__(self, lineNumber=None, action=None, oid=None):
        BaseFilterDefinition.__init__(self, lineNumber, action)
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
    def __init__(self, lineNumber=None, action=None, oid=None):
        OIDBasedFilterDefinition.__init__(self, lineNumber, action, oid)
        self.specificTrap = None

class V2FilterDefinition(OIDBasedFilterDefinition):
    def __init__(self, lineNumber=None, action=None, oid=None):
        OIDBasedFilterDefinition.__init__(self, lineNumber, action, oid)

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
        self._initialized = False

    def _parseFilterDefinition(self, line, lineNumber):
        """
           Parse an SNMP filter definition of the format:
            include|exclude v1|v2 <version-specific options>

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

        action = tokens[0].lower()
        snmpVersion = tokens[1].lower()
        if action != "include" and action != "exclude":
            return "Invalid action '%s'; the only valid actions are 'include' or 'exclude'" % tokens[0]
        elif snmpVersion != "v1" and snmpVersion != "v2":
            return "Invalid SNMP version '%s'; the only valid versions are 'v1' or 'v2'" % tokens[1]

        if snmpVersion == "v1":
            return self._parseV1FilterDefinition(lineNumber, action, tokens[2:])

        return self._parseV2FilterDefinition(lineNumber, action, tokens[2:])

    def _parseV1FilterDefinition(self, lineNumber, action, remainingTokens):
        """
           Parse an SNMP V1 filter definition.
           Valid definitions have one of the following formats:
                v1 include|exclude TRAP_TYPE
                v1 include|exclude GLOBBED_OID
                v1 include|exclude OID *|SPECIFIC_TRAP
            where
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
            if not oidOrGenericTrap.isdigit() or not oidOrGenericTrap in "012345":
                return "Invalid generic trap '%s'; must be one of 0-5" % (oidOrGenericTrap)

            genericTrapType = oidOrGenericTrap
            genericTrapDefinition = GenericTrapFilterDefinition(lineNumber, action, genericTrapType)
            if genericTrapType in self._v1Traps:
                previousDefinition = self._v1Traps[genericTrapType]
                return "Generic trap '%s' conflicts with previous definition at line %d" % (genericTrapType, previousDefinition.lineNumber)

            self._v1Traps[genericTrapType] = genericTrapDefinition
            return None

        result = self._validateOID(oidOrGenericTrap)
        if result:
            return "'%s' is not a valid OID: %s" % (oidOrGenericTrap, result)

        oid = oidOrGenericTrap
        filterDef = V1FilterDefinition(lineNumber, action, oid)
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
        elif key not in filtersByLevel:
            filtersByLevel[key] = filterDef
        else:
            previousDefinition = filtersByLevel[key]
            return "OID '%s' conflicts with previous definition at line %d" % (oid, previousDefinition.lineNumber)
        return None

    def _parseV2FilterDefinition(self, lineNumber, action, remainingTokens):
        """
           Parse an SNMP V2 filter definition
           Valid definitions have one of the following formats:
                v2 include|exclude OID
                v2 include|exclude GLOBBED_OID
            where
                OID             is an valid OID
                GLOBBED_OID     is an OID ending with ".*"

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

        filterDef = V2FilterDefinition(lineNumber, action, oid)

        filtersByLevel = self._v2Filters.get(filterDef.levels(), None)
        if filtersByLevel == None:
            filtersByLevel = {oid: filterDef}
            self._v2Filters[filterDef.levels()] = filtersByLevel
        elif oid not in filtersByLevel:
            filtersByLevel[oid] = filterDef
        else:
            previousDefinition = filtersByLevel[oid]
            return "OID '%s' conflicts with previous definition at line %d" % (oid, previousDefinition.lineNumber)
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

        if not "." in oid:
            return "At least one '.' required"
        return None

    def _read_filters(self):
        fileName = self._daemon.options.trapFilterFile
        if fileName:
            path = zenPath('etc', fileName)
            if os.path.exists(path):
                with open(path) as filterDefinitionFile:
                    lineNumber = 0
                    for line in filterDefinitionFile:
                        lineNumber += 1
                        if line.startswith('#'):
                            continue

                        # skip blank lines
                        line = line.strip()
                        if not line:
                            continue;

                        errorMessage = self._parseFilterDefinition(line, lineNumber)
                        if errorMessage:
                            log.error("Failed to parse filter definition file %s at line %d: %s", format(path), lineNumber, errorMessage)
                            log.error("Exiting due to invalid filter definition file")
                            sys.exit(1)

                self._filtersDefined = 0 != (len(self._v1Traps) + len(self._v1Filters) + len(self._v2Filters))
                if self._filtersDefined:
                    log.info("Finished reading filter definition file %s", format(path))
                else:
                    log.warn("No zentrap filters found in %s", format(path))
            else:
                log.error("Could find filter definition file %s", format(path))
                log.error("Exiting due to invalid filter definition file")
                sys.exit(1)

    def initialize(self):
        self._daemon = zope.component.getUtility(ICollector)
        self._eventService = zope.component.queryUtility(IEventService)
        self._read_filters()
        self._initialized = True

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
                result = TRANSFORM_DROP
        else:
            log.debug("Skipping filter for event=%s, filtersDefined=%s",
                      event, self._filtersDefined)
        return result

    def _dropEvent(self, event):
        """
        Determine if an event should be dropped. Assumes there are some filters defined, so the
        default if no matching filter is found should be True (i.e. the event did not match any
        existing filter to keep it, so drop it).

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
        genericTrap = event["snmpV1GenericTrapType"]
        if genericTrap in "012345":
            filterDefinition = self._v1Traps.get(genericTrap, None)
            if filterDefinition == None:
                return True
            return filterDefinition.action == "exclude"
        return True

    def _dropV2Event(self, event):
        oid = event["oid"]

        # First, try an exact match on the OID
        filterDefinition = self._findV2Filter(oid)
        if filterDefinition != None:
            log.debug("_dropV2Event: matched definition %s", filterDefinition)
            return filterDefinition.action == "exclude"

        # Convert the OID to its globbed equivalent and try that
        globbedValue = oid
        while globbedValue != "*":
            globbedValue = getNextHigherGlobbedOid(globbedValue)
            filterDefinition = self._findV2Filter(globbedValue)
            if filterDefinition:
                break

        if filterDefinition == None:
            log.debug("_dropV2Event: no matching definitions found")
            return True

        log.debug("_dropV2Event: matched definition %s", filterDefinition)
        return filterDefinition.action == "exclude"

    def _findV2Filter(self, oid):
        filterDefinition = None
        oidLevels = countOidLevels(oid)
        filtersByLevel = self._v2Filters.get(oidLevels, None)
        if filtersByLevel != None and len(filtersByLevel) > 0:
            filterDefinition = filtersByLevel.get(oid, None)
        return filterDefinition

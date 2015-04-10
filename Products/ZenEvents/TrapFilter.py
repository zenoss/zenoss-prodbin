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

from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences, \
    IEventService, \
    IScheduledTask, IStatisticsService
from Products.ZenHub.interfaces import ICollectorEventTransformer, \
    TRANSFORM_CONTINUE, \
    TRANSFORM_DROP
from Products.ZenUtils.Utils import unused, zenPath

log = logging.getLogger("zen.zentrap")


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
        return self.oid.count(".") + 1 if self.oid else 0

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
        self._oids = set()

        # Map of SNMP V1 Generic Trap filters where key is the generic trap number and value is a GenericTrapFilterDefinition
        self._v1Traps = dict()

        # Map of SNMP V1 enterprise-specific traps where key is the count of levels in an OID, and
        # value is a map of unique V1FilterDefinition objects for that number of OID levels. The map of V1FilterDefinition objects is keyed
        # by OID
        self._v1Filters = dict()
        self._v2Filters = dict()
        self._filtersDefined = False
        self._initialized = False

    def _parseFilterDefinition(self, line, lineNumber):
        """
           Parse an SNMP filter definition of the format
           include|exclude v1|v2 <version-specific options

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

        mapByLevel = self._v1Filters.get(filterDef.levels(), None)
        if mapByLevel == None:
            mapByLevel = {oid: filterDef}
            self._v1Filters[filterDef.levels()] = mapByLevel
        elif oid not in mapByLevel:
            mapByLevel[oid] = filterDef
        else:
            previousDefinition = mapByLevel[oid]
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

        mapByLevel = self._v2Filters.get(filterDef.levels(), None)
        if mapByLevel == None:
            mapByLevel = {oid: filterDef}
            self._v2Filters[filterDef.levels()] = mapByLevel
        elif oid not in mapByLevel:
            mapByLevel[oid] = filterDef
        else:
            previousDefinition = mapByLevel[oid]
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
                            log.error("Failed to parse filter file %s at line %d: %s", format(path), lineNumber, errorMessage)
                            log.error("Exiting due to invalid filter definition file")
                            sys.exit(1)

                self._filtersDefined = 0 != (len(self._v1Traps) + len(self._v1Filters) + len(self._v2Filters))
                if self._filtersDefined:
                    log.info("Finished reading filter definition file %s", format(path))
                else:
                    log.warn("No zentrap filters found in %s", format(path))
            else:
                log.warn("Config file %s was not found; no zentrap filters added.", format(path))

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
        trapOid = event.get('oid', None)
        snmpVersion = event.get('snmpVersion', None)
        if trapOid and snmpVersion and self._filtersDefined:
            log.debug("Filtering V%s trap %s", snmpVersion, trapOid)
            if self._dropOid(trapOid):
                log.debug("Dropping trap %s", trapOid)
                result = TRANSFORM_DROP
        else:
            log.debug("Skipping filter for event=%s, filtersDefined=%s",
                      event, self._filtersDefined)
        return result

    def _dropOid(self, oid):
        # FIXME: implement the new filtering logic here
        return False

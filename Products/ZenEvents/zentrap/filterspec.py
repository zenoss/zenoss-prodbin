##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re

log = logging.getLogger("zen.zentrap")


def countOidLevels(oid):
    """
    @return: The number of levels in an OID
    @rtype: int
    """
    return oid.count(".") + 1 if oid else 0


class FilterSpecification(object):
    def __init__(self, monitor):
        self._monitor = monitor

        # Map of SNMP V1 Generic Trap filters where key is the generic trap
        # number and value is a GenericTrapFilterDefinition
        self._v1Traps = {}

        # Map of SNMP V1 enterprise-specific traps where key is the count of
        # levels in an OID, and value is a map of unique V1FilterDefinition
        # objects for that number of OID levels. The map of
        # V1FilterDefinition objects is keyed by "OID[-specificTrap]"
        self._v1Filters = {}

        # Map of SNMP V2 enterprise-specific traps where key is the count of
        # levels in an OID, and value is a map of unique V2FilterDefinition
        # objects for that number of OID levels. The map of
        # V2FilterDefinition objects is keyed by OID
        self._v2Filters = {}
        self._filtersDefined = False

    @property
    def v1traps(self):
        return self._v1Traps

    @property
    def v1filters(self):
        return self._v1Filters

    @property
    def v2filters(self):
        return self._v2Filters

    @property
    def defined(self):
        return self._filtersDefined

    def update_from_string(self, trapFilters, reset=True):
        """
        Returns a sequence of events.
        """
        if reset:
            self._reset()
        events = []
        for lineNumber, line in enumerate(trapFilters.split("\n")):
            if line.startswith("#"):
                continue

            # skip blank lines
            line = line.strip()
            if not line:
                continue

            errorMessage = self._parseFilterDefinition(line, lineNumber)
            if errorMessage:
                errorMessage = (
                    "Failed to parse filter definition at line %d: %s"
                    % (lineNumber, errorMessage)
                )
                log.warn(errorMessage)
                events.append(
                    {
                        "device": "127.0.0.1",
                        "eventClass": "/App/Zenoss",
                        "severity": 4,
                        "eventClassKey": "",
                        "summary": "SNMP Trap Filter processing issue",
                        "component": "zentrap",
                        "message": errorMessage,
                        "eventKey": "SnmpTrapFilter.{}".format(lineNumber),
                    }
                )
                continue
        numFiltersDefined = (
            len(self._v1Traps) + len(self._v1Filters) + len(self._v2Filters)
        )
        self._filtersDefined = 0 != numFiltersDefined
        if self._filtersDefined:
            log.debug(
                "Finished reading filter configuration. Lines parsed:%s, "
                "Filters defined:%s [v1Traps:%d, v1Filters:%d, "
                "v2Filters:%d]",
                lineNumber,
                numFiltersDefined,
                len(self._v1Traps),
                len(self._v1Filters),
                len(self._v2Filters),
            )
        else:
            log.warn("No zentrap filters defined.")
        return events

    def _reset(self):
        self._v1Traps = {}
        self._v1Filters = {}
        self._v2Filters = {}
        self._filtersDefined = False

    def _parseFilterDefinition(self, line, lineNumber):
        """
        Parse an SNMP filter definition of the format:
            [COLLECTOR REGEX] include|exclude v1|v2 <version-specific options>

        @param line: The filter definition to parse
        @type line: string
        @param lineNumber: The line number of the filter defintion within
            the file
        @type line: int
        @return: Returns None on success, or an error message on failure
        @rtype: string
        """
        tokens = line.split()
        if len(tokens) < 3:
            return "Incomplete filter definition"

        if re.search("include|exclude", tokens[0], re.IGNORECASE):
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
            return (
                "Invalid action '%s'; the only valid actions are "
                "'include' or 'exclude'" % tokens[0]
            )
        elif (
            snmpVersion != "v1" and snmpVersion != "v2" and snmpVersion != "v3"
        ):
            return (
                "Invalid SNMP version '%s'; the only valid versions are "
                "'v1' or 'v2' or 'v3'" % tokens[1]
            )

        # Do not parse if CollectorRegex does not match collector name
        try:
            if not re.search(collectorRegex, self._monitor):
                return None
        except Exception:
            errorMessage = (
                "Could not compile collector expression {!r} on "
                "line {}".format(collectorRegex, lineNumber)
            )
            log.error(errorMessage)
            self._app.sendEvent(
                {
                    "device": "127.0.0.1",
                    "eventClass": "/App/Zenoss",
                    "severity": 4,
                    "eventClassKey": "",
                    "summary": "SNMP Trap Filter processing issue",
                    "component": "zentrap",
                    "message": errorMessage,
                    "eventKey": "SnmpTrapFilter.{}".format(lineNumber),
                }
            )
            return errorMessage

        if snmpVersion == "v1":
            return self._parseV1FilterDefinition(
                lineNumber, action, remainingTokens, collectorRegex
            )

        return self._parseV2FilterDefinition(
            lineNumber, action, remainingTokens, collectorRegex
        )

    def _override_definition(self, new, old):
        """
        Routine to determine if a TrapFilterDefinition should be overridden.
        Basic overiding rules:
        1. new collectorRegex is not default value '.*' & prev is
        2. new collectorRegex is not a regex & prev is
            (exact collector name match)
        """
        if new.collectorRegex == old.collectorRegex:
            return False
        override = False
        isNotRegex = re.compile("^[\w-]+$")
        if new.collectorRegex != ".*" and old.collectorRegex == ".*":
            override = True
        elif isNotRegex.match(new.collectorRegex) and not isNotRegex.match(
            old.collectorRegex
        ):
            override = True

        if override:
            log.debug(
                "Trap Filter definition conflict override, collector "
                "expression is more exacting. new:%r, prev:%r",
                new.collectorRegex,
                old.collectorRegex,
            )
            return True
        return False

    def _parseV1FilterDefinition(
        self, lineNumber, action, remainingTokens, collectorRegex
    ):
        """
        Parse an SNMP V1 filter definition.

        Valid definitions have one of the following formats:
            [COLLECTOR REGEX] v1 include|exclude TRAP_TYPE
            [COLLECTOR REGEX] v1 include|exclude GLOBBED_OID
            [COLLECTOR REGEX] v1 include|exclude OID *|SPECIFIC_TRAP
            [COLLECTOR REGEX] v1 include|exclude OID
        where
            COLLECTOR REGEX is a regular expression pattern applied
                against the collector zentrap is running under
            TRAP_TYPE       is a generic trap type in the rage [0-5]
            GLOBBED_OID     is an OID ending with ".*"
            OID             is a valid OID
            SPECIFIC_TRAP   is any specific trap type
                (any non-negative integer)
        Note that the last two cases are used for enterprise-specific
        traps (i.e. where the generic trap type is 6).

        @param lineNumber: The line number of the filter defintion within
            the file
        @type line: int
        @param action: The action for this line (include or exclude)
        @type line: string
        @param remainingTokens: The remaining (unparsed) tokens from the
            filter definition
        @type line: string array
        @return: Returns None on success, or an error message on failure
        @rtype: string
        """
        if len(remainingTokens) > 2:
            return (
                "Too many fields found; at most 4 fields allowed "
                "for V1 filters"
            )

        oidOrGenericTrap = ""
        if len(remainingTokens) > 0:
            oidOrGenericTrap = remainingTokens[0].strip(".")

        if len(oidOrGenericTrap) == 1 and oidOrGenericTrap != "*":
            return self._handle_generic_v1_trap(
                oidOrGenericTrap, lineNumber, action, collectorRegex
            )

        result = self._validateOID(oidOrGenericTrap)
        if result:
            return "'%s' is not a valid OID: %s" % (oidOrGenericTrap, result)

        return self._handle_v1_oid(
            oidOrGenericTrap,
            remainingTokens,
            lineNumber,
            action,
            collectorRegex,
        )

    def _handle_v1_oid(
        self, oid, remainingTokens, lineNumber, action, collectorRegex
    ):
        filterDef = V1FilterDefinition(lineNumber, action, oid, collectorRegex)
        if len(remainingTokens) == 2:
            if oid.endswith("*"):
                return "Specific trap not allowed with globbed OID"
            filterDef.specificTrap = remainingTokens[1]
            if (
                filterDef.specificTrap != "*"
                and not filterDef.specificTrap.isdigit()
            ):
                return (
                    "Specific trap '%s' invalid; must be "
                    "non-negative integer" % filterDef.specificTrap
                )

        key = oid
        if filterDef.specificTrap is not None:
            key = "".join([oid, "-", filterDef.specificTrap])

        filtersByLevel = self._v1Filters.get(filterDef.levels(), None)
        if filtersByLevel is None:
            filtersByLevel = {key: filterDef}
            self._v1Filters[filterDef.levels()] = filtersByLevel
        elif key in filtersByLevel:
            previousDef = filtersByLevel[key]
            if not self._override_definition(filterDef, previousDef):
                return (
                    "OID '%s' conflicts with previous definition at line %d"
                    % (oid, previousDef.lineNumber)
                )
        filtersByLevel[key] = filterDef

    def _handle_generic_v1_trap(
        self, trapType, lineNumber, action, collectorRegex
    ):
        if not trapType.isdigit() or trapType not in "012345":
            return "Invalid generic trap '%s'; must be one of 0-5" % (trapType)

        trapDef = GenericTrapFilterDefinition(
            lineNumber, action, trapType, collectorRegex
        )
        if trapType in self._v1Traps:
            previousDef = self._v1Traps[trapType]
            if not self._override_definition(trapDef, previousDef):
                return (
                    "Generic trap '%s' conflicts with previous "
                    "definition at line %d"
                    % (trapType, previousDef.lineNumber)
                )
        self._v1Traps[trapType] = trapDef

    def _parseV2FilterDefinition(
        self, lineNumber, action, remainingTokens, collectorRegex
    ):
        """
           Parse an SNMP V2 filter definition
           Valid definitions have one of the following formats:
                [COLLECTOR REGEX] v2 include|exclude OID
                [COLLECTOR REGEX] v2 include|exclude GLOBBED_OID
            where
                COLLECTOR  REGEX is a regular expression pattern applied
                    against the collector zentrap is running under
                OID              is an valid OID
                GLOBBED_OID      is an OID ending with ".*"

        @param lineNumber: The line number of the filter defintion within
            the file
        @type line: int
        @param action: The action for this line (include or exclude)
        @type line: string
        @param remainingTokens: The remaining (unparsed) tokens from the
            filter definition
        @type line: string array
        @return: Returns None on success, or an error message on failure
        @rtype: string
        """
        if len(remainingTokens) > 1:
            return (
                "Too many fields found; at most 3 fields allowed "
                "for V2 filters"
            )

        oid = ""
        if len(remainingTokens) > 0:
            oid = remainingTokens[0].strip(".")
        result = self._validateOID(oid)
        if result:
            return "'%s' is not a valid OID: %s" % (oid, result)

        filterDef = V2FilterDefinition(lineNumber, action, oid, collectorRegex)

        filtersByLevel = self._v2Filters.get(filterDef.levels(), None)
        if filtersByLevel is None:
            filtersByLevel = {oid: filterDef}
            self._v2Filters[filterDef.levels()] = filtersByLevel
        elif oid in filtersByLevel:
            previousDef = filtersByLevel[oid]
            if not self._override_definition(filterDef, previousDef):
                return (
                    "OID '%s' conflicts with previous definition at line %d"
                    % (oid, previousDef.lineNumber)
                )
        filtersByLevel[oid] = filterDef

    def _validateOID(self, oid):
        """
        Simplistic SNMP OID validation. Not trying to enforce some RFC spec -
        just weed out some of the more obvious mistakes
        """
        if oid == "*":
            return None

        if not oid:
            return "Empty OID is invalid"

        validChars = set("0123456789.*")
        if not all((char in validChars) for char in oid):
            return "Invalid character found; only digits, '.' and '*' allowed"

        globCount = oid.count("*")
        if (
            globCount > 1
            or oid.startswith(".*")
            or (globCount == 1 and not oid.endswith(".*"))
        ):
            return (
                "When using '*', only a single '*' at the end of "
                "OID is allowed"
            )

        if ".." in oid:
            return "Consecutive '.'s not allowed"

        if "." not in oid:
            return "At least one '.' required"


class BaseFilterDefinition(object):
    def __init__(self, lineNumber=None, action=None, collectorRegex=None):
        self.lineNumber = lineNumber
        self.action = action
        self.collectorRegex = collectorRegex


class GenericTrapFilterDefinition(BaseFilterDefinition):
    def __init__(
        self,
        lineNumber=None,
        action=None,
        genericTrap=None,
        collectorRegex=None,
    ):
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
    def __init__(
        self, lineNumber=None, action=None, oid=None, collectorRegex=None
    ):
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
    def __init__(
        self, lineNumber=None, action=None, oid=None, collectorRegex=None
    ):
        OIDBasedFilterDefinition.__init__(
            self, lineNumber, action, oid, collectorRegex
        )
        self.specificTrap = None


class V2FilterDefinition(OIDBasedFilterDefinition):
    def __init__(
        self, lineNumber=None, action=None, oid=None, collectorRegex=None
    ):
        OIDBasedFilterDefinition.__init__(
            self, lineNumber, action, oid, collectorRegex
        )

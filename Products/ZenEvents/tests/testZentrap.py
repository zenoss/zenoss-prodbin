##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

#runtests -v -t unit Products.ZenEvents -m testZentrap

from Products.ZenEvents.zentrap import BaseFilterDefinition
from Products.ZenEvents.zentrap import OIDBasedFilterDefinition
from Products.ZenEvents.zentrap import GenericTrapFilterDefinition
from Products.ZenEvents.zentrap import TrapFilter
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class OIDBasedFilterDefinitionTest(BaseTestCase):
    def testEQByOID(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        self.assert_(base1 == base2)

    def testEQByOIDFails(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "5.4.3.2.1")
        self.assert_(base1 != base2)

    def testEQByOIDIgnoresAction(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "exclude", "1.2.3.4.5")
        self.assert_(base1 == base2)

    def testEQByOIDFailsForDifferentClass(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = BaseFilterDefinition(0, "include")
        self.assert_(base1 != base2)

    def testHash(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        self.assert_(base1.__hash__() == base2.__hash__())

    def testHashFails(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "include", "5.4.3.2.1")
        self.assert_(base1.__hash__() != base2.__hash__())

    def testHashIgnoresAction(self):
        base1 = OIDBasedFilterDefinition(0, "include", "1.2.3.4.5")
        base2 = OIDBasedFilterDefinition(0, "exclude", "1.2.3.4.5")
        self.assert_(base1.__hash__() == base2.__hash__())

class GenericTrapFilterDefinitionTest(BaseTestCase):
    def testEQByOID(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "1")
        self.assert_(base1 == base2)

    def testEQByOIDFails(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "5")
        self.assert_(base1 != base2)

    def testEQByOIDIgnoresAction(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "exclude", "1")
        self.assert_(base1 == base2)

    def testEQByOIDFailsForDifferentClass(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = BaseFilterDefinition(0, "include")
        self.assert_(base1 != base2)

    def testHash(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "1")
        self.assertEquals(base1.__hash__(), base2.__hash__())

    def testHashFails(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "include", "2")
        self.assertNotEquals(base1.__hash__(), base2.__hash__())

    def testHashIgnoresAction(self):
        base1 = GenericTrapFilterDefinition(0, "include", "1")
        base2 = GenericTrapFilterDefinition(0, "exclude", "1")
        self.assert_(base1.__hash__() == base2.__hash__())


class TrapFilterTest(BaseTestCase):
    def testValidateOIDForGlob(self):
        filter = TrapFilter()
        results = filter._validateOID("*")
        self.assertEquals(results, None)

        results = filter._validateOID("1.2.*")
        self.assertEquals(results, None)

    def testValidateOIDFailsForEmptyString(self):
        filter = TrapFilter()
        results = filter._validateOID("")
        self.assertEquals(results, "Empty OID is invalid")

    def testValidateOIDFailsForSimpleNumber(self):
        filter = TrapFilter()
        results = filter._validateOID("123")
        self.assertEquals(results, "At least one '.' required")

    def testValidateOIDFailsForInvalidChars(self):
        filter = TrapFilter()
        results = filter._validateOID("1.2.3-5.*")
        self.assertEquals(results, "Invalid character found; only digits, '.' and '*' allowed")

    def testValidateOIDFailsForInvalidGlobbing(self):
        filter = TrapFilter()
        results = filter._validateOID("1.2.3.*.5.*")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("1.*.5")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("1.5*")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("*.")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("*.1")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("*.*")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("5*")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

        results = filter._validateOID("*5")
        self.assertEquals(results, "When using '*', only a single '*' at the end of OID is allowed")

    def testParseFilterDefinitionForEmptyLine(self):
        filter = TrapFilter()
        results = filter._parseFilterDefinition("", 99)
        self.assertEquals(results, "Incomplete filter definition")

    def testParseFilterDefinitionForIncompleteLine(self):
        filter = TrapFilter()
        results = filter._parseFilterDefinition("a b", 99)
        self.assertEquals(results, "Incomplete filter definition")

    def testParseFilterDefinitionForInvalidAction(self):
        filter = TrapFilter()
        results = filter._parseFilterDefinition("invalid V1 ignored", 99)
        self.assertEquals(results, "Invalid action 'invalid'; the only valid actions are 'include' or 'exclude'")

    def testParseFilterDefinitionForInvalidVersion(self):
        filter = TrapFilter()
        results = filter._parseFilterDefinition("include V3 ignored", 99)
        self.assertEquals(results, "Invalid SNMP version 'V3'; the only valid versions are 'v1' or 'v2'")

    def testParseFilterDefinitionForInvalidV1Definition(self):
        filter = TrapFilter()
        results = filter._parseFilterDefinition("include V1 .", 99)
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseFilterDefinitionForCaseInsensitiveDefinition(self):
        filter = TrapFilter()
        results = filter._parseFilterDefinition("InClude v1 3", 99)
        self.assertEquals(results, None)

    def testParseFilterDefinitionForValidV1Definition(self):
        filter = TrapFilter()
        results = filter._parseFilterDefinition("include V1 3", 99)
        self.assertEquals(results, None)

    def testParseFilterDefinitionForInvalidV2Definition(self):
        filter = TrapFilter()
        results = filter._parseFilterDefinition("include V2 .", 99)
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseFilterDefinitionForValidV2Definition(self):
        filter = TrapFilter()
        results = filter._parseFilterDefinition("include V2 .1.3.6.1.4.*", 99)
        self.assertEquals(results, None)

    def testParseV1FilterDefinitionForGenericTrap(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", ["0"])
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 1)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 0)

        genericTrapDefinition = filter._v1Traps["0"]
        self.assert_(genericTrapDefinition != None)
        self.assertEquals(genericTrapDefinition.lineNumber, 99)
        self.assertEquals(genericTrapDefinition.action, "include")
        self.assertEquals(genericTrapDefinition.genericTrap, "0")

        # Now add another to make sure we can parse more than one
        results = filter._parseV1FilterDefinition(100, "exclude", ["5"])
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 2)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 0)

        genericTrapDefinition = filter._v1Traps["5"]
        self.assert_(genericTrapDefinition != None)
        self.assertEquals(genericTrapDefinition.lineNumber, 100)
        self.assertEquals(genericTrapDefinition.action, "exclude")
        self.assertEquals(genericTrapDefinition.genericTrap, "5")

    def testParseV1FilterDefinitionEnterpriseSpecificTrap(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", ["1.2.3.*"])
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 1)
        self.assertEquals(len(filter._v2Filters), 0)

        oidLevels = 4
        mapByLevel = filter._v1Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 1)

        filterDef = mapByLevel["1.2.3.*"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 99)
        self.assertEquals(filterDef.action, "include")
        self.assertEquals(filterDef.oid, "1.2.3.*")
        self.assertEquals(filterDef.specificTrap, None)

        # Add another 4-level OID
        results = filter._parseV1FilterDefinition(100, "exclude", ["1.2.3.4", "25"])
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 1)
        self.assertEquals(len(filter._v2Filters), 0)

        mapByLevel = filter._v1Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 2)

        filterDef = mapByLevel["1.2.3.4"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 100)
        self.assertEquals(filterDef.action, "exclude")
        self.assertEquals(filterDef.oid, "1.2.3.4")
        self.assertEquals(filterDef.specificTrap, "25")

        # Add another single-level OID
        results = filter._parseV1FilterDefinition(101, "exclude", ["*"])
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 2)
        self.assertEquals(len(filter._v2Filters), 0)

        oidLevels = 1
        mapByLevel = filter._v1Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 1)

        filterDef = mapByLevel["*"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 101)
        self.assertEquals(filterDef.action, "exclude")
        self.assertEquals(filterDef.oid, "*")
        self.assertEquals(filterDef.specificTrap, None)

    def testParseV1FilterDefinitionFailsForTooManyArgs(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", ["0", "1", "2"])
        self.assertEquals(results, "Too many fields found; at most 4 fields allowed for V1 filters")

    def testParseV1FilterDefinitionFailsForEmptyOID(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", [])
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV1FilterDefinition(99, "include", [""])
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV1FilterDefinition(99, "include", ["."])
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV1FilterDefinition(99, "include", ["..."])
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseV1FilterDefinitionFailsForInvalidOID(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", ["invalidOID"])
        self.assertEquals(results, "'invalidOID' is not a valid OID: Invalid character found; only digits, '.' and '*' allowed")

    def testParseV1FilterDefinitionFailsForInvalidTrap(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", ["a"])
        self.assertEquals(results, "Invalid generic trap 'a'; must be one of 0-5")

        results = filter._parseV1FilterDefinition(99, "include", ["6"])
        self.assertEquals(results, "Invalid generic trap '6'; must be one of 0-5")

    def testParseV1FilterDefinitionFailsForConflictingTrap(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", ["1"])
        self.assertEquals(results, None)

        results = filter._parseV1FilterDefinition(100, "include", ["1"])
        self.assertEquals(results, "Generic trap '1' conflicts with previous definition at line 99")

        # Verify we find a conflict for generic traps where the action differs
        results = filter._parseV1FilterDefinition(100, "exclude", ["1"])
        self.assertEquals(results, "Generic trap '1' conflicts with previous definition at line 99")

    def testParseV1FilterDefinitionFailsForConflictingOID(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5", "2"])
        self.assertEquals(results, None)

        results = filter._parseV1FilterDefinition(100, "include", [".1.3.6.1.4.5", "2"])
        self.assertEquals(results, "OID '1.3.6.1.4.5' conflicts with previous definition at line 99")

        # Verify we find a conflict for OIDs where the action differs
        results = filter._parseV1FilterDefinition(100, "exclude", [".1.3.6.1.4.5", "2"])
        self.assertEquals(results, "OID '1.3.6.1.4.5' conflicts with previous definition at line 99")

        results = filter._parseV1FilterDefinition(101, "include", [".1.3.6.1.4.*"])
        self.assertEquals(results, None)

        # Verify we find a conflict for glob-based OIDs
        results = filter._parseV1FilterDefinition(102, "include", [".1.3.6.1.4.*"])
        self.assertEquals(results, "OID '1.3.6.1.4.*' conflicts with previous definition at line 101")

        # Verify we find a conflict for glob-based OIDs where the action differs
        results = filter._parseV1FilterDefinition(102, "exclude", [".1.3.6.1.4.*"])
        self.assertEquals(results, "OID '1.3.6.1.4.*' conflicts with previous definition at line 101")

    def testParseV1FilterDefinitionFailsForEnterpriseSpecificGlob(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5.*", "23"])
        self.assertEquals(results, "Specific trap not allowed with globbed OID")

    def testParseV1FilterDefinitionFailsForInvalidEnterpriseSpecificTrap(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5", "abc"])
        self.assertEquals(results, "Specific trap 'abc' invalid; must be non-negative integer")

        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5", "-1"])
        self.assertEquals(results, "Specific trap '-1' invalid; must be non-negative integer")

    def testParseV1FilterDefinitionFailsForMissingEnterpriseSpecificTrap(self):
        filter = TrapFilter()
        results = filter._parseV1FilterDefinition(99, "include", [".1.3.6.1.4.5"])
        self.assertEquals(results, "Missing specific trap number or '*'")

    def testParseV2FilterDefinition(self):
        filter = TrapFilter()
        results = filter._parseV2FilterDefinition(99, "include", ["1.2.3.*"])
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 1)

        oidLevels = 4
        mapByLevel = filter._v2Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 1)

        filterDef = mapByLevel["1.2.3.*"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 99)
        self.assertEquals(filterDef.action, "include")
        self.assertEquals(filterDef.oid, "1.2.3.*")

        # Add another 4-level OID
        results = filter._parseV2FilterDefinition(100, "exclude", ["1.2.3.4"])
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 1)

        mapByLevel = filter._v2Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 2)

        filterDef = mapByLevel["1.2.3.4"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 100)
        self.assertEquals(filterDef.action, "exclude")
        self.assertEquals(filterDef.oid, "1.2.3.4")

        # Add another single-level OID
        results = filter._parseV2FilterDefinition(101, "exclude", ["*"])
        self.assertEquals(results, None)
        self.assertEquals(len(filter._v1Traps), 0)
        self.assertEquals(len(filter._v1Filters), 0)
        self.assertEquals(len(filter._v2Filters), 2)

        oidLevels = 1
        mapByLevel = filter._v2Filters[oidLevels]
        self.assert_(mapByLevel != None)
        self.assertEquals(len(mapByLevel), 1)

        filterDef = mapByLevel["*"]
        self.assert_(filterDef != None)
        self.assertEquals(filterDef.lineNumber, 101)
        self.assertEquals(filterDef.action, "exclude")
        self.assertEquals(filterDef.oid, "*")

    def testParseV2FilterDefinitionFailsForTooManyArgs(self):
        filter = TrapFilter()
        results = filter._parseV2FilterDefinition(99, "include", ["0", "1"])
        self.assertEquals(results, "Too many fields found; at most 3 fields allowed for V2 filters")

    def testParseV2FilterDefinitionFailsForEmptyOID(self):
        filter = TrapFilter()
        results = filter._parseV2FilterDefinition(99, "include", [])
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV2FilterDefinition(99, "include", [""])
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV2FilterDefinition(99, "include", ["."])
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

        results = filter._parseV2FilterDefinition(99, "include", ["..."])
        self.assertEquals(results, "'' is not a valid OID: Empty OID is invalid")

    def testParseV2FilterDefinitionFailsForInvalidOID(self):
        filter = TrapFilter()
        results = filter._parseV2FilterDefinition(99, "include", ["invalidOID"])
        self.assertEquals(results, "'invalidOID' is not a valid OID: Invalid character found; only digits, '.' and '*' allowed")

    def testParseV2FilterDefinitionFailsForConflictingOID(self):
        filter = TrapFilter()
        results = filter._parseV2FilterDefinition(99, "include", [".1.3.6.1.4.5"])
        self.assertEquals(results, None)

        results = filter._parseV2FilterDefinition(100, "include", [".1.3.6.1.4.5"])
        self.assertEquals(results, "OID '1.3.6.1.4.5' conflicts with previous definition at line 99")

        # Verify we find a conflict for OIDs where the action differs
        results = filter._parseV2FilterDefinition(100, "exclude", [".1.3.6.1.4.5"])
        self.assertEquals(results, "OID '1.3.6.1.4.5' conflicts with previous definition at line 99")

        results = filter._parseV2FilterDefinition(101, "include", [".1.3.6.1.4.*"])
        self.assertEquals(results, None)

        # Verify we find a conflict for glob-based OIDs
        results = filter._parseV2FilterDefinition(102, "include", [".1.3.6.1.4.*"])
        self.assertEquals(results, "OID '1.3.6.1.4.*' conflicts with previous definition at line 101")

        # Verify we find a conflict for glob-based OIDs where the action differs
        results = filter._parseV2FilterDefinition(102, "exclude", [".1.3.6.1.4.*"])
        self.assertEquals(results, "OID '1.3.6.1.4.*' conflicts with previous definition at line 101")

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(OIDBasedFilterDefinitionTest))
    suite.addTest(makeSuite(GenericTrapFilterDefinitionTest))
    suite.addTest(makeSuite(TrapFilterTest))
    return suite

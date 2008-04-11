###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from ZenModelBaseTest import ZenModelBaseTest

from Products.ZenModel.migrate.Migrate import Migration, Version, Step


class MyTestStep(Step):
    def __init__(self, major, minor, micro):
        self.version = Version(major, minor, micro)
    def __cutover__(self):
        pass
    def __cleanup__(self):
        pass
    def name(self):
        return 'MyTestStep_%s' % self.version.short()

class TestMigrate(ZenModelBaseTest):

    def testGetEarliestAppropriateStepVersion(self):
        m = Migration(noopts=True)
        self.assertEquals(Version(1, 0, 70),
            m.getEarliestAppropriateStepVersion(codeVers=Version(1, 1, 50)))
        self.assertEquals(Version(1, 1, 70),
            m.getEarliestAppropriateStepVersion(codeVers=Version(1, 1, 70)))
        self.assertEquals(Version(1, 1, 70),
            m.getEarliestAppropriateStepVersion(codeVers=Version(1, 1, 99)))
        self.assertEquals(Version(1, 1, 70),
            m.getEarliestAppropriateStepVersion(codeVers=Version(1, 2, 0)))
        m.allSteps.append(MyTestStep(98, 3, 71))
        self.assertEquals(Version(98, 3, 70),
            m.getEarliestAppropriateStepVersion(codeVers=Version(99, 0, 1)))


    def testDetermineSteps(self):
        m = Migration(noopts=True)
        m.allSteps = [  MyTestStep(1, 0, 0), 
                        MyTestStep(1, 1, 0),
                        MyTestStep(1, 2, 0),
                        ]
        m.options.level='1.1.0'
        self.assertEquals(m.determineSteps(), m.allSteps[1:])
        m.options.level = None
        m.options.steps = ['MyTestStep_1.1.0']
        self.assertEquals(m.determineSteps(), m.allSteps[1:2])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestMigrate))
    return suite
        

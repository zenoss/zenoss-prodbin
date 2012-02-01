###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import time

from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenEvents.ActionRuleWindow import ActionRuleWindow as ARW


HOUR = 60
THREE_HOURS = HOUR * 3
HALF_HOUR = HOUR / 2

tests = (

('contains_daily_ST', '2010-03-13 01:00:00', THREE_HOURS, ARW.DAILY, (
    ('starting ST', '2010-03-13 01:00:00', '2010-03-13 01:00:00', '2010-03-13 03:59:59'),
    ('ending ST', '2010-03-13 04:00:00', '2010-03-13 03:59:59', '2010-03-14 01:00:00'),
    ('starting spring-forward', '2010-03-14 01:00:00', '2010-03-14 01:00:00', '2010-03-14 03:59:59'),
    ('ending spring-forward', '2010-03-14 04:00:00', '2010-03-14 03:59:59', '2010-03-15 01:00:00'),
    ('starting DST', '2010-11-06 01:00:00', '2010-11-06 01:00:00', '2010-11-06 03:59:59'),
    ('ending DST', '2010-11-06 04:00:00', '2010-11-06 03:59:59', '2010-11-07 01:00:00'),
    ('starting fall-back', '2010-11-07 01:00:00', '2010-11-07 01:00:00', '2010-11-07 03:59:59'),
    ('ending fall-back', '2010-11-07 04:00:00', '2010-11-07 03:59:59', '2010-11-08 01:00:00'),
)),

('contains_daily_DST', '2010-11-06 01:00:00', THREE_HOURS, ARW.DAILY, (
    ('starting DST', '2010-11-06 01:00:00', '2010-11-06 01:00:00', '2010-11-06 03:59:59'),
    ('ending DST', '2010-11-06 04:00:00', '2010-11-06 03:59:59', '2010-11-07 01:00:00'),
    ('starting fall-back', '2010-11-07 01:00:00', '2010-11-07 01:00:00', '2010-11-07 03:59:59'),
    ('ending fall-back', '2010-11-07 04:00:00', '2010-11-07 03:59:59', '2010-11-08 01:00:00'),
    ('starting ST', '2010-11-08 01:00:00', '2010-11-08 01:00:00', '2010-11-08 03:59:59'),
    ('ending ST', '2010-11-08 04:00:00', '2010-11-08 03:59:59', '2010-11-09 01:00:00'),
    ('starting spring-forward', '2011-03-13 01:00:0', '2011-03-13 01:00:00', '2011-03-13 03:59:59'),
    ('ending spring-forward', '2011-03-13 04:00:00', '2011-03-13 03:59:59', '2011-03-14 01:00:00'),
)),

('contains_weekly_ST', '2010-03-07 01:00:00', THREE_HOURS, ARW.WEEKLY, (
    ('starting ST', '2010-03-07 01:00:00', '2010-03-07 01:00:00', '2010-03-07 03:59:59'),
    ('ending ST', '2010-03-07 04:00:00', '2010-03-07 03:59:59', '2010-03-14 01:00:00'),
    ('starting spring-forward', '2010-03-14 01:00:00', '2010-03-14 01:00:00', '2010-03-14 03:59:59'),
    ('ending spring-forward', '2010-03-14 04:00:00', '2010-03-14 03:59:59', '2010-03-21 01:00:00'),
    ('starting DST', '2010-10-31 01:00:00', '2010-10-31 01:00:00', '2010-10-31 03:59:59'),
    ('ending DST', '2010-10-31 04:00:00', '2010-10-31 03:59:59', '2010-11-07 01:00:00'),
    ('starting fall-back', '2010-11-07 01:00:00', '2010-11-07 01:00:00', '2010-11-07 03:59:59'),
    ('ending fall-back', '2010-11-07 04:00:00', '2010-11-07 03:59:59', '2010-11-14 01:00:00'),
)),

('contains_weekly_DST', '2010-10-31 01:00:00', THREE_HOURS, ARW.WEEKLY, (
    ('starting DST', '2010-10-31 01:00:00', '2010-10-31 01:00:00', '2010-10-31 03:59:59'),
    ('ending DST', '2010-10-31 04:00:00', '2010-10-31 03:59:59', '2010-11-07 01:00:00'),
    ('starting fall-back', '2010-11-07 01:00:00', '2010-11-07 01:00:00', '2010-11-07 03:59:59'),
    ('ending fall-back', '2010-11-07 04:00:00', '2010-11-07 03:59:59', '2010-11-14 01:00:00'),
    ('starting ST', '2010-11-21 01:00:00', '2010-11-21 01:00:00', '2010-11-21 03:59:59'),
    ('ending ST', '2010-11-21 04:00:00', '2010-11-21 03:59:59', '2010-11-28 01:00:00'),
    ('starting spring-forward', '2011-03-13 01:00:0', '2011-03-13 01:00:00', '2011-03-13 03:59:59'),
    ('ending spring-forward', '2011-03-13 04:00:00', '2011-03-13 03:59:59', '2011-03-20 01:00:00'),
)),

('contains_monthly_ST', '2010-02-14 01:00:00', THREE_HOURS, ARW.MONTHLY, (
    ('starting ST', '2010-02-14 01:00:00', '2010-02-14 01:00:00', '2010-02-14 03:59:59'),
    ('ending ST', '2010-02-14 04:00:00', '2010-02-14 03:59:59', '2010-03-14 01:00:00'),
    ('starting spring-forward', '2010-03-14 01:00:00', '2010-03-14 01:00:00', '2010-03-14 03:59:59'),
    ('ending spring-forward', '2010-03-14 04:00:00', '2010-03-14 03:59:59', '2010-04-14 01:00:00'),
    ('starting DST', '2010-04-14 01:00:00', '2010-04-14 01:00:00', '2010-04-14 03:59:59'),
    ('ending DST', '2010-04-14 04:00:00', '2010-04-14 03:59:59', '2010-05-14 01:00:00'),
)),

('contains_monthly_DST', '2010-10-07 01:00:00', THREE_HOURS, ARW.MONTHLY, (
    ('starting DST', '2010-10-07 01:00:00', '2010-10-07 01:00:00', '2010-10-07 03:59:59'),
    ('ending DST', '2010-10-07 04:00:00', '2010-10-07 03:59:59', '2010-11-07 01:00:00'),
    ('starting fall-back', '2010-11-07 01:00:00', '2010-11-07 01:00:00', '2010-11-07 03:59:59'),
    ('ending fall-back', '2010-11-07 04:00:00', '2010-11-07 03:59:59', '2010-12-07 01:00:00'),
    ('starting ST', '2010-12-07 01:00:00', '2010-12-07 01:00:00', '2010-12-07 03:59:59'),
    ('ending ST', '2010-12-07 04:00:00', '2010-12-07 03:59:59', '2011-01-07 01:00:00'),
)),

('contains_weekday_ST', '2010-03-08 01:00:00', THREE_HOURS, ARW.EVERY_WEEKDAY, (
    ('starting ST(Monday)', '2010-03-08 01:00:00', '2010-03-08 01:00:00', '2010-03-08 03:59:59'),
    ('ending ST(Monday)', '2010-03-08 04:00:00', '2010-03-08 03:59:59', '2010-03-09 01:00:00'),
    ('starting ST(Friday)', '2010-03-12 01:00:00', '2010-03-12 01:00:00', '2010-03-12 03:59:59'),
    ('ending ST(Friday)', '2010-03-12 04:00:00', '2010-03-12 03:59:59', '2010-03-15 01:00:00'),
    ('starting DST(Monday)', '2010-03-15 01:00:00', '2010-03-15 01:00:00', '2010-03-15 03:59:59'),
    ('ending DST(Monday)', '2010-03-15 04:00:00', '2010-03-15 03:59:59', '2010-03-16 01:00:00'),
    ('starting DST(Friday)', '2010-03-19 01:00:00', '2010-03-19 01:00:00', '2010-03-19 03:59:59'),
    ('ending DST(Friday)', '2010-03-19 04:00:00', '2010-03-19 03:59:59', '2010-03-22 01:00:00'),
)),

('contains_weekday_DST', '2010-11-01 01:00:00', THREE_HOURS, ARW.EVERY_WEEKDAY, (
    ('starting DST(Monday)', '2010-11-01 01:00:00', '2010-11-01 01:00:00', '2010-11-01 03:59:59'),
    ('ending DST(Monday)', '2010-11-01 04:00:00', '2010-11-01 03:59:59', '2010-11-02 01:00:00'),
    ('starting DST(Friday)', '2010-11-05 01:00:00', '2010-11-05 01:00:00', '2010-11-05 03:59:59'),
    ('ending DST(Friday)', '2010-11-05 04:00:00', '2010-11-05 03:59:59', '2010-11-08 01:00:00'),
    ('starting ST(Monday)', '2010-11-08 01:00:00', '2010-11-08 01:00:00', '2010-11-08 03:59:59'),
    ('ending ST(Monday)', '2010-11-08 04:00:00', '2010-11-08 03:59:59', '2010-11-09 01:00:00'),
    ('starting ST(Friday)', '2010-11-12 01:00:00', '2010-11-12 01:00:00', '2010-11-12 03:59:59'),
    ('ending ST(Friday)', '2010-11-12 04:00:00', '2010-11-12 03:59:59', '2010-11-15 01:00:00'),
)),

)


gt = lambda s: time.mktime(time.strptime(s, '%Y-%m-%d %H:%M:%S'))
tg = lambda t: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))


class TestActionRuleWindow(ZenModelBaseTest):
    def afterSetUp(self):
        super(TestActionRuleWindow, self).afterSetUp()
        self.dmd.ZenUsers.manage_addUser('user1', 'zenoss', ['Manager'])
        self.user = self.dmd.ZenUsers.user1


    def beforeTearDown(self):
        self.dmd.ZenUsers.manage_deleteUsers(['user1'])
        super(TestActionRuleWindow, self).beforeTearDown()


    def testSchedules(self):
        for name, start, duration, repeat, steps in tests:
            self.user.manage_addActionRule(name)
            rule = self.user._getOb(name)
            rule.manage_addActionRuleWindow(name)
            window = rule.windows._getOb(name)
            window.start = gt(start)
            window.duration = duration
            window.repeat = repeat
            window.enabled = True

            for msg, begin, beforeTime, afterTime in steps:
                t = gt(begin)
                nextEvent = tg(window.nextEvent(t))
                self.assertEqual(nextEvent, beforeTime,
                    '%s %s has wrong pre-execution next time. (%s != %s)' % (
                        name, msg, nextEvent, beforeTime))

                window.execute(t)
                nextEvent = tg(window.nextEvent(t))
                self.assertEqual(nextEvent, afterTime,
                    '%s %s has wrong post-execution next time. (%s != %s)' % (
                        name, msg, nextEvent, afterTime))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    #suite.addTest(makeSuite(TestActionRuleWindow))
    suite.addTest(makeSuite(ZenModelBaseTest))
    return suite

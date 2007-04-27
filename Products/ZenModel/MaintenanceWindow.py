###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""MaintenanceWindow

A scheduled period of time during which a window is under maintenance.

$Id:$"""

__version__ = "$Revision: 1.7 $"[11:-2]

DAY_SECONDS = 24*60*60
WEEK_SECONDS = 7*DAY_SECONDS

import time
import Globals

from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils import Time

def lastDayPreviousMonth(seconds):
    parts = list(time.localtime(seconds))
    # use day 1 of this month
    parts[2] = 1
    # and go back DAY_SECONDS
    return time.mktime(parts) - DAY_SECONDS

def addMonth(secs, dayOfMonthHint=0):
    base = list(time.localtime(secs))
    # add a month
    base[1] += 1
    # year wrap
    if base[1] == 13:
        base[0] += 1
        base[1] = 1
    # Check for the case Jan 31 becomes March 3
    # in that case, force it back to Feb 28

    # first, remember the month
    month = base[1]
    if dayOfMonthHint:
        base[2] = dayOfMonthHint
    # normalize
    base = list(time.localtime(time.mktime(base)))
    # if the month changed, walk back to the end of the previous month
    if base[1] != month:
        return lastDayPreviousMonth(time.mktime(base))
    return time.mktime(base)

def minmax(value, minValue, maxValue, label, msgs):
    "add a message to msgs if not minValue <= value <= maxValue"
    if not minValue <= value <= maxValue:
        msgs.append("Bad value for %s: "
                    "must be between %s and %s, inclusive" %
                    (label, minValue, maxValue))

def makeInts(values, msgs):
    result = []
    try:
        for v in values:
            result.append(int(v))
    except ValueError:
        msgs.append("Bad number: " + v)
    return result
    
class MaintenanceWindow(ZenModelRM):
    
    start = None
    started = None
    duration = 60
    repeat = 'Never'
    startProductionState = 300
    stopProductionState = 1000
    enabled = True
    skip = 1
 
    _properties = (
        {'id':'start', 'type':'int', 'mode':'w'},
        {'id':'started', 'type':'int', 'mode':'w'},
        {'id':'duration', 'type':'int', 'mode':'w'},
        {'id':'repeat', 'type':'string', 'mode':'w'},
        {'id':'skip', 'type':'int', 'mode':'w'},
        ) 

    factory_type_information = ( 
        { 
            'immediate_view' : 'maintenanceWindowDetail',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'maintenanceWindowDetail'
                , 'permissions'   : ( Permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )

    backCrumb = 'deviceManagement' 
    #backCrumb = 'deviceOrganizerManage'
    _relations = (
        ("productionState", ToOne(ToManyCont, "Products.ZenModel.MaintenanceWindowable", "maintenanceWindows")),
        )
    
    security = ClassSecurityInfo()


    REPEAT = "Never/Daily/Every Weekday/Weekly/Monthly/First Sunday of the Month".split('/')
    NEVER, DAILY, EVERY_WEEKDAY, WEEKLY, MONTHLY, FSOTM = REPEAT

    def __init__(self, id):
        ZenModelRM.__init__(self, id)
        self.start = time.time()
        self.enabled = False

    def set(self, start, duration, repeat, enabled=True):
        self.start = start
        self.duration = duration
        self.repeat = repeat
        self.enabled = enabled

    def repeatOptions(self):
        "Provide the list of REPEAT options"
        return self.REPEAT

    # Nice methods used by the GUI for presentation purposes
    def niceDuration(self):
        """Return a human readable version of the duration in
        days, hours, minutes"""
        return Time.Duration(self.duration)

    def niceStartDate(self):
        "Return a date in the format use by the calendar javascript"
        return Time.USDate(self.start)

    def niceStartDateTime(self):
        "Return start time as a string with nice sort qualities"
        return Time.LocalDateTime(self.start)

    def niceStartProductionState(self):
        "Return a string version of the startProductionState"
        return self.convertProdState(self.startProductionState)

    def niceStopProductionState(self):
        "Return a string version of the stopProductionState"
        return self.convertProdState(self.stopProductionState)

    def niceStartHour(self):
        return time.localtime(self.start)[3]

    def niceStartMinute(self):
        return time.localtime(self.start)[4]

    security.declareProtected('Change Maintenance Window',
                              'manage_editMaintenanceWindow')
    def manage_editMaintenanceWindow(self,
                                     startDate='',
                                     startHours='',
                                     startMinutes='00',
                                     durationDays='0',
                                     durationHours='00',
                                     durationMinutes='00',
                                     repeat='Never',
                                     startProductionState=1000,
                                     stopProductionState=300,
                                     enabled=True,
                                     skip=1,
                                     REQUEST=None,
                                     **kw):
        "Update the maintenance window from GUI elements"
        msgs = []
        startHours, startMinutes = makeInts((startHours, startMinutes), msgs)
        self.enabled = bool(enabled)
        import re
        try:
            month, day, year = re.split('[^ 0-9]', startDate)
        except ValueError:
            msgs.append("Date needs three number fields")
        minmax(startMinutes, 0, 59, 'minute', msgs)
        minmax(startHours, 0, 59, 'hour', msgs)
        day, month, year = makeInts((day, month, year), msgs)
        minmax(day, 0, 31, 'day', msgs)
        minmax(month, 1, 12, 'month', msgs)
        minmax(year, 2000, 2037, 'year', msgs)
        if not msgs:
            t = time.mktime((year, month, day, startHours, startMinutes,
                             0, 0, 0, -1))
        if not msgs:
            durationDays, durationHours, durationMinutes = \
                makeInts((durationDays, durationHours, durationMinutes), msgs)
        minmax(durationHours, 0, 23, 'hours', msgs)
        minmax(durationMinutes, 0, 59, 'minutes', msgs)
        if not msgs:
            duration = (durationDays * (60*24) +
                        durationHours * 60 +
                        durationMinutes)
            if duration < 1:
                msgs.append('Maintenance Window must be at least 1')
        if msgs:
            if REQUEST:
                if REQUEST.has_key('message'):
                    del REQUEST['message']
                REQUEST['message'] = '; '.join(msgs)
        else:
            self.start = t
            self.duration = duration
            self.repeat = repeat
            self.startProductionState = startProductionState
            self.stopProductionState = stopProductionState
            self.skip = skip
            now = time.time()
            if self.started and self.nextEvent(now) < now:
                self.end()
        return self.callZenScreen(REQUEST)


    def nextEvent(self, now):
        "Return the time of the next begin() or end()"
        if self.started:
            return self.started + self.duration * 60
        # ok, so maybe "now" is a little late: start anything that
        # should have been started by now
        return self.next(now - self.duration * 60 + 1)


    security.declareProtected('View', 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
        "fix up breadCrumbs to add a link back to the Manage tab"
        bc = super(MaintenanceWindow, self).breadCrumbs(terminator)
        url, display = bc[-2]
        url += "/" + self.backCrumb
        bc.insert(-1, (url, 'manage'))
        return bc


    def next(self, now = None):
        """From Unix time_t now value, return next time_t value
        for the window to start, or None"""

        if not self.enabled:
            return None

        if now is None:
            now = time.time()

        if now < self.start:
            return self.start

        if self.repeat == self.NEVER:
            if now > self.start:
                return None
            return self.start

        elif self.repeat == self.DAILY:
            skip = (DAY_SECONDS * self.skip)
            last = self.start + ((now - self.start) // skip * skip)
            return last + skip

        elif self.repeat == self.EVERY_WEEKDAY:
            weeksSince = (now - self.start) // WEEK_SECONDS
            weekdaysSince = weeksSince * 5
            # start at the most recent week-even point from the start
            base = self.start + weeksSince * DAY_SECONDS * 7
            while 1:
                dow = time.localtime(base).tm_wday
                if dow not in (5,6):
                    if base > now and weekdaysSince % self.skip == 0:
                        break
                    weekdaysSince += 1
                base += DAY_SECONDS
            assert base >= now
            return base
            
        elif self.repeat == self.WEEKLY:
            skip = (WEEK_SECONDS * self.skip)
            last = self.start + ((now - self.start) // skip * skip)
            return last + skip

        elif self.repeat == self.MONTHLY:
            months = 0
            m = self.start
            dayOfMonthHint = time.localtime(self.start).tm_mday
            while m < now or months % self.skip:
                m = addMonth(m, dayOfMonthHint)
                months += 1
            return m

        elif self.repeat == self.FSOTM:
            base = list(time.localtime(now))
            # Move time to this year/month
            base[2:6] = time.localtime(self.start)[2:6]
            base = time.mktime(base)
            # creep ahead by days until it's the FSOTM
            # (not the most efficient implementation)
            count = 0
            while 1:
                tm = time.localtime(base)
                if base > now and 1 <= tm.tm_mday <= 7 and tm.tm_wday == 6:
                    count += 1
                    if count % self.skip == 0:
                        break
                base += DAY_SECONDS
            return base
        raise ValueError('bad value for MaintenanceWindow repeat: %r' %self.repeat)

    def target(self):
        return self.productionState().primaryAq()

    def begin(self, now = None):
        "hook for entering the Maintenance Window: call if you override"
        self.target().setProdState(self.startProductionState)
        if not now:
            now = time.time()
        self.started = now


    def end(self):
        "hook for leaving the Maintenance Window: call if you override"
        self.started = None
        self.target().setProdState(self.stopProductionState)


    def execute(self, now = None):
        "Take the next step: either start or stop the Maintenance Window"
        if self.started:
            self.end()
        else:
            self.begin(now)

DeviceMaintenanceWindow = MaintenanceWindow
OrganizerMaintenanceWindow = MaintenanceWindow


if __name__=='__main__':
    m = MaintenanceWindow('tester')
    t = time.mktime( (2006, 1, 29, 10, 45, 12, 6, 29, 0) )
    P = 60*60*2
    m.set(t, P, m.NEVER)
    assert m.next() == None
    m.set(t, P, m.DAILY)
    c = time.mktime( (2006, 1, 30, 10, 45, 12, 6, 29, 0) )
    assert m.next(t + P + 1) == c
    m.set(t, P, m.WEEKLY)
    c = time.mktime( (2006, 2, 5, 10, 45, 12, 6, 36, 0) )
    assert m.next(t + 1) == c
    m.set(t - DAY_SECONDS, P, m.EVERY_WEEKDAY)
    c = time.mktime( (2006, 1, 30, 10, 45, 12, 7, 30, 0) )
    assert m.next(t) == c
    m.set(t, P, m.MONTHLY)
    c = time.mktime( (2006, 2, 28, 10, 45, 12, 0, 0, 0) )
    assert m.next(t+1) == c
    t2 = time.mktime( (2005, 12, 31, 10, 45, 12, 0, 0, 0) )
    m.set(t2, P, m.MONTHLY)
    c = time.mktime( (2006, 1, 31, 10, 45, 12, 0, 0, 0) )
    c2 = time.mktime( (2006, 2, 28, 10, 45, 12, 0, 0, 0) )
    assert m.next(t2+1) == c
    assert m.next(c+1) == c2
    c = time.mktime( (2006, 2, 5, 10, 45, 12, 0, 0, 0) )
    m.set(t, P, m.FSOTM)
    assert m.next(t+1) == c

    # skips
    m.skip = 2
    m.set(t, P, m.DAILY)
    c = time.mktime( (2006, 1, 31, 10, 45, 12, 6, 29, 0) )
    assert m.next(t + 1) == c

    m.set(t, P, m.WEEKLY)
    c = time.mktime( (2006, 2, 12, 10, 45, 12, 6, 36, 0) )
    assert m.next(t + 1) == c

    m.set(t, P, m.MONTHLY)
    c = time.mktime( (2006, 3, 29, 10, 45, 12, 6, 36, 0) )
    assert m.next(t + 1) == c

    m.set(t - DAY_SECONDS * 2, P, m.EVERY_WEEKDAY)
    c = time.mktime( (2006, 1, 31, 10, 45, 12, 7, 30, 0) )
    assert m.next(t + 1) == c

    c = time.mktime( (2006, 3, 5, 10, 45, 12, 0, 0, 0) )
    m.set(t, P, m.FSOTM)
    assert m.next(t+1) == c

    r = {'test':None}
    m.manage_editMaintenanceWindow(
                                     startDate='01/29/2006',
                                     startHours='10',
                                     startMinutes='45',
                                     durationDays='1',
                                     durationHours='1',
                                     durationMinutes='1',
                                     repeat='Weekly',
                                     startProductionState=1000,
                                     stopProductionState=300,
                                     enabled=True,
                                     REQUEST=r)

    if r.has_key('message'):
        print r['message']
    assert not r.has_key('message')
    assert m.start == t - 12
    assert m.duration == 24*60+61
    assert m.repeat == 'Weekly'
    assert m.startProductionState == 1000
    assert m.stopProductionState == 300


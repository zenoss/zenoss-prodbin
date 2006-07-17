#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""MaintenanceWindow

A scheduled period of time during which a window is under maintenance.

$Id:$"""

__version__ = "$Revision: 1.7 $"[11:-2]

DAY_SECONDS = 24*60*60

import time

from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from DateTime import DateTime
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *

def daytime(daySeconds, timeSeconds):
    base = list(time.localtime(daySeconds))
    base[3:6] = time.localtime(timeSeconds)[3:6]
    return time.mktime(base)

def lastDayPreviousMonth(seconds):
    parts = list(time.localtime(seconds))
    # use day 1 of this month
    parts[2] = 1
    # and go back DAY_SECONDS
    return time.mktime(parts) - DAY_SECONDS

def addMonth(secs):
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
    # normalize
    base = list(time.localtime(time.mktime(base)))
    # if the month changed, walk back to the end of the previous month
    if base[1] != month:
        return lastDayPreviousMonth(time.mktime(base))
    return time.mktime(base)
    
class MaintenanceWindow(ZenModelRM):
    
    start = None
    started = None
    duration = 60
    repeat = 'Never'
    startProductionState = 300
    stopProductionState = 1000

    _properties = (
        {'id':'start', 'type':'date', 'mode':'w'},
        {'id':'started', 'type':'date', 'mode':'w'},
        {'id':'duration', 'type':'int', 'mode':'w'},
        {'id':'repeat', 'type':'string', 'mode':'w'},
        ) 

    _relations = (
        ("device", ToOne(ToManyCont, "Device", "maintenanceWindows")),
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
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )
    
    
    
    security = ClassSecurityInfo()


    REPEAT = "Never/Daily/Every Weekday/Weekly/Monthly/First Sunday of the Month".split('/')
    NEVER, DAILY, EVERY_WEEKDAY, WEEKLY, MONTHLY, FSOTM = range(len(REPEAT))

    def __init__(self, id):
        ZenModelRM.__init__(self, id)
        self.start = DateTime(time.time() + DAY_SECONDS)

    def set(self, start, duration, repeat):
        self.start = start
        self.duration = duration
        self.repeat = repeat

    def repeatOptions(self):
        return self.REPEAT

    def niceDuration(self):
        duration = self.duration
        if duration < 60:
            return ":%02d" % duration
        if duration < 24*60:
            return "%02d:%02d" % (duration / 60, duration % 60)
        return "%d days %02d:%02d" % (duration // (60 * 24),
                                      (duration // 60) % 24,
                                      duration % 60)

    def niceStartProductionState(self):
        return self.convertProdState(self.startProductionState)

    def niceStopProductionState(self):
        return self.convertProdState(self.stopProductionState)


    security.declareProtected('Change Maintenance Window',
                              'manage_editMaintenanceWindow')
    def manage_editMaintenanceWindow(self, *args, **kw):
        "Update the maintenance window"

    security.declareProtected('View', 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
        "fix up breadCrumbs to go back to the Manage tab"
        bc = super(MaintenanceWindow, self).breadCrumbs(terminator)
        url, display = bc[-2]
        url += "/deviceManagement"
        bc[-2] = (url, display)
        return bc


    def next(self, now = None):
        "from Unix time_t now value, return next time_t value for the window, or None"
        if now is None:
            now = time.time()
        if self.repeat == self.NEVER:
            if now > self.start:
                return None
            return self.start

        elif self.repeat == self.DAILY:
            base = daytime(now, self.start)
            if base < now:
                base += DAY_SECONDS
                assert base > now
            return base

        elif self.repeat == self.EVERY_WEEKDAY:
            base = daytime(now, self.start)
            while base < now or time.localtime(base).tm_wday in (5,6):
                base += DAY_SECONDS
            assert base > now
            return base
            
        elif self.repeat == self.WEEKLY:
            base = daytime(now, self.start)
            dow = time.localtime(self.start).tm_wday
            while base < now or time.localtime(base).tm_wday != dow:
                base += DAY_SECONDS
            return base

        elif self.repeat == self.MONTHLY:
            base = list(time.localtime(now))
            base[2:6] = time.localtime(self.start)[2:6]
            secs = time.mktime(base)
            if secs < now:
                return addMonth(secs)
            return secs

        elif self.repeat == self.FSOTM:
            base = list(time.localtime(now))
            # Move time to this year/month
            base[2:6] = time.localtime(self.start)[2:6]
            base = time.mktime(base)
            # creep ahead by days until it's the FSOTM
            # (not the most efficient implementation)
            while 1:
                tm = time.localtime(base)
                if base > now and 1 <= tm.tm_mday <= 7 and tm.tm_wday == 6:
                    break
                base += DAY_SECONDS
            return base
        raise ValueError('bad value for MaintenanceWindow repeat')

if __name__=='__main__':
    m = MaintenanceWindow('tester')
    t = time.mktime( (2006, 1, 29, 10, 45, 12, 6, 29, 0) )
    m.set(t, 60*60*2, m.NEVER)
    assert m.next() == None
    m.set(t, 60*60*2, m.DAILY)
    c = time.mktime( (2006, 1, 30, 10, 45, 12, 0, 30, 0) )
    assert m.next(t + 1) == c
    m.set(t, 60*60*2, m.WEEKLY)
    c = time.mktime( (2006, 2, 5, 10, 45, 12, 6, 36, 0) )
    assert m.next(t + 1) == c
    m.set(t - DAY_SECONDS, 60*60*2, m.EVERY_WEEKDAY)
    c = time.mktime( (2006, 1, 30, 10, 45, 12, 7, 30, 0) )
    assert m.next(t) == c
    m.set(t, 60*60*2, m.MONTHLY)
    c = time.mktime( (2006, 2, 28, 10, 45, 12, 0, 0, 0) )
    assert m.next(t+1) == c
    t2 = time.mktime( (2005, 12, 31, 10, 45, 12, 0, 0, 0) )
    m.set(t2, 60*60*2, m.MONTHLY)
    c = time.mktime( (2006, 1, 31, 10, 45, 12, 0, 0, 0) )
    c2 = time.mktime( (2006, 2, 28, 10, 45, 12, 0, 0, 0) )
    assert m.next(t2+1) == c
    assert m.next(c+1) == c2
    c = time.mktime( (2006, 2, 5, 10, 45, 12, 0, 0, 0) )
    m.set(t, 60*60*2, m.FSOTM)
    assert m.next(t+1) == c

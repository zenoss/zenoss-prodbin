##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """MaintenanceWindow

A scheduled period of time during which a window is under maintenance.

"""

DAY_SECONDS = 24*60*60
WEEK_SECONDS = 7*DAY_SECONDS

import time
import logging
log = logging.getLogger("zen.MaintenanceWindows")

import Globals

from AccessControl import ClassSecurityInfo
from zope.interface import implements
from ZenossSecurity import *
from ZenModelRM import ZenModelRM
from Products.ZenModel.interfaces import IIndexed
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils import Time
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit

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


RETURN_TO_ORIG_PROD_STATE = -99

class MaintenanceWindow(ZenModelRM):

    implements(IIndexed)
    meta_type = 'Maintenance Window'

    default_catalog = 'maintenanceWindowSearch'

    name = None
    start = None
    started = None
    duration = 60
    repeat = 'Never'
    startProductionState = 300
    stopProductionState = RETURN_TO_ORIG_PROD_STATE
    enabled = True
    skip = 1

    _properties = (
        {'id':'name', 'type':'string', 'mode':'w'},
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
                , 'permissions'   : (ZEN_MAINTENANCE_WINDOW_VIEW, )
                },
            )
         },
        )

    backCrumb = 'deviceManagement'
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

    def displayName(self):
        if self.name is not None: return self.name
        else: return self.id

    def repeatOptions(self):
        "Provide the list of REPEAT options"
        return self.REPEAT

    def getTargetId(self):
        return self.target().id

    # Nice methods used by the GUI for presentation purposes
    def niceDuration(self):
        """Return a human readable version of the duration in
        days, hours, minutes"""
        return Time.Duration(self.duration*60)

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
        return 'Original'

    def niceStartHour(self):
        return time.localtime(self.start)[3]

    def niceStartMinute(self):
        return time.localtime(self.start)[4]

    security.declareProtected(ZEN_MAINTENANCE_WINDOW_EDIT,
                              'manage_editMaintenanceWindow')
    def manage_editMaintenanceWindow(self,
                                     startDate='',
                                     startHours='',
                                     startMinutes='00',
                                     durationDays='0',
                                     durationHours='00',
                                     durationMinutes='00',
                                     repeat='Never',
                                     startProductionState=300,
                                     stopProductionState=RETURN_TO_ORIG_PROD_STATE,
                                     enabled=True,
                                     skip=1,
                                     REQUEST=None):
        "Update the maintenance window from GUI elements"
        def makeInt(v, fieldName, minv=None, maxv=None, acceptBlanks=True):
            if acceptBlanks:
                if isinstance(v, str):
                    v = v.strip()
                v = v or '0'
            try:
                v = int(v)
                if minv is not None and v < minv:
                    raise ValueError
                if maxv is not None and v > maxv:
                    raise ValueError
            except ValueError:
                if minv is None and maxv is None:
                    msg = '%s must be an integer.' % fieldName
                elif minv is not None and maxv is not None:
                    msg = '%s must be between %s and %s inclusive.' % (
                                fieldName, minv, maxv)
                elif minv is not None:
                    msg = '%s must be at least %s' % (fieldName, minv)
                else:
                    msg = '%s must be no greater than %s' % (fieldName, maxv)
                msgs.append(msg)
                v = None
            return v

        msgs = []
        # startHours, startMinutes come from menus.  No need to catch
        # ValueError on the int conversion.
        startHours = int(startHours)
        startMinutes = int(startMinutes)
        self.enabled = bool(enabled)
        import re
        try:
            month, day, year = re.split('[^ 0-9]', startDate)
        except ValueError:
            msgs.append("Date needs three number fields")
        day = int(day)
        month = int(month)
        year = int(year)
        if not msgs:
            t = time.mktime((year, month, day, startHours, startMinutes,
                             0, 0, 0, -1))
        if not msgs:
            durationDays = makeInt(durationDays, 'Duration days',
                                        minv=0)
            durationHours = makeInt(durationHours, 'Duration hours',
                                        minv=0, maxv=23)
            durationMinutes = makeInt(durationMinutes, 'Duration minutes',
                                        minv=0, maxv=59)
        if not msgs:
            duration = (durationDays * (60*24) +
                        durationHours * 60 +
                        durationMinutes)

            if duration < 1:
                msgs.append('Duration must be at least 1 minute.')
        if msgs:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Window Edit Failed',
                    '\n'.join(msgs),
                    messaging.WARNING
                )
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
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Window Updated',
                    'Maintenance window changes were saved.'
                )
                audit('UI.MaintenanceWindow.Edit', self)
        if REQUEST:
            return REQUEST.RESPONSE.redirect(self.getUrlForUserCommands())


    def nextEvent(self, now):
        "Return the time of the next begin() or end()"
        if self.started:
            return self.adjustDST(self.started + self.duration * 60 - 1)
        # ok, so maybe "now" is a little late: start anything that
        # should have been started by now
        return self.next(self.padDST(now) - self.duration * 60 + 1)


    security.declareProtected(ZEN_VIEW, 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
        "fix up breadCrumbs to add a link back to the Manage tab"
        bc = super(MaintenanceWindow, self).breadCrumbs(terminator)
        url, display = bc[-2]
        url += "/" + self.backCrumb
        bc.insert(-1, (url, 'manage'))
        return bc


    def next(self, now = None):
        """
        From Unix time_t now value, return next time_t value
        for the window to start, or None
        This adjusts for DST changes.
        """
        return self.adjustDST(self._next(now))
        
    def _next(self, now):
        if not self.enabled:
            return None

        if self.skip is None:
            self.skip = 1

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

    def isActive(self):
        """
        Return whether or not the maintenance window is active.

        @return: is this window active or not?
        @rtype: boolean
        """
        if not self.enabled or self.started is None:
            return False
        return True

    def fetchDeviceMinProdStates(self, devices=None):
        """
        Return a dictionary of devices and their minimum production state from
        all maintenance windows.

        Note: This method should be moved to the zenjobs command in order to
              improve performance.

        @return: dictionary of device_id:production_state
        @rtype: dictionary
        """
        # Get all maintenance windows + action rules from all device classes,
        # devices, Systems, Locations, and Groups.
        # Yes, it's O(m * n)
        minDevProdStates = {}
        cat = getattr(self, self.default_catalog)
        for entry in cat():
            try:
                mw = entry.getObject()
            except Exception:
                continue

            if not mw.isActive():
                # Note: if the mw has just ended, the self.end() method
                #       has already made the mw inactive before this point
                continue

            log.debug("Updating min MW Prod state using state %s from window %s",
                    mw.startProductionState, mw.displayName())

            if self.primaryAq() == mw.primaryAq():
                # Special case: our window's devices
                mwDevices = devices
            else:
                mwDevices = mw.fetchDevices()

            for device in mwDevices:
                state = minDevProdStates.get(device.id, None)
                if state is None or state > mw.startProductionState:
                    minDevProdStates[device.id] = mw.startProductionState
                    log.debug("MW %s has lowered %s's min MW prod state to %s",
                        mw.displayName(), device.id, mw.startProductionState)

        return minDevProdStates


    def fetchDevices(self):
        """
        Get the list of devices from our maintenance window.
        """
        target = self.target()
        from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
        if isinstance(target, DeviceOrganizer):
            devices = target.getSubDevices()
        else:
            devices = [target]

        return devices


    security.declareProtected(ZEN_MAINTENANCE_WINDOW_EDIT, 'setProdState')
    def setProdState(self, state, ending=False):
        """
        At any one time there is one production state for each device to be in,
        and that is the state that is the most 'blacked out' in all of the active
        maintenance windows affecting that device.  When the last maintenance
        window affecting a device has ended, the original production state of the
        device is used to determine the end state of the device.

        Maintenance windows are processed by zenjobs in batch so the ordering
        of when two maintenance windows that end at the same time get processed
        is non-deterministic.  Since there is only one stop production state now,
        this is not an issue.

        @parameter state: hint from the maint window about device's start or stop state
        @type state: integer
        @parameter ending: are we ending a maintenance window?
        @type ending: boolean
        """
        # Note: self.begin() starts our window before we get called, so the
        #       following takes into account our window state too.
        #       Conversely, self.end() ends the window before calling this code.
        devices = self.fetchDevices()
        minDevProdStates = self.fetchDeviceMinProdStates( devices )

        for device in devices:
            if ending:
                # Note: If no maintenance windows apply to a device, then the
                #       device won't exist in minDevProdStates
                # This takes care of the case where there are still active
                # maintenance windows.
                minProdState = minDevProdStates.get(device.id,
                                            device.preMWProductionState)

            elif device.id in minDevProdStates:
                minProdState = minDevProdStates[device.id]

            else: # This is impossible for us to ever get here as minDevProdStates
                  # has been added by self.fetchDeviceMinProdStates()
                log.error("The device %s does not appear in any maintenance"
                          " windows (including %s -- which is just starting).",
                          device.id, self.displayName())
                continue

            self._p_changed = 1
            # Changes the current state for a device, but *not*
            # the preMWProductionState
            oldProductionState = self.dmd.convertProdState(device.productionState)
            newProductionState = self.dmd.convertProdState(minProdState)
            log.info("MW %s changes %s's production state from %s to %s",
                     self.displayName(), device.id, oldProductionState,
                     newProductionState)
            audit('System.Device.Edit', device, starting=str(not ending),
                maintenanceWindow=self.displayName(), 
                productionState=newProductionState,
                oldData_={'productionState':oldProductionState})
            device.setProdState(minProdState, maintWindowChange=True)


    def begin(self, now = None):
        """
        Hook for entering the Maintenance Window: call if you override
        """
        log.info("Mainenance window %s starting" % self.displayName())
        if not now:
            now = time.time()

        # Make sure that we've started before the calculation of the production
        # state occurs.
        self.started = now
        self.setProdState(self.startProductionState)



    def end(self):
        """
        Hook for leaving the Maintenance Window: call if you override
        """
        log.info("Mainenance window %s ending" % self.displayName())
        # Make sure that the window has ended before the calculation of
        # the production state occurs.
        self.started = None
        self.setProdState(self.stopProductionState, ending=True)


    def execute(self, now = None):
        "Take the next step: either start or stop the Maintenance Window"
        if self.started:
            self.end()
        else:
            self.begin(now)

    def adjustDST(self, result):
        if result is None:
            return None
        if self.started:
            startTime = time.localtime(self.started)
        else:
            startTime = time.localtime(self.start)
        resultTime = time.localtime(result)
        if startTime.tm_isdst == resultTime.tm_isdst:
            return result
        if startTime.tm_isdst:
            return result + 60*60
        return result - 60*60


    def padDST(self, now):
        """
        When incrementing or decrementing timestamps within a DST switch we
        need to add or subtract the DST offset accordingly.
        """
        startTime = time.localtime(self.start)
        nowTime = time.localtime(now)
        if startTime.tm_isdst == nowTime.tm_isdst:
            return now
        elif startTime.tm_isdst:
            return now - 60 * 60
        else:
            return now + 60 * 60


DeviceMaintenanceWindow = MaintenanceWindow
OrganizerMaintenanceWindow = MaintenanceWindow


from Products.ZCatalog.ZCatalog import manage_addZCatalog
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.CMFCore.utils import getToolByName


def createMaintenanceWindowCatalog(dmd):

    catalog_name = 'maintenanceWindowSearch'

    manage_addZCatalog(dmd, catalog_name, catalog_name)
    cat = getToolByName(dmd, catalog_name)

    id_index = makeCaseInsensitiveFieldIndex('getId')
    cat._catalog.addIndex('id', id_index)
    cat.addColumn('id')

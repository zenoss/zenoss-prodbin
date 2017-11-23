##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import time, datetime

from Products.Zuul.infos import InfoBase, ProxyProperty

class MaintenanceWindowInfo(InfoBase):
    name = ProxyProperty('name')
    start = ProxyProperty('start')
    started = ProxyProperty('started')
    enabled = ProxyProperty('enabled')
    #duration = ProxyProperty('duration')
    repeat = ProxyProperty('repeat')
    skip = ProxyProperty('skip')
    days = ProxyProperty('days')
    occurrence = ProxyProperty('occurrence')
    startState = ProxyProperty('startProductionState')

    @property
    def startProdState(self):
        return self._object.niceStartProductionState()

    @property
    def niceRepeat(self):
        return self._object.niceRepeat()

    @property
    def duration(self):
        return self._object.niceDuration()

    @property
    def startTime(self):
        return self._object.niceStartDateTime()

    def updateWindow(self, p):
        startDateTime = p.get('startDateTime', None)
        if not startDateTime:
            startDate = p.get('startDate',
                datetime.datetime.now().strftime('%m/%d/%Y'))
            startHours = p.get('startHours', '00')
            startMinutes = p.get('startMinutes', '00')
            startSeconds = p.get('startSeconds', '00')
            startDateTimeString = '{} {}:{}:{}'.format(
            startDate, startHours, startMinutes, startSeconds)
            dateTime = datetime.datetime.strptime(startDateTimeString,
                "%m/%d/%Y %H:%M:%S")
            startDateTime = time.mktime(dateTime.timetuple())
        duration = int(p['durationMinutes']) or int(p['durationHours']) \
            or int(p['durationDays'])
        if not duration:
            p['durationHours'] = 1
        if p['repeat'] not in self._object.REPEAT:
            p['repeat'] = self._object.REPEAT[0]
        self._object.manage_editMaintenanceWindow( 
                                     startDateTime=startDateTime,
                                     durationDays=p['durationDays'],
                                     durationHours=p['durationHours'],
                                     durationMinutes=p['durationMinutes'],
                                     repeat=p['repeat'],
                                     days=p.get('days', 'Sunday'),
                                     occurrence=p.get('occurrence', '1st'),
                                     startProductionState=p['startProductionState'],
                                     enabled=p['enabled']
                                )

class UserCommandManagementInfo(InfoBase):
    id = ProxyProperty('id')
    command = ProxyProperty('command')
    description = ProxyProperty('description')

    def updateUserCommand(self, params):
        self._object.updateUserCommand(params)

class AdminRoleManagementInfo(InfoBase):
    id = ProxyProperty('id')
    description = ProxyProperty('description')
    role = ProxyProperty('role')

    @property
    def email(self):
        return self._object.email()

    @property
    def pager(self):
        return self._object.pager()

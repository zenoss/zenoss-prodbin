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

from ZEvent import ZEvent
from Products.ZenModel.ZenModelItem import ZenModelItem
from Acquisition import Implicit

from AccessControl import Permissions as permissions
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

class EventDetail(ZEvent, ZenModelItem, Implicit):
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")

    factory_type_information = ( 
        { 
            'id'             : 'EventDetail',
            'meta_type'      : 'EventDetail',
            'description'    : """Detail view of netcool event""",
            'icon'           : 'EventDetail_icon.gif',
            'product'        : 'ZenEvents',
            'factory'        : '',
            'immediate_view' : 'viewEventFields',
            'actions'        :
            ( 
                { 'id'            : 'fields'
                , 'name'          : 'Fields'
                , 'action'        : 'viewEventFields'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'details'
                , 'name'          : 'Details'
                , 'action'        : 'viewEventDetail'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'log'
                , 'name'          : 'Log'
                , 'action'        : 'viewEventLog'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )

    def __init__(self, manager, fields, data, details=None, logs=None):
        ZEvent.__init__(self, manager, fields, data)
        self._details = details
        self._logs = logs

    def getEventDetails(self):
        """return array of detail tuples (field,value)"""
        return self._details


    def getEventLogs(self):
        """return an array of log tuples (user,date,text)"""
        return self._logs
        

InitializeClass(EventDetail)

class EventData:
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
    def __init__(self, field, value):
        self.field = field
        self.value = value
InitializeClass(EventData)


class EventLog:
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
    def __init__(self, user, date, text):
        self.user = user
        self.date = date
        self.text = text
InitializeClass(EventLog)

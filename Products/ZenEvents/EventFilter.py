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

class EventFilter(object):
    "Mix-in for objects that query events"

    where = None
    formName = 'actionRule'

    def getQueryElements(self):
        s = self.genMeta().items()
        s.sort()
        result = ['<option/>']
        for name, attrType in s:
            result.append('<option value="%s">%s</option>' %
                          (name, attrType.label))
        return '\n'.join(result)

    def getWhereClauseAsJavaScript(self):
        s = self.genMeta().items()
        s.sort()
        result = []
        for name, attrType in s:
            result.append('   %s\n' % attrType.genProperties(name))
        result = ['var properties={' + ',\n'.join(result) + '};\n'] 
        result.append((Modes + 'var current = %s \n') %
                       self._whereClauseAsJavaScript())
        result.append('initializeFilters(current)\n')
        return ''.join(result)

    def genMeta(self):
        from WhereClause import Text, Select, Compare, Enumerated, DeviceGroup
        from Products.ZenModel.DataRoot import DataRoot
        from EventManagerBase import EventManagerBase
        kw = {}
        def addDevices(name, label, column):
            devices = self.dmd.getDmdRoot(name).getOrganizerNames()
            kw[column] = DeviceGroup(label, devices)
        addDevices('Systems', 'Systems', 'systems')
        addDevices('Groups', 'Device Groups', 'deviceGroups')
        addDevices('Devices', 'Device Class', 'deviceClass')
        addDevices('Events', 'Event Class', 'eventClass')
        esconv = [(b, a) for a, b in EventManagerBase.eventStateConversions]
        sconv = [(b, a) for a, b in EventManagerBase.severityConversions]
        pconv = [d.split(':') for d in DataRoot.prodStateConversions]
        pconv = [(int(b), a) for a, b in pconv]
        dpconv = [x.split(':') for x in DataRoot.priorityConversions]
        dpconv = [(int(b), a) for a, b in dpconv]
        owners = [(n, n) for n in self.dmd.ZenUsers.getAllUserSettingsNames()]
        return dict(
            summary=Text("Summary"),
            prodState=Enumerated("Production State",pconv),
            severity=Enumerated("Severity",sconv),
            eventState=Enumerated("Event State",esconv),
            device=Text("Device"),
            devicePriority=Enumerated("Device Priority",dpconv),
            eventClassKey=Text("Event Class Key"),
            count=Compare("Count"),
            manager=Text("Manager"),
            agent=Select("Agent",[(x, x) for x in
            "zentrap", "zenprocess", "zenstatus", 
            "zenperfsnmp", "zensyslog", "zenxevent",
            "zenmodeler","zenperfxmlrpc","zenping",
            "zenactions","zencommand"]),
            facility=Select("Facility",[
            "auth","authpriv","cron","daemon","kern","lpr","mail",
            "mark","news","security","syslog","user","uucp",
            "local0","local1","local2","local3","local4",
            "local05","local6","local7"]),
            priority=Select("Priority",[
            "debug","info","notice","warning","error","critical",
            "alert","emergency"]),
            component=Text("Component"),
            message=Text("Message"),
            ntevid=Text("ntevid"),
            ipAddress=Text("IP Address"),
            ownerId=Select("Owner Id", owners),
            **kw)

    def getWhere(self):
        return self.where

    def _whereClauseAsJavaScript(self):
        import WhereClause
        return WhereClause.toJavaScript(self.genMeta(), self.getWhere())

Modes = """
 var modes = {
   text:[{text:"contains",value:"~"},
         {text:"does not contain",value:"!~"},
         {text:"begins with",value:"^"},
         {text:"ends with",value:"$"},
         {text:"is",value:""},
         {text:"is not",value:"!"}],
   select:[{text:"is",value:""},
           {text:"is not",value:"!"}],
   compare:[{text:"<",value:"<"},
            {text:"<=",value:"<="},
            {text:"=",value:"="},
            {text:">",value:">"},
            {text:">=",value:">"}],
   cselect:[{text:"<",value:"<"},
            {text:"<=",value:"<="},
            {text:"=",value:"="},
            {text:">",value:">"},
            {text:">=",value:">="}]};
"""



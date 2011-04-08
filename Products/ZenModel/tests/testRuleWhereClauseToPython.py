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

from Products.ZenEvents.WhereClause import Text, Select, Compare, Enumerated, DeviceGroup, EventClass
from Products.ZenEvents.WhereClause import toPython
from ZenModelBaseTest import ZenModelBaseTest



class TestRuleWhereClauseToPython(ZenModelBaseTest):

    def setUp(self):

        # this var has the structure: [(old_where, new_python), ...]
        # These rules are adapted from a customers rules and have been scrubbed
        # to use mock data, such as deviceClass. The structure and format have
        # not changed.
        self.test_rules = [
            # this where clause was built with every available filter in the old UI.
            ("(prodState < 1000) and (devicePriority < 5) and (facility = 11) and (eventClassKey != '/Status/Perf') and (eventKey like '%/Status%') and (agent = 'zenhub') and (manager like '%manager_ends_with') and (deviceClass like '/%') and (message not like '%msg doesnt contain%') and (eventState < 1) and (ntevid like '%ntevid_test%') and (severity < 5) and (eventClass like '/Status/Heartbeat%') and (summary like '%foobaz%') and (priority = 0) and (deviceGroups like '%|/%') and (location like '%loc_contains%') and (ownerId = 'admin' or ownerId = 'tester') and (ipAddress like '%192.168%') and (systems like '%|/%')",
             "(dev.production_state < 1000) and (dev.priority < 5) and (evt.syslog_facility == 11) and (evt.event_class_key != '/Status/Perf') and ('/Status' in evt.event_key) and (evt.agent == 'zenhub') and (evt.monitor.endswith('manager_ends_with')) and (dev.device_class.beginswith('/')) and ('msg doesnt contain' not in evt.message) and (evt.status < 1) and ('ntevid_test' in evt.nt_event_code) and (evt.severity < 5) and (evt.event_class.beginswith('/Status/Heartbeat')) and ('foobaz' in evt.summary) and (evt.syslog_priority == 0) and ('/' in dev.groups) and ('loc_contains' in dev.location) and (evt.current_user_name == 'admin') or (evt.current_user_name == 'tester') and ('192.168' in dev.ip_address) and ('/' in dev.systems)"),

            ("(prodState = 1000) and (deviceClass like '/Network%' or deviceClass like '/Server%') and (eventState = 0) and (severity >= 5) and (summary not like '%System Fault: FAN FAULT is detected.%') and (deviceGroups like '%|/test%' or deviceGroups like '%|/another/test%')",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) or (dev.device_class.beginswith('/Server')) and (evt.status == 0) and (evt.severity >= 5) and ('System Fault: FAN FAULT is detected.' not in evt.summary) and ('/test' in dev.groups) or ('/another/test' in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (device != 'telcotesting1.sat6') and (eventState = 0) and (severity >= 5)",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) and (dev.name != 'telcotesting1.sat6') and (evt.status == 0) and (evt.severity >= 5)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (device not like '%stl3%') and (eventState = 0) and (severity >= 5) and (summary not like '%System Fault: FAN FAULT is detected.%') and (deviceGroups not like '%|/test%')",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) and ('stl3' not in dev.name) and (evt.status == 0) and (evt.severity >= 5) and ('System Fault: FAN FAULT is detected.' not in evt.summary) and ('/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 4) and (deviceGroups not like '%|/test%')",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) and (evt.status == 0) and (evt.severity >= 4) and ('/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (deviceGroups not like '%|/another/test%')",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and ('/another/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (deviceGroups not like '%|/test%')",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and ('/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (summary not like '%System Fault: FAN FAULT is detected.%') and (deviceGroups not like '%|/test%')",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and ('System Fault: FAN FAULT is detected.' not in evt.summary) and ('/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (summary not like '%System Fault: FAN FAULT is detected.%')",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and ('System Fault: FAN FAULT is detected.' not in evt.summary)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (summary not like '%threshold of Over%' or summary not like '%fan fault%')",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and ('threshold of Over' not in evt.summary) or ('fan fault' not in evt.summary)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5)",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network')) and (evt.status == 0) and (evt.severity >= 5)"),

            ("(prodState = 1000) and (deviceClass like '/Network/Router%') and (eventState = 0) and (severity >= 5)",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Network/Router')) and (evt.status == 0) and (evt.severity >= 5)"),

            ("(prodState = 1000) and (deviceClass like '/Server%') and (device != 'localhost') and (eventState = 0) and (count > 1) and (severity >= 4)",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Server')) and (dev.name != 'localhost') and (evt.status == 0) and (evt.count > 1) and (evt.severity >= 4)"),

            ("(prodState = 1000) and (deviceClass like '/Server%') and (eventState = 0) and (count > 1) and (severity >= 4)",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Server')) and (evt.status == 0) and (evt.count > 1) and (evt.severity >= 4)"),

            ("(prodState = 1000) and (deviceClass like '/Server%') and (eventState = 0) and (severity >= 4)",
             "(dev.production_state == 1000) and (dev.device_class.beginswith('/Server')) and (evt.status == 0) and (evt.severity >= 4)"),

            ("(prodState = 1000) and (eventClass like '/Status/Perf%') and (eventState = 0) and (summary like '%threshold of Over%') and (deviceGroups like '%|/test%')",
             "(dev.production_state == 1000) and (evt.event_class.beginswith('/Status/Perf')) and (evt.status == 0) and ('threshold of Over' in evt.summary) and ('/test' in dev.groups)"),

            ("(prodState = 1000) and (eventState = 0) and (eventClass like '/Status/Perf%') and (summary like '%threshold of Over%') and (deviceGroups like '%|/%') and (systems like '%|/foo%' or systems like '%|/foo/bar%')",
             "(dev.production_state == 1000) and (evt.status == 0) and (evt.event_class.beginswith('/Status/Perf')) and ('threshold of Over' in evt.summary) and ('/' in dev.groups) and ('/foo' in dev.systems) or ('/foo/bar' in dev.systems)"),

            ("severity >= 5 and eventState = 0 and prodState >= 1000",
             "(evt.severity >= 5) and (evt.status == 0) and (dev.production_state >= 1000)"),
        ]


        # Set up really controlled meta for these mock alert rules.
        deviceGroups_options = [(0, '/'), (1, '/test'), (2, '/another'), (3, '/another/test')]
        deviceGroups = DeviceGroup('Device Group', deviceGroups_options)

        systems_options =  [(0, '/'), (1, '/foo'), (2, '/foo/bar'), (3, '/baz')]
        systems = DeviceGroup('Systems', systems_options)

        esconv = [(0, 'New'), (1, 'Acknowledged'), (2, 'Suppressed')]
        sconv = [(5, 'Critical'), (4, 'Error'), (3, 'Warning'), (2, 'Info'), (1, 'Debug'), (0, 'Clear')]
        pconv = [(1000, 'Production'), (500, 'Pre-Production'), (400, 'Test'), (300, 'Maintenance'), (-1, 'Decommissioned')]
        dpconv = [(5, 'Highest'), (4, 'High'), (3, 'Normal'), (2, 'Low'), (1, 'Lowest'), (0, 'Trivial')]
        owners =  [('admin', 'admin'), ('tester', 'tester')]
        eventClasses = [
                ('/', '/'),
                ('/App', '/App'),
                ('/Status', '/Status'),
                ('/Status/Heartbeat', '/Status/Heartbeat'),
                ('/Status/Perf', '/Status/Perf'),
                ('/Status/Ping', '/Status/Ping')]
        deviceClasses = [
                ('/', '/'),
                ('/Discovered', '/Discovered'),
                ('/Server', '/Server'),
                ('/Server/Linux', '/Server/Linux'),
                ('/Network', '/Network'),
                ('/Network/Router','/Network/Router')]

        self.generated_meta = dict(
            eventClass=EventClass('Event Class', eventClasses),
            deviceClass=EventClass('Device Class', deviceClasses),
            summary=Text("Summary"),
            location=Text("Location"),
            prodState=Enumerated("Production State",pconv),
            severity=Enumerated("Severity",sconv),
            eventState=Enumerated("Event State",esconv),
            device=Text("Device"),
            devicePriority=Enumerated("Device Priority",dpconv),
            eventClassKey=Text("Event Class Key"),
            count=Compare("Count"),
            manager=Text("Manager"),
            agent=Select("Agent",[(x, x) for x in
                "zenhub", "zenping", "zensyslog", "zenactions", "zentrap",
                "zenmodeler", "zenperfsnmp", "zencommand", "zenprocess", "zenwin",
                "zeneventlog"]),
            facility=Select("Facility",[
                "auth","authpriv","cron","daemon","kern","lpr","mail",
                "mark","news","security","syslog","user","uucp",
                "local0","local1","local2","local3","local4",
                "local05","local6","local7"]),
            priority=Select("Priority",[
                "debug","info","notice","warning","error","critical",
                "alert","emergency"]),
            component=Text("Component"),
            eventKey=Text("Event Key"),
            message=Text("Message"),
            ntevid=Text("ntevid"),
            ipAddress=Text("IP Address"),
            ownerId=Select("Owner Id", owners),
            deviceGroups = deviceGroups,
            systems = systems,
        )

    def testRuleWhereClauseToPython(self):
        for where_clause, python_statement in self.test_rules:
            self.assertEquals(toPython(self.generated_meta, where_clause), python_statement)
    


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRuleWhereClauseToPython))
    return suite

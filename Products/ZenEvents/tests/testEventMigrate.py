##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenTestCase.BaseTestCase import BaseTestCase
from zope.interface import implements
from Products.ZenEvents.events2.processing import AddDeviceContextAndTagsPipe
from Products.ZenEvents.events2.proxy import EventProxy
from Products.ZenMessaging.queuemessaging.interfaces import IQueuePublisher
from Products.ZenEvents.zeneventmigrate import ZenEventMigrate
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from ConfigParser import ConfigParser
from datetime import datetime
from itertools import repeat
import re

import logging
log = logging.getLogger('zen.testEventMigrate')

#lookup
import Globals
from Products.Five import zcml
import Products.ZenossStartup
zcml.load_site()


class MockChannel(object):
    """
    Mocks out an AMQP channel.
    """
    def tx_select(self):
        pass

    def tx_commit(self):
        pass

class MockPublisher(object):
    """
    Mocks out an IQueuePublisher which saves published events for verification.
    """
    implements(IQueuePublisher)

    def __init__(self):
        self.msgs = []
        self.channel = MockChannel()

    def publish(self, exchange, routing_key, message, createQueues=None, mandatory=False):
        self.msgs.append(message)

class MockCursor(object):
    """
    Mocks out a SQL cursor object.
    """
    def __init__(self, conn):
        self.conn = conn
        self.next_result = None

    def execute(self, sql, args=None):
        self.next_result = self.conn.resultForQuery(sql, args)

    def fetchall(self):
        return self.next_result

    def fetchone(self):
        return self.next_result[0]

    def close(self):
        pass

class MockConnection(object):
    """
    Mocks out a SQL connection.
    """
    def __init__(self, queries):
        self.queries = queries

    def cursor(self):
        return MockCursor(self)

    def resultForQuery(self, sql, args=None):
        for query, result in self.queries.iteritems():
            if re.search(query, sql):
                try:
                    return result.next()
                except StopIteration:
                    return []
        raise Exception('Unsupported query: %s' % sql)

class testEventMigrate(BaseTestCase):

    def afterSetUp(self):
        super(testEventMigrate, self).afterSetUp()

        self.zeneventmigrate = ZenEventMigrate(app=self.app, connect=True)

        # Initialize config
        self.zeneventmigrate.config = ConfigParser()
        self.zeneventmigrate.config.add_section(self.zeneventmigrate.config_section)

        # Don't save state to disk
        self.zeneventmigrate._storeConfig = lambda *x: None

        # Don't show progress messages
        self.zeneventmigrate._progress = lambda *x: None

    def testMigrateSameDeviceClass(self):
        """
        Tests that an event sent when a device belongs to a new device class is tagged with the original device class
        from the migrated event.
        """
        devices = self.dmd.Devices

        original = devices.createOrganizer("/Server/Solaris")
        original_guid = IGlobalIdentifier(original).getGUID()

        updated = devices.createOrganizer("/Server/SSH/Solaris")
        updated_guid = IGlobalIdentifier(updated).getGUID()

        updated.createInstance('test-solaris10.zenoss.loc')

        evt = {
            'dedupid': "test-solaris10.zenoss.loc|SUNWxscreensaver-hacks|/Change/Set||2|calling function "
                       "'setProductKey' with 'SUNWxscreensaver-hacks' on object SUNWxscreensaver-hacks",
            'evid': "0002aaaf-e10f-4348-a7b8-ae12573e560a",
            'device': "test-solaris10.zenoss.loc",
            'component': "SUNWxscreensaver-hacks",
            'eventClass': "/Change/Set",
            'eventKey': "",
            'summary': "calling function 'setProductKey' with 'SUNWxscreensaver-hacks' on object SUNWxscreensaver-hacks",
            'message': "calling function 'setProductKey' with 'SUNWxscreensaver-hacks' on object SUNWxscreensaver-hacks",
            'severity': 2,
            'eventState': 0,
            'eventClassKey': "",
            'eventGroup': "",
            'stateChange': datetime(2011, 6, 8, 13, 24, 20),
            'firstTime': 1307557460.044,
            'lastTime': 1307557460.044,
            'count': 1,
            'prodState': 1000,
            'suppid': '',
            'manager': '',
            'agent': 'ApplyDataMap',
            'DeviceClass': '/Server/Solaris',
            'Location': '',
            'Systems': '|',
            'DeviceGroups': '|',
            'ipAddress': '10.175.211.23',
            'facility': 'unknown',
            'priority': -1,
            'ntevid': 0,
            'ownerid': '',
            'deletedTime': datetime(2011, 6, 8, 13, 24, 20),
            'clearid': None,
            'DevicePriority': 3,
            'eventClassMapping': '',
            'monitor': '',
        }

        events = [evt]
        queries = {
            r'^SELECT COUNT\(\*\) AS num_rows FROM status': repeat([{ 'num_rows': len(events) }]),
            r'^SELECT \* FROM status': [events].__iter__(),
            r'^SELECT evid, name, value FROM detail': repeat([]),
            r'^SELECT \* FROM log WHERE evid IN': repeat([]),
        }
        conn = MockConnection(queries)
        mock_publisher = MockPublisher()
        self.zeneventmigrate._migrate_events(conn, mock_publisher, True)
        self.assertEquals(1, len(mock_publisher.msgs))
        event_summary = mock_publisher.msgs[0]
        event_occurrence = event_summary.occurrence[0]
        for d in event_occurrence.details:
            if d.name == EventProxy.DEVICE_CLASS_DETAIL_KEY:
                self.assertEquals([original.getOrganizerName()], d.value)

        device_class_tags = set()
        for t in event_occurrence.tags:
            if t.type == AddDeviceContextAndTagsPipe.DEVICE_DEVICECLASS_TAG_KEY:
                device_class_tags.update(t.uuid)

        self.assertTrue(original_guid in device_class_tags, msg="Event wasn't tagged with original device class")
        self.assertFalse(updated_guid in device_class_tags, msg="Event was tagged with new device class")

    def testMigrateSameLocation(self):
        """
        Tests that an event sent when a device belongs to a new location is tagged with the original location
        from the migrated event.
        """
        devices = self.dmd.Devices
        locations = self.dmd.Locations

        original = locations.createOrganizer("/Austin")
        original_guid = IGlobalIdentifier(original).getGUID()

        updated = locations.createOrganizer("/Annapolis")
        updated_guid = IGlobalIdentifier(updated).getGUID()

        device_class = devices.createOrganizer("/Server/Windows/WMI/Active Directory/2008")
        device = device_class.createInstance('test-win2008-ad.zenoss.loc')
        device.setLocation(updated.getOrganizerName())

        evt = {
            'dedupid': "test-win2008-ad.zenoss.loc|zeneventlog|/Status/Wmi||4|\n            Could not read the Windows"
                       " event log (ExecNotificationQuery on test-win2008-ad.zenoss.loc (DOS code 0x800700a4)). C",
            'evid': "00049aee-b0bc-4621-8393-9b0cf831afc4",
            'device': "test-win2008-ad.zenoss.loc",
            'component': "zeneventlog",
            'eventClass': "/Status/Wmi",
            'eventKey': "",
            'summary': "Could not read the Windows event log (ExecNotificationQuery on test-win2008-ad.zenoss.loc (DOS"
                       " code 0x800700a4)). C",
            'message': "Could not read the Windows event log (ExecNotificationQuery on test-win2008-ad.zenoss.loc (DOS"
                       " code 0x800700a4)). Check your username/password settings and verify network connectivity.",
            'severity': 4,
            'eventState': 0,
            'eventClassKey': "",
            'eventGroup': "",
            'stateChange': datetime(2011, 6, 9, 22, 39, 48),
            'firstTime': 1307677188.839,
            'lastTime': 1307677188.839,
            'count': 1,
            'prodState': 1000,
            'suppid': '',
            'manager': 'pwarren-dev.zenoss.loc',
            'agent': 'zeneventlog',
            'DeviceClass': '/Server/Windows/WMI/Active Directory/2008',
            'Location': '/Austin',
            'Systems': '|',
            'DeviceGroups': '|',
            'ipAddress': '10.175.211.197',
            'facility': 'unknown',
            'priority': -1,
            'ntevid': 0,
            'ownerid': '',
            'deletedTime': datetime(2011, 6, 9, 22, 39, 48),
            'clearid': '947d299f-cc25-4250-a8de-b8fd8bc2b06d',
            'DevicePriority': 3,
            'eventClassMapping': '',
            'monitor': 'localhost',
        }

        events = [evt]
        queries = {
            r'^SELECT COUNT\(\*\) AS num_rows FROM status': repeat([{ 'num_rows': len(events) }]),
            r'^SELECT \* FROM status': [events].__iter__(),
            r'^SELECT evid, name, value FROM detail': repeat([]),
            r'^SELECT \* FROM log WHERE evid IN': repeat([]),
        }
        conn = MockConnection(queries)
        mock_publisher = MockPublisher()
        self.zeneventmigrate._migrate_events(conn, mock_publisher, True)
        self.assertEquals(1, len(mock_publisher.msgs))
        event_summary = mock_publisher.msgs[0]
        event_occurrence = event_summary.occurrence[0]
        for d in event_occurrence.details:
            if d.name == EventProxy.DEVICE_LOCATION_DETAIL_KEY:
                self.assertEquals([original.getOrganizerName()], d.value)

        device_location_tags = set()
        for t in event_occurrence.tags:
            if t.type == AddDeviceContextAndTagsPipe.DEVICE_LOCATION_TAG_KEY:
                device_location_tags.update(t.uuid)

        self.assertTrue(original_guid in device_location_tags, msg="Event wasn't tagged with original location")
        self.assertFalse(updated_guid in device_location_tags, msg="Event was tagged with new location")

    def testMigrateSameGroups(self):
        """
        Tests that an event sent when a device belongs to new device groups is tagged with the original device groups
        from the migrated event.
        """
        devices = self.dmd.Devices
        groups = self.dmd.Groups

        group_first = groups.createOrganizer('/First')
        group_second = groups.createOrganizer('/Second')
        group_third = groups.createOrganizer('/Third')
        group_first_nested = groups.createOrganizer('/First/FirstNested')

        group_fourth = groups.createOrganizer('/Fourth')
        group_fifth = groups.createOrganizer('/Fifth')

        device_class = devices.createOrganizer("/Server/Linux")
        device = device_class.createInstance('pwarren-dev.zenoss.loc')
        device.setGroups([group_fourth.getOrganizerName(), group_fifth.getOrganizerName()])

        evt = {
            'dedupid': "pwarren-dev.zenoss.loc|snmpd|||2|Received SNMP packet(s) from UDP: [10.175.210.74]:48219",
            'evid': "0015e762-1983-40ad-a966-d2a66ee40fd9",
            'device': "pwarren-dev.zenoss.loc",
            'component': "snmpd",
            'eventClass': "/Unknown",
            'eventKey': "",
            'summary': "Received SNMP packet(s) from UDP: [10.175.210.74]:48219",
            'message': "Received SNMP packet(s) from UDP: [10.175.210.74]:48219",
            'severity': 2,
            'eventState': 0,
            'eventClassKey': "snmpd",
            'eventGroup': "syslog",
            'stateChange': datetime(2011, 6, 13, 3, 10, 13),
            'firstTime': 1307952609.997,
            'lastTime': 1307952609.997,
            'count': 1,
            'prodState': 1000,
            'suppid': '',
            'manager': 'pwarren-dev.zenoss.loc',
            'agent': 'zensyslog',
            'DeviceClass': '/Server/Linux',
            'Location': '/Austin',
            'Systems': '|/Production|/Development',
            'DeviceGroups': '|/First|/Second|/Third|/First/FirstNested',
            'ipAddress': '10.175.210.74',
            'facility': 'nfacilit',
            'priority': 6,
            'ntevid': 0,
            'ownerid': '',
            'deletedTime': datetime(2011, 6, 13, 7, 11, 8),
            'clearid': None,
            'DevicePriority': 3,
            'eventClassMapping': '',
            'monitor': 'localhost',
        }

        events = [evt]
        queries = {
            r'^SELECT COUNT\(\*\) AS num_rows FROM status': repeat([{ 'num_rows': len(events) }]),
            r'^SELECT \* FROM status': [events].__iter__(),
            r'^SELECT evid, name, value FROM detail': repeat([]),
            r'^SELECT \* FROM log WHERE evid IN': repeat([]),
        }
        conn = MockConnection(queries)
        mock_publisher = MockPublisher()
        self.zeneventmigrate._migrate_events(conn, mock_publisher, True)
        self.assertEquals(1, len(mock_publisher.msgs))
        event_summary = mock_publisher.msgs[0]
        event_occurrence = event_summary.occurrence[0]

        expected_group_names = set([g.getOrganizerName() for g in [group_first, group_second, group_third,
                                                                   group_first_nested]])
        found_group_names = set()

        for d in event_occurrence.details:
            if d.name == EventProxy.DEVICE_GROUPS_DETAIL_KEY:
                found_group_names.update(d.value)
        diff_names = expected_group_names - found_group_names
        self.assertEquals(0, len(diff_names))

        expected_group_tags = set([IGlobalIdentifier(g).getGUID() for g in [group_first, group_second, group_third,
                                                                            group_first_nested]])
        found_group_tags = set()
        for t in event_occurrence.tags:
            if t.type == AddDeviceContextAndTagsPipe.DEVICE_GROUPS_TAG_KEY:
                found_group_tags.update(t.uuid)

        diff_tags = expected_group_tags - found_group_tags
        self.assertEquals(0, len(diff_tags))

    def testMigrateSameSystems(self):
        """
        Tests that an event sent when a device belongs to new systems is tagged with the original systems
        from the migrated event.
        """
        devices = self.dmd.Devices
        groups = self.dmd.Systems

        system_production = groups.createOrganizer('/Production')
        system_development = groups.createOrganizer('/Development')

        system_additional = groups.createOrganizer('/Additional')
        system_preprod = groups.createOrganizer('/PreProduction')

        device_class = devices.createOrganizer("/Server/Linux")
        device = device_class.createInstance('pwarren-dev.zenoss.loc')
        device.setSystems([system_additional.getOrganizerName(), system_preprod.getOrganizerName()])

        evt = {
            'dedupid': "pwarren-dev.zenoss.loc|snmpd|||2|Received SNMP packet(s) from UDP: [10.175.210.74]:48219",
            'evid': "0015e762-1983-40ad-a966-d2a66ee40fd9",
            'device': "pwarren-dev.zenoss.loc",
            'component': "snmpd",
            'eventClass': "/Unknown",
            'eventKey': "",
            'summary': "Received SNMP packet(s) from UDP: [10.175.210.74]:48219",
            'message': "Received SNMP packet(s) from UDP: [10.175.210.74]:48219",
            'severity': 2,
            'eventState': 0,
            'eventClassKey': "snmpd",
            'eventGroup': "syslog",
            'stateChange': datetime(2011, 6, 13, 3, 10, 13),
            'firstTime': 1307952609.997,
            'lastTime': 1307952609.997,
            'count': 1,
            'prodState': 1000,
            'suppid': '',
            'manager': 'pwarren-dev.zenoss.loc',
            'agent': 'zensyslog',
            'DeviceClass': '/Server/Linux',
            'Location': '/Austin',
            'Systems': '|/Production|/Development',
            'DeviceGroups': '|/First|/Second|/Third|/First/FirstNested',
            'ipAddress': '10.175.210.74',
            'facility': 'nfacilit',
            'priority': 6,
            'ntevid': 0,
            'ownerid': '',
            'deletedTime': datetime(2011, 6, 13, 7, 11, 8),
            'clearid': None,
            'DevicePriority': 3,
            'eventClassMapping': '',
            'monitor': 'localhost',
        }

        events = [evt]
        queries = {
            r'^SELECT COUNT\(\*\) AS num_rows FROM status': repeat([{ 'num_rows': len(events) }]),
            r'^SELECT \* FROM status': [events].__iter__(),
            r'^SELECT evid, name, value FROM detail': repeat([]),
            r'^SELECT \* FROM log WHERE evid IN': repeat([]),
        }
        conn = MockConnection(queries)
        mock_publisher = MockPublisher()
        self.zeneventmigrate._migrate_events(conn, mock_publisher, True)
        self.assertEquals(1, len(mock_publisher.msgs))
        event_summary = mock_publisher.msgs[0]
        event_occurrence = event_summary.occurrence[0]

        expected_system_names = set([s.getOrganizerName() for s in [system_development, system_production]])
        found_system_names = set()

        for d in event_occurrence.details:
            if d.name == EventProxy.DEVICE_SYSTEMS_DETAIL_KEY:
                found_system_names.update(d.value)
        diff_names = expected_system_names - found_system_names
        self.assertEquals(0, len(diff_names))

        expected_system_tags = set([IGlobalIdentifier(s).getGUID() for s in [system_development, system_production]])
        found_system_tags = set()
        for t in event_occurrence.tags:
            if t.type == AddDeviceContextAndTagsPipe.DEVICE_SYSTEMS_TAG_KEY:
                found_system_tags.update(t.uuid)

        diff_tags = expected_system_tags - found_system_tags
        self.assertEquals(0, len(diff_tags))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testEventMigrate))
    return suite

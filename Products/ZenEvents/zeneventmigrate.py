##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
Script used to migrate events from a Zenoss 3.1.x events database into the
new ZEP event schema. All properties of the events are mapped to the new
property values, and zeneventd identification/tagging is performed to ensure
that events will be associated with the correct entities in Zenoss.
"""

import logging
import os
import sys
from time import mktime
from ConfigParser import ConfigParser, NoOptionError
from copy import deepcopy
from itertools import imap
from uuid import uuid4
from signal import signal, siginterrupt, SIGTERM, SIGINT
from time import sleep

import Globals

from Products.ZenUtils.mysql import MySQLdb
from MySQLdb import connect
from MySQLdb.cursors import DictCursor
from _mysql import escape_string

from zenoss.protocols.protobufs.zep_pb2 import (EventSummary, ZepRawEvent, STATUS_NEW, STATUS_ACKNOWLEDGED,
                                                STATUS_SUPPRESSED, STATUS_CLOSED, STATUS_CLEARED,
                                                SYSLOG_PRIORITY_EMERG, SYSLOG_PRIORITY_DEBUG)
from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT
from Products.ZenEvents.syslog_h import fac_values, LOG_FAC
from Products.ZenUtils.AmqpDataManager import AmqpTransaction
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from zope.component import getUtility
from Products.ZenMessaging.queuemessaging.interfaces import IQueuePublisher
from Products.ZenMessaging.queuemessaging.adapters import EventProtobufSeverityMapper
from Products.ZenEvents.events2.processing import EventProxy
from Products.ZenEvents.events2.processing import (Manager, EventContext, IdentifierPipe, AddDeviceContextAndTagsPipe,
                                                   AssignDefaultEventClassAndTagPipe)
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.Location import Location
from Products.ZenModel.System import System

log = logging.getLogger('zen.EventMigrate')

class MappingEventContext(object):
    """
    Contains the event summary information to be published to the migrated
    events queue.
    """
    def __init__(self, event_dict):
        self._event_dict = event_dict
        self._summary = EventSummary()
        self._occurrence = self._summary.occurrence.add()
        self._actor = self._occurrence.actor

    @property
    def event_dict(self):
        return self._event_dict

    @property
    def summary(self):
        return self._summary

    @property
    def occurrence(self):
        return self._occurrence

    @property
    def actor(self):
        return self._actor

    def __str__(self):
        return str(self._summary)

def _user_uuid(dmd, userName):
    # We have to call _getOb instead of getUserSettings here because the
    # latter will create a new user settings object even if the user is
    # not known.
    try:
        user = dmd.ZenUsers._getOb(userName)
        return IGlobalIdentifier(user).getGUID()
    except Exception:
        if log.isEnabledFor(logging.DEBUG):
            log.exception("Failed to look up user UUID for %s", userName)

def _convert_summary(new_name, conversion_fcn = None):
    """
    Returns a function to convert a value from a previous event into
    its equivalent value in the EventSummary.
    """
    def _convert_summary_internal(value, event_ctx):
        if conversion_fcn:
            value = conversion_fcn(value)
        if value is not None:
            setattr(event_ctx.summary, new_name, value)
    return _convert_summary_internal

def _convert_occurrence(new_name, conversion_fcn = None):
    """
    Returns a function to convert a value from a previous event into
    its equivalent value in the Event occurrence.
    """
    def _convert_occurrence_internal(value, event_ctx):
        if conversion_fcn:
            value = conversion_fcn(value)
        if value is not None:
            setattr(event_ctx.occurrence, new_name, value)
    return _convert_occurrence_internal

def _add_detail(new_name, conversion_fcn = None):
    """
    Returns a function to convert a value from a previous event into
    its equivalent EventDetail within the event occurrence.
    """
    def _add_detail_internal(value, event_ctx):
        if conversion_fcn:
            value = conversion_fcn(value)
        if value is not None:
            detail = event_ctx.occurrence.details.add()
            detail.name = new_name
            if not hasattr(value, '__iter__'):
                value = (str(value),)
            else:
                value = map(str, value)
            detail.value.extend(value)
    return _add_detail_internal

def _add_details(value, event_ctx):
    """
    Converts event details from the detail table to EventDetail objects
    on the event occurrence.
    """
    for detail_name, detail_value in value.iteritems():
        detail = event_ctx.occurrence.details.add()
        detail.name = detail_name
        detail.value.append(detail_value)

_AUDIT_LOG_CONVERSIONS = {
    'event state changed to acknowledged': STATUS_ACKNOWLEDGED,
    'deleted by user': STATUS_CLOSED,
}

def _add_logs(dmd):
    """
    Converts event logs from the log table to either AuditLog or
    EventNote objects on the event summary depending on whether
    the log message matches system generated values.
    """
    def _add_logs_internal(value, event_ctx):
        for log_row in value:
            username = log_row['userName']
            useruuid = _user_uuid(dmd, username)
            text = log_row['text']
            ctime = _convert_ts_to_millis(log_row['ctime'])

            audit_state = _AUDIT_LOG_CONVERSIONS.get(text.lower())
            if audit_state:
                log = event_ctx.summary.audit_log.add(timestamp=ctime,
                                                      new_status=audit_state,
                                                      user_name=username)
                if useruuid:
                    log.user_uuid = useruuid
            else:
                note = event_ctx.summary.notes.add(uuid=str(uuid4()),
                                                   user_name=username,
                                                   created_time=ctime,
                                                   message=text)
                if useruuid:
                    note.user_uuid = useruuid
    
    return _add_logs_internal

def _convert_actor(sub_type):
    """
    Returns a function to convert a value from a previous event into
    its equivalent value in the EventActor within the event occurrence.
    """
    def _convert_actor_internal(value, event_ctx):
        if value:
            actor = event_ctx.actor
            if not sub_type:
                actor.element_type_id = DEVICE
                actor.element_identifier = value
            else:
                actor.element_sub_type_id = COMPONENT
                actor.element_sub_identifier = value
    return _convert_actor_internal

def _convert_severity(value):
    return EventProtobufSeverityMapper.SEVERITIES[str(value).upper()]

def _convert_pipe_delimited(value):
    if value:
        values = [val for val in value.split('|') if val]
        return values if values else None

_STATE_CONVERSIONS = {
    0: STATUS_NEW,
    1: STATUS_ACKNOWLEDGED,
    2: STATUS_SUPPRESSED,
}

def _convert_state(status):
    """
    Converts an event state from a previous event into the equivalent new
    state. Events migrated from history get a status of STATUS_CLOSED or
    STATUS_CLEARED depending on the presence of the clearid field.
    """
    def _convert_state_internal(value, event_ctx):
        if status:
            event_ctx.summary.status = _STATE_CONVERSIONS.get(value, STATUS_NEW)
        else:
            event_ctx.summary.status = STATUS_CLEARED if event_ctx.event_dict.get('clearid','') else STATUS_CLOSED
    
    return _convert_state_internal

def _convert_ts_to_millis(value):
    return int(mktime(value.timetuple()) * 1000)

def _convert_double_to_millis(value):
    return int(value * 1000)

def _drop_empty(value):
    return value if value else None

_FACILITY_CONVERSIONS = dict((k,LOG_FAC(v)) for k, v in fac_values.iteritems() if k not in ('facmask','nfacilities'))

def _convert_facility(value):
    """
    Converts a syslog facility from the old string format to the new
    numeric format. This was changed because all systems don't use the
    same mapping for syslog facilities and using a numeric facility
    ensures we don't lose data from the original syslog event.
    """
    if value and value in _FACILITY_CONVERSIONS:
        return _FACILITY_CONVERSIONS[value]

def _convert_priority(value):
    if value >= SYSLOG_PRIORITY_EMERG and value <= SYSLOG_PRIORITY_DEBUG:
       return value

def _convert_event_class_mapping_uuid(dmd):
    """
    Converts an event class mapping to the UUID of the event class
    mapping.
    """
    failed_mappings = set()

    def _convert_event_class_mapping_uuid_internal(value):
        if value:
            try:
                value = value.encode('ascii')
                components = value.split('/')
                components.insert(-1, 'instances')
                eventClass = dmd.unrestrictedTraverse('/zport/dmd/Events' + '/'.join(components))
                return IGlobalIdentifier(eventClass).getGUID()
            except Exception:
                if value not in failed_mappings:
                    failed_mappings.add(value)
                    if log.isEnabledFor(logging.DEBUG):
                        log.exception("Failed to resolve event class mapping: %s", value)
                    else:
                        log.warning('Failed to resolve event class mapping: %s', value)
    return _convert_event_class_mapping_uuid_internal

def _convert_ownerid(dmd):
    def _convert_ownerid_internal(value, event_ctx):
        if value:
            event_ctx.summary.current_user_name = value
            useruuid = _user_uuid(dmd, value)
            if useruuid:
                event_ctx.summary.current_user_uuid = useruuid

    return _convert_ownerid_internal

class EventConverter(object):
    """
    Utility class used to convert an old-style event from the status or
    history table into the equivalent EventSummary protobuf. Other mappers
    exist for converting old style events to event occurrences, but this
    needs to preserve information that is stored in the event summary (i.e.
    count, event notes, audit logs).
    """

    _FIELD_MAPPERS = {
        'evid': _convert_summary('uuid'),
        'dedupid': _convert_occurrence('fingerprint'),
        'device': _convert_actor(False),
        'component': _convert_actor(True),
        'eventClass': _convert_occurrence('event_class'),
        'eventKey': _convert_occurrence('event_key', _drop_empty),
        'summary': _convert_occurrence('summary'),
        'message': _convert_occurrence('message'),
        'severity': _convert_occurrence('severity', _convert_severity),
        'eventClassKey': _convert_occurrence('event_class_key', _drop_empty),
        'eventGroup': _convert_occurrence('event_group', _drop_empty),
        'stateChange': _convert_summary('status_change_time', _convert_ts_to_millis),
        'firstTime': _convert_summary('first_seen_time', _convert_double_to_millis),
        'lastTime': _convert_summary('last_seen_time', _convert_double_to_millis),
        'count': _convert_summary('count'),
        'prodState': _add_detail(EventProxy.PRODUCTION_STATE_DETAIL_KEY),
        # This doesn't have an equivalent value in new schema - just add as detail
        'suppid': _add_detail('suppid', _drop_empty),
        # Deprecated
        'manager': _add_detail('manager', _drop_empty),
        'agent': _convert_occurrence('agent', _drop_empty),
        'DeviceClass': _add_detail(EventProxy.DEVICE_CLASS_DETAIL_KEY, _drop_empty),
        'Location': _add_detail(EventProxy.DEVICE_LOCATION_DETAIL_KEY, _drop_empty),
        'Systems': _add_detail(EventProxy.DEVICE_SYSTEMS_DETAIL_KEY, _convert_pipe_delimited),
        'DeviceGroups': _add_detail(EventProxy.DEVICE_GROUPS_DETAIL_KEY, _convert_pipe_delimited),
        'ipAddress': _add_detail(EventProxy.DEVICE_IP_ADDRESS_DETAIL_KEY, _drop_empty),
        'facility': _convert_occurrence('syslog_facility', _convert_facility),
        'priority': _convert_occurrence('syslog_priority', _convert_priority),
        'ntevid': _convert_occurrence('nt_event_code', _drop_empty),
        'clearid': _convert_summary('cleared_by_event_uuid', _drop_empty),
        'DevicePriority': _add_detail(EventProxy.DEVICE_PRIORITY_DETAIL_KEY),
        'monitor': _convert_occurrence('monitor', _drop_empty),
        'deletedTime': _convert_summary('status_change_time', _convert_ts_to_millis),
        'details': _add_details,
    }

    def __init__(self, dmd, status):
        self.dmd = dmd
        self.status = status
        # Most of these can be shared above - a few require DMD access
        self.field_mappers = dict(EventConverter._FIELD_MAPPERS)
        self.field_mappers['ownerid'] = _convert_ownerid(dmd)
        self.field_mappers['eventState'] = _convert_state(status)
        self.field_mappers['eventClassMapping'] = _convert_occurrence('event_class_mapping_uuid',
                                                                      _convert_event_class_mapping_uuid(dmd))
        self.field_mappers['logs'] = _add_logs(dmd)

    def convert(self, event_dict):
        event_ctx = MappingEventContext(event_dict)
        for name, value in event_dict.iteritems():
            if name in self.field_mappers:
                self.field_mappers[name](value, event_ctx)
            else:
                _add_detail(name)(value, event_ctx)
        return event_ctx

_IN_CLAUSE = lambda evids: ','.join("'%s'" % evid for evid in evids)

class ShutdownException(Exception):
    pass

class ZenEventMigrate(ZenScriptBase):
    def __init__(self, noopts=0, app=None, connect=True):
        super(ZenEventMigrate, self).__init__(noopts=noopts, app=app, connect=connect)
        self.config_filename = zenPath('etc/zeneventmigrate.conf')
        self.config_section = 'zeneventmigrate'
        self._shutdown = False

    def buildOptions(self):
        super(ZenEventMigrate, self).buildOptions()
        self.parser.add_option('--dont-fetch-args', dest='fetchArgs', default=True, action='store_false',
                                help='By default MySQL connection information'
                                    ' is retrieved from Zenoss if not'
                                    ' specified and if Zenoss is available.'
                                    ' This disables fetching of these values'
                                    ' from Zenoss.')
        self.parser.add_option('--evthost', dest='evthost', default='127.0.0.1',
                               help='Events database hostname (Default: %default)')
        self.parser.add_option('--evtport', dest='evtport', action='store', type='int', default=3306,
                               help='Port used to connect to the events database (Default: %default)')
        self.parser.add_option('--evtuser', dest='evtuser', default=None,
                               help='Username used to connect to the events database')
        self.parser.add_option('--evtpass', dest='evtpass', default=None,
                               help='Password used to connect to the events database')
        self.parser.add_option('--evtdb', dest='evtdb', default='events',
                               help='Name of events database (Default: %default)')
        self.parser.add_option('--batchsize', dest='batchsize', action='store', type='int', default=100,
                               help='Number of events to process in one batch (Default: %default)')
        self.parser.add_option('--sleep', dest='sleep', action='store', type='int', default=0,
                               help='Number of seconds to wait after migrating a batch of events (Default: %default)')
        self.parser.add_option('--restart', dest='restart', action='store_true', default=False,
                               help='Use this flag to start a new migration process (disables resuming a previous '
                                    'migration).')

    def _output(self, message):
        if sys.stdout.isatty():
            print message
        else:
            log.info(message)

    def _progress(self, message):
        if sys.stdout.isatty():
            sys.stdout.write("\r" + message)
            sys.stdout.flush()
        else:
            log.info(message)

    def _loadConfig(self):
        self.config = ConfigParser()
        self.config.read(self.config_filename)
        if not self.config.has_section(self.config_section):
            self.config.add_section(self.config_section)

    def _storeConfig(self):
        with open(self.config_filename, 'wb') as configfile:
            self.config.write(configfile)

    def _getConfig(self, option, default=None):
        try:
            return self.config.get(self.config_section, option)
        except NoOptionError:
            return default

    def _setConfig(self, option, value):
        self.config.set(self.config_section, option, value)

    def _execQuery(self, conn, sql, args=None):
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(sql, args)
            rows = cursor.fetchall()
            return rows
        finally:
            if cursor:
                cursor.close()

    def _countQuery(self, conn, sql, args=None):
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(sql, args)
            rows = cursor.fetchall()
            cursor.execute("SELECT FOUND_ROWS() AS num_rows")
            count = cursor.fetchone()['num_rows']
            return rows, count
        finally:
            if cursor:
                cursor.close()

    def _add_details(self, conn, evids, events_by_evid):
        """
        Queries the database for event details for all of the events with the specified
        event ids. Each returned detail is added to the event dictionary for the event
        in events_by_evid.
        """
        query = "SELECT evid, name, value FROM detail WHERE evid IN (%s)" % _IN_CLAUSE(evids)
        rows = self._execQuery(conn, query)
        for row in rows:
            evid = row['evid']
            event = events_by_evid[evid]
            if not 'details' in event:
                event['details'] = {}
            event['details'][row['name']] = row['value']

    def _add_logs(self, conn, evids, events_by_evid):
        """
        Queries the database for event logs for all of the events with the specified
        event ids. Each returned log is added to the event dictionary for the event
        in events_by_evid.
        """
        query = "SELECT * FROM log WHERE evid IN (%s)" % _IN_CLAUSE(evids)
        rows = self._execQuery(conn, query)
        for row in rows:
            evid = row.pop('evid')
            event = events_by_evid[evid]
            if not 'logs' in event:
                event['logs'] = []
            event['logs'].append(row)

    def _page_rows(self, conn, status=True):
        """
        Pages through rows in the database in either the status or history
        table. After returning a batch of rows, the location of the last
        processed event is persisted to disk to ensure we resume from the
        right location in case the process is aborted for any reason.
        """
        table = 'status' if status else 'history'

        offset = 0
        last_evid = self._getConfig('%s_last_evid' % table)
        where = "WHERE evid > '%s'" % escape_string(last_evid) if last_evid else ''

        if last_evid:
            num_rows_query = "SELECT SQL_CALC_FOUND_ROWS evid FROM %s %s LIMIT 0" % (table, where)
            num_rows = self._countQuery(conn, num_rows_query)[1]
        else:
            num_rows_query = "SELECT COUNT(*) AS num_rows FROM %s" % table
            num_rows = self._execQuery(conn, num_rows_query)[0]['num_rows']

        if not num_rows:
            self._output("No events to migrate from %s" % table)
            return

        query = "SELECT * FROM %s %s ORDER BY evid LIMIT %%s OFFSET %%s" % (table, where)
        rows = self._execQuery(conn, query, (self.options.batchsize, offset))
        while not self._shutdown and rows:
            self._progress("Processing events in %s: [%d/%d]" % (table, offset, num_rows))
            evids = []
            events_by_evid = {}
            for row in rows:
                evid = row['evid']
                events_by_evid[evid] = row
                evids.append(evid)
            self._add_details(conn, evids, events_by_evid)
            self._add_logs(conn, evids, events_by_evid)
            yield rows
            self._setConfig('%s_last_evid' % table, rows[-1]['evid'])
            self._storeConfig()
            if self.options.sleep:
                log.debug("Pausing event migration for %s seconds" % self.options.sleep)
                sleep(self.options.sleep)
            offset += self.options.batchsize
            rows = self._execQuery(conn, query, (self.options.batchsize, offset))

        if not self._shutdown:
            self._progress("Processing events in %s: [%d/%d]\n" % (table, num_rows, num_rows))


    def _event_to_zep_raw_event(self, event):
        """
        Converts an event occurrence into a ZepRawEvent (required for running through
        zeneventd pipes).
        """
        zepRawEvent = ZepRawEvent()
        zepRawEvent.event.CopyFrom(event)
        return zepRawEvent

    def _merge_tags(self, zep_raw_event, event):
        """
        Merges results from the identification and tagging pipes into the event
        occurrence to be published. This will take the element_uuid, element_sub_uuid, titles
        and tags from the ZEP raw event and copy them to the appropriate place on
        the event occurrence.
        """
        raw_actor = zep_raw_event.event.actor
        event_actor = event.actor
        for field in ('element_uuid', 'element_sub_uuid', 'element_title', 'element_sub_title'):
            if raw_actor.HasField(field):
                setattr(event_actor, field, getattr(raw_actor, field))
        event.tags.extend(imap(deepcopy, zep_raw_event.event.tags))

    def _migrate_events(self, conn, publisher, status):
        converter = EventConverter(self.dmd, status)
        manager = Manager(self.dmd)
        pipes = (IdentifierPipe(manager), AddDeviceContextAndTagsPipe(manager),
                 AssignDefaultEventClassAndTagPipe(manager))
        routing_key = 'zenoss.events.summary' if status else 'zenoss.events.archive'

        taggers = {
            EventProxy.DEVICE_CLASS_DETAIL_KEY: (self.dmd.Devices, DeviceClass),
            EventProxy.DEVICE_GROUPS_DETAIL_KEY: (self.dmd.Groups, DeviceGroup),
            EventProxy.DEVICE_LOCATION_DETAIL_KEY: (self.dmd.Locations, Location),
            EventProxy.DEVICE_SYSTEMS_DETAIL_KEY: (self.dmd.Systems, System),
        }

        try:
            for event_rows in self._page_rows(conn, status):
                with AmqpTransaction(publisher.channel):
                    for mapping_event_context in imap(converter.convert, event_rows):
                        if self._shutdown:
                            raise ShutdownException()
                        occurrence = mapping_event_context.occurrence
                        zep_raw_event = self._event_to_zep_raw_event(occurrence)
                        event_ctx = EventContext(log, zep_raw_event)
                        for pipe in pipes:
                            pipe(event_ctx)

                        # Clear tags for device class, location, systems, groups from current device
                        event_ctx.eventProxy.tags.clearType(AddDeviceContextAndTagsPipe.DEVICE_TAGGERS.keys())

                        # Resolve tags from original fields in the event
                        for detail in occurrence.details:
                            if detail.name in taggers:
                                organizer_root, organizer_cls = taggers[detail.name]
                                tags = set()
                                for val in detail.value:
                                    try:
                                        obj = organizer_root.unrestrictedTraverse(str(val[1:]))
                                        if isinstance(obj, organizer_cls):
                                            tags.update(manager.getUuidsOfPath(obj))
                                    except Exception:
                                        if log.isEnabledFor(logging.DEBUG):
                                            log.debug("Unable to resolve UUID for %s", val)
                                if tags:
                                    event_tag = occurrence.tags.add()
                                    event_tag.type = detail.name
                                    event_tag.uuid.extend(tags)

                        self._merge_tags(zep_raw_event, occurrence)
                        if log.isEnabledFor(logging.DEBUG):
                            log.debug("Migrated event: %s", mapping_event_context.summary)

                        publisher.publish("$MigratedEvents", routing_key, mapping_event_context.summary,
                                          createQueues=("$ZepMigratedEventSummary","$ZepMigratedEventArchive"))
        except ShutdownException:
            pass

    def _sigterm(self, signum=None, frame=None):
        log.debug('SIGTERM signal caught')
        self._shutdown = True
        self._output('\nShutting down...')

    def run(self):
        signal(SIGTERM, self._sigterm)
        signal(SIGINT, self._sigterm)
        # Try to avoid stacktraces from interrupted signal calls
        siginterrupt(SIGTERM, False)
        siginterrupt(SIGINT, False)

        if self.options.restart:
            if os.path.exists(self.config_filename):
                os.remove(self.config_filename)

        self._loadConfig()
        if self.options.batchsize <= 0:
            self.parser.error('Invalid argument for --batchsize parameter - must be positive')
        if self.options.sleep < 0:
            self.parser.error('Invalid argument for --sleep parameter')

        if not self.options.fetchArgs:
            if not self.options.evtuser or self.options.evtpass is None:
                self.parser.error('Required arguments --evtuser and --evtpass must be provided when using '
                                  '--dont-fetch-args')
        else:
            zem = self.dmd.ZenEventManager
            self.options.evthost = zem.host
            self.options.evtport = zem.port
            self.options.evtuser = zem.username
            self.options.evtpass = zem.password
            self.options.evtdb = zem.database
        conn = None
        publisher = None
        try:
            conn = connect(host=self.options.evthost,
                           user=self.options.evtuser,
                           passwd=self.options.evtpass,
                           db=self.options.evtdb,
                           port=self.options.evtport,
                           cursorclass=DictCursor,
                           use_unicode=True)
            conn.autocommit(1)

            publisher = getUtility(IQueuePublisher)

            # Migrate status
            self._migrate_events(conn, publisher, True)

            # Migrate history
            self._migrate_events(conn, publisher, False)
            
        except Exception as e:
            if log.isEnabledFor(logging.DEBUG):
                log.exception('Error migrating events')
            print >>sys.stderr, "Failed to migrate events: %s" % e
        finally:
            if publisher:
                publisher.close()
            if conn:
                conn.close()


if __name__ == '__main__':
    migrate = ZenEventMigrate()
    migrate.run()

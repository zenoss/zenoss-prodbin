###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from propertyMonitor import PropertyMonitor
"""PropertyMonitor will implement properties for attributes defined in 'fields'
   and 'readonly_fields' class attributes.  Any updates to attributes listed
   in 'fields' can be obtained after the event processing script has run.
   Entries in the 'compatibility_map' will generate property definitions which
   will access the underlying data for the new-named attribute.
"""

class Event(object):
    __metaclass__ = PropertyMonitor
    
    fields = ("fingerprint status severity summary message event_class "
            "event_key event_class_key event_group component device service "
            "_clearClasses")
    # fingerprint = "Dynamically generated fingerprint that allows the system to perform de-duplication on repeating events that share similar characteristics."
    # message = "event message"
    # severity = "event severity"
    # event_class = "Name of the event class into which this event has been created or mapped."
    # event_key = "Free-form text field (maximum 128 characters) that allows another specificity key to be used to drive the de-duplication and auto-clearing correlation process."
    # event_class_key = "Free-form text field (maximum 128 characters) that is used as the first step in mapping an unknown event into an event class."
    # event_group = "Free-form text field (maximum 64 characters) that can be used to group similar types of events. This is primarily an extension point for customization. Currently not used in a standard system."
    # component Free-form text field (maximum 255 characters) that allows additional context to be given to events (for example, the interface name for an interface threshold event).
    # device
    # service
    
    readonly_fields = ("evid uuid created_time monitor ip_address production_state agent "
            "class_name_uuid location_uuid syslog_facility syslog_priority nt_event_code "
            "device_priority event_class_mapping_uuid count "
            "acknowledged_by_user_uuid cleared_by_event_uuid suppressed_by_event_uuid "
            "first_seen_time last_seen_time")
    # evid, uuid Unique identifier for this event
    # created_time   Timestamp when this event was created (occurred? what is the difference?)
    # monitor   In a distributed setup, contains the name of the collector from which the event originated.
    # ip_address 
    # production_state  Production state of the device when the event occurred. If an event is still active when a device's production state is changed, the event's prodState will be updated accordingly.
    # agent     Typically the name of the daemon that generated the event. For example, an SNMP threshold event will have zenperfsnmp as its agent.
    # class_name_uuid   Device class of the device that the event is related to.
    # location_uuid     Location of the device that the event is related to.
    # syslog_facility   Only present on events coming from syslog. The syslog facility.
    # syslog_priority   Only present on events coming from syslog. The syslog priority.
    # nt_event_code     Only present on events coming from Windows event log. The NT Event ID.
    # device_priority   Priority of the device that the event is related to.
    # event_class_mapping_uuid  If this event was matched by one of the configured event class mappings, contains the name of that mapping rule.
    # ownerid   Name of the user who acknowledged this event.
    # clearid   Only present on events in history that were auto-cleared. The evid of the event that cleared this one.
    # suppid    If this event has been suppressed by another event, then suppid contains the other event's evid.

    # map legacy names for these attributes to new names, for compatibility with old transforms
    compatibility_map = { 
        "created" : "created_time",
        "eventClass" : "event_class",
        "eventClassKey" : "event_class_key",
        "eventClassMapping" : "event_class_mapping_uuid",
        "eventGroup" : "event_group",
        "eventKey" : "event_key",
        "dedupid" : "fingerprint",
        "manager" : "monitor",
        "ntevid" : "nt_event_code",
        "facility" : "syslog_facility",
        "priority" : "syslog_priority",
        "evid" : "uuid",
        # to be copied from Device, if available
        "ipAddress" : "ip_address",
        "prodState" : "production_state",
        "DeviceClass" : "class_name_uuid",
        "Location" : "location_uuid",
        "DevicePriority" : "device_priority",
        # control attributes sent in Event, but really attributes of the EventContext
        "eventState" : "status",
        "stateChange" : "status_change_time",
        "firstSeen" : "first_seen_time",
        "lastSeen" : "last_seen_time",
        "ownerid" : "acknowledged_by_user_uuid",
        "clearid" : "cleared_by_event_uuid",
        "suppid" : "suppressed_by_event_uuid",
        "_action" : "status",
        }
        
class EventSummary(object):
    __metaclass__ = PropertyMonitor
    
    readonly_fields = "status_change_time first_seen_time last_seen_time count events"
    # stateChange = "last time information about the event changed"
    # firstTime = "first time event occurred"
    # lastTime = "most recent time event occurred"
    # count = "number of times event occurred between firstTime and lastTime"
    # events = "list of previous events"

    
class EventContext(object):
    __metaclass__ = PropertyMonitor

    fields = "action"
    # action = "new/history/drop"
    
    readonly_fields = "summary"
    # summary = EventSummary()

    
class Device(object):
    __metaclass__ = PropertyMonitor

    readonly_fields = ("uuid id title priority production_state "
            "device_priority ip_address class_name_uuid location_uuid "
            "groups systems services")
    # uuid
    # id
    # title
    # priority = "A numeric value: 0 (Trivial), 1 (Lowest), 2 (Low), 3 (Normal), 4 (High), 5 (Highest)"
    # ipAddress
    # className
    # location
    # groups
    # systems
    # services
    compatibility_map = { 
        "ipAddress" : "ip_address",
        "prodState" : "production_state",
        "className" : "class_name_uuid",
        "location" : "location_uuid",
        "priority" : "device_priority",
        }

class Component(object):
    __metaclass__ = PropertyMonitor
    
    readonly_fields = "uuid id device"
    # uuid = "unique component identifier"
    # id
    # device

class Service(object):
    __metaclass__ = PropertyMonitor
    
    readonly_fields = "uuid title"
    # uuid = "unique service identifier"
    # title = "service title"
    
if 0: # for epydoc only
    # globals
    evt = Event()
    ctx = EventContext()
    dev = Device()
    device = dev
    component = Component() # may be None
    service = Service() # may be None


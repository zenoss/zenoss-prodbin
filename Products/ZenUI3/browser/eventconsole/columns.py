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

"""
This module describes the parameters for columns that may appear in the event
console. This is used both to generate the JavaScript defining the columns and
to evaluate filters.
"""

from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_NEW,
    STATUS_ACKNOWLEDGED,
    STATUS_AGED,
    STATUS_CLEARED,
    STATUS_CLOSED,
    STATUS_SUPPRESSED,
    SEVERITY_CRITICAL,
    SEVERITY_CLEAR,
    SEVERITY_DEBUG,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING
)

COLUMN_CONFIG = {

    'dedupid'   : dict(
        header='Deduplication ID',
        filter='textfield'),

    'evid'      : dict(
        header='Event ID',
        filter='textfield'),

    'device'    : dict(
        header='Device',
        filter='textfield',
        renderer='Zenoss.render.linkFromGrid'),

    'component' : dict(
        header='Component',
        filter='textfield',
        renderer='Zenoss.render.DeviceComponent'),

    'eventClass': dict(
        header='Event Class',
        filter='textfield',
        renderer='Zenoss.render.linkFromGrid'),

    'eventKey'  : dict(
        header='Event Key',
        filter='textfield'),

    'summary'   : dict(
        header='Summary',
        filter='textfield'),

    'message'   : dict(
        header='Message',
        filter='textfield'),

    'severity'  : dict(
        header='Severity',
        width=60,
        filter={
            'xtype':'multiselectmenu',
            'text':'...',
            'source': [{
                'value': SEVERITY_CRITICAL,
                'name': 'Critical'
            },{
                'value': SEVERITY_ERROR,
                'name': 'Error'
            },{
                'value': SEVERITY_WARNING,
                'name': 'Warning'
            },{
                'value': SEVERITY_INFO,
                'name':'Info'
            },{
                'value': SEVERITY_DEBUG,
                'name':'Debug',
                'checked':False
            },{
                'value': SEVERITY_CLEAR,
                'name':'Clear',
                'checked':False
            }]
        },
        renderer='Zenoss.util.render_severity'),

    'eventState': dict(
        header='Status',
        width=60,
        filter={
            # Values are offset from actual values by -1
            'xtype':'multiselectmenu',
            'text':'...',
            'source':[{
                'value':STATUS_NEW,
                'name':'New'
            },
            {
                'value':STATUS_ACKNOWLEDGED,
                'name':'Acknowledged'
            },
            {
                'value':STATUS_SUPPRESSED,
                'name':'Suppressed',
                'checked':False
            },
            {
                'value':STATUS_CLOSED,
                'name':'Closed',
                'checked':False
            },
            {
                'value':STATUS_CLEARED,
                'name':'Cleared',
                'checked':False
            },
            {
                'value':STATUS_AGED,
                'name':'Aged',
                'checked':False
            }]
        },
        renderer='Zenoss.util.render_status'),

    'eventClassKey': dict(
        header='Event Class Key',
        filter='textfield'),

    'eventGroup': dict(
        header='Event Group',
        filter='textfield'),

    'stateChange': dict(
        header='State Change',
        filter='datefield'),

    'firstTime' : dict(
        header='First Seen',
        filter={
            'xtype':'datefield',
            'format':'Y-m-d H:i:s'
        },
        width=120,
        renderer='Ext.util.Format.dateRenderer(Zenoss.date.ISO8601Long)'),

    'lastTime'  : dict(
        header='Last Seen',
        filter={
            'xtype':'datefield',
            'format':'Y-m-d H:i:s'
        },
        width=120,
        renderer='Ext.util.Format.dateRenderer(Zenoss.date.ISO8601Long)'),

    'count'     : dict(
        header='Count',
        width=60,
        filter={
            'xtype': 'textfield',
            'vtype': 'numcmp'
        }
    ),

    'prodState' : dict(
        header='Production State',
        filter={
            'xtype':'multiselect-prodstate'
        }),

    'agent'     : dict(
        header='Agent',
        filter='textfield'),

    'DeviceClass': dict(
        header='Device Class',
        filter='textfield',
        renderer='Zenoss.render.linkFromGrid'
        ),

    'Location'  : dict(
        header='Location',
        filter='textfield',
        renderer='Zenoss.render.linkFromGrid'
        ),

    'Systems'   : dict(
        header='Systems',
        filter='textfield'),

    'DeviceGroups': dict(
        header='Groups',
        filter='textfield',
        renderer='Zenoss.util.render_device_group_link'),

    'ipAddress' : dict(
        header='IP Address',
        filter='textfield'),

    'facility' : dict(
        header='Facility',
        filter='textfield'),

    'priority' : dict(
        header='Priority',
        filter={
            'xtype':'multiselectmenu',
            'source':[{
                'value':5,
                'name':'Highest'
            },{
                'value':4,
                'name':'High'
            },{
                'value':3,
                'name':'Normal'
            },{
                'value':2,
                'name':'Low'
            },{
                'value':1,
                'name':'Lowest'
            },{
                'value':0,
                'name':'Trivial'
            }]
        }),

    'ntevid': dict(
        header='NT Event ID',
        filter='textfield'),

    'ownerid': dict(
        header='Owner',
        filter='textfield'),

    'clearid': dict(
        header='Clear ID',
        filter='textfield'),

    'DevicePriority': dict(
        header='Device Priority',
        filter='textfield'),

    'eventClassMapping': dict(
        header='Event Class Mapping',
        filter='textfield'),

    'monitor': dict(
        header='Collector',
        filter='textfield')
}

ARCHIVE_COLUMN_CONFIG = COLUMN_CONFIG.copy()
ARCHIVE_COLUMN_CONFIG['eventState'] = dict(
        header='Status',
        width=60,
        filter={
            # Values are offset from actual values by -1
            'xtype':'multiselectmenu',
            'text':'...',
            'source':[{
                'value':STATUS_CLOSED,
                'name':'Closed',
            },
            {
                'value':STATUS_CLEARED,
                'name':'Cleared',
            },
            {
                'value':STATUS_AGED,
                'name':'Aged',
            }]
        },
        renderer='Zenoss.util.render_status'
)
ARCHIVE_COLUMN_CONFIG['severity'] = dict(
        header='Severity',
        width=60,
        filter={
            'xtype':'multiselectmenu',
            'text':'...',
            'source': [{
                'value': SEVERITY_CRITICAL,
                'name': 'Critical'
            },{
                'value': SEVERITY_ERROR,
                'name': 'Error'
            },{
                'value': SEVERITY_WARNING,
                'name': 'Warning'
            },{
                'value': SEVERITY_INFO,
                'name':'Info'
            },{
                'value': SEVERITY_DEBUG,
                'name':'Debug',
                'checked':False
            },{
                'value': SEVERITY_CLEAR,
                'name':'Clear',
            }]
        },
        renderer='Zenoss.util.render_severity'
)
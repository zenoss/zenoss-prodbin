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
        renderer='Zenoss.util.render_linkable'),

    'component' : dict(
        header='Component',
        filter='textfield',
        renderer='Zenoss.util.render_linkable'),

    'eventClass': dict(
        header='Event Class',
        filter='textfield',
        renderer='Zenoss.util.render_linkable'),

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
                'value':5,
                'text': 'Critical'
            },{
                'value':4,
                'text': 'Error'
            },{
                'value':3,
                'text': 'Warning'
            },{
                'value':2,
                'text':'Info'
            },{
                'value':1,
                'text':'Debug',
                'checked':False
            },{
                'value':0,
                'text':'Clear',
                'checked':False
            }]
        },
        renderer='Zenoss.util.render_severity'),

    'eventState': dict(
        header='Status',
        width=60,
        filter={
            'xtype':'multiselectmenu',
            'text':'...',
            'source':[{
                'value':0,
                'text':'New'
            },{
                'value':1,
                'text':'Acknowledged'
            },{
                'value':2,
                'text':'Suppressed',
                'checked':False
            }
            ]
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
        filter='textfield'),

    'prodState' : dict(
        header='Production State',
        filter={
            'xtype':'multiselectmenu',
            'text':'...',
            'source':[{
                'value':1000,
                'text':'Production'
            },{
                'value':500,
                'text':'Pre-Production',
                'checked':False
            },{
                'value':400,
                'text':'Test',
                'checked':False
            },{
                'value':300,
                'text':'Maintenance',
                'checked':False,
            },{
                'value':-1,
                'text':'Decommissioned',
                'checked':False
            }
            ]
        }),

    'suppid'    : dict(
        header='Supplemental ID',
        filter='textfield'),

    'manager'   : dict(
        header='Manager',
        filter='textfield'),

    'agent'     : dict(
        header='Agent',
        filter='textfield'),

    'DeviceClass': dict(
        header='Device Class',
        filter='textfield'),

    'Location'  : dict(
        header='Location',
        filter='textfield'),

    'Systems'   : dict(
        header='Systems',
        filter='textfield'),

    'DeviceGroups': dict(
        header='Groups',
        filter='textfield'),

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
                'text':'Highest'
            },{
                'value':4,
                'text':'High'
            },{
                'value':3,
                'text':'Normal'
            },{
                'value':2,
                'text':'Low'
            },{
                'value':1,
                'text':'Lowest'
            },{
                'value':0,
                'text':'Trivial'
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


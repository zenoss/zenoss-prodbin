/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

(function(){

Ext.ns('Zenoss');

// the store that holds the records for the device grid
var deviceStore = {
    xtype: 'directstore',
    autoLoad: {params:{id: 'Processes'}},
    
    // Ext.data.DirectProxy config
    api: {read: Zenoss.remote.ProcessRouter.getDevices},
    
    // Ext.data.JsonReader config
    root: 'data',
    fields: [
        {name: 'device', type: 'string'},
        {name: 'ipAddress', type: 'int'},
        {name: 'productionState', type: 'string'},
        {name: 'events', type: 'auto'},
        {name: 'availability', type: 'float'}
    ],
    
}; // deviceStore

// renders IP address in dotted-decimal format
function ipAddressRenderer(value) {
    return Zenoss.util.num2dot(value);
}

// templates for the events renderer
var iconTemplate = new Ext.Template('<div style="float: left;" ' + 
                     'class="severity-icon-small {severity}"></div>');
iconTemplate.compile();
                     
var countTemplate = new Ext.Template('<div style="' +
        'float: left; ' +
        'vertical-align: 27%;' +
        'margin-left: .5em;' +
        'margin-right: 1.5em;">' +
        '{count}</div>');
countTemplate.compile();

// renders events using icons for critical, error and warning
function eventsRenderer(value) {
    var result = '';
    Ext.each(['critical', 'error', 'warning'], function(severity) {
        result += iconTemplate.apply({severity: severity});
        result += countTemplate.apply({count: value[severity]});
    });
    return result;
}

// renders availability as a percentage with 3 digits after decimal point
function availabilityRenderer(value) {
    return Ext.util.Format.number(value*100, '0.000%');
}

// the column model for the device grid
var deviceColumnModel = new Ext.grid.ColumnModel({
    defaults: {
        sortable: false,
        menuDisabled: true,
        width: 200
    },
    columns: [{dataIndex: 'device',
               header: _t('Device'),
               id: 'device'
               },
              {dataIndex: 'ipAddress',
               header: _t('IP Address'),
               renderer: ipAddressRenderer
               },
              {dataIndex: 'productionState',
               header: _t('Production State')
               },
              {dataIndex: 'events',
                header: _t('Events'),
                renderer: eventsRenderer
                },
              {dataIndex: 'availability',
               header: _t('Availability'), 
               id: 'availability',
               renderer: availabilityRenderer
               }] // columns
});

var deviceConfig = {
    id: 'deviceGrid',
    store: deviceStore,
    colModel: deviceColumnModel,
    autoExpandColumn: 'availability',
    stripeRows: true
};

/**
 * @class Zenoss.DeviceGridPanel
 * @extends Ext.grid.GridPanel
 * Shows devices in a filtered grid panel similar to that on the event console
 * Fixed columns. A drag source.
 * Used on:
 *   Processes
 *   Services
 *   Manufacturers
 *   Dashboard
 *   Devices
 * @constructor
 */
Zenoss.DeviceGridPanel = Ext.extend(Ext.grid.GridPanel, {

    constructor: function(userConfig) {
        var config = Ext.apply(deviceConfig, userConfig);
        Zenoss.DeviceGridPanel.superclass.constructor.call(this, config);
    }

}); // DeviceGridPanel

Ext.reg('DeviceGridPanel', Zenoss.DeviceGridPanel);

// the store that holds the records for the device grid
var eventStore = {
    xtype: 'directstore',
    autoLoad: {params:{id: 'Processes'}},
    
    // Ext.data.DirectProxy config
    api: {read: Zenoss.remote.ProcessRouter.getEvents},
    
    // Ext.data.JsonReader config
    root: 'data',
    fields: [
        {name: 'severity', type: 'auto'},
        {name: 'device', type: 'string'},
        {name: 'component', type: 'string'},
        {name: 'eventClass', type: 'string'},
        {name: 'summary', type: 'string'}
    ],
    
}; // eventStore

function severityRenderer(value) {
    return Zenoss.util.convertSeverity(value);
}

var eventColumnModel = new Ext.grid.ColumnModel({
    defaults: {
        sortable: false,
        menuDisabled: true,
        width: 200
    },
    columns: [{dataIndex: 'severity',
               header: _t('Severity'),
               id: 'severity',
               renderer: severityRenderer
               },
              {dataIndex: 'device',
               header: _t('Device')
               },
              {dataIndex: 'component',
               header: _t('Component')
               },
              {dataIndex: 'eventClass',
                header: _t('Event Class')
                },
              {dataIndex: 'summary',
               header: _t('Summary'), 
               id: 'summary'
               }] // columns
}); // eventColumnModel

var eventConfig = {
    id: 'eventGrid',
    store: eventStore,
    colModel: eventColumnModel,
    autoExpandColumn: 'summary',
    stripeRows: true
};

/**
 * @class Zenoss.EventGridPanel
 * @extends Ext.grid.GridPanel
 * Shows events in a filtered grid panel similar to that on the event console
 * Fixed columns. A drag source.
 * @constructor
 */
Zenoss.EventGridPanel = Ext.extend(Ext.grid.GridPanel, {
    
    constructor: function(userConfig) {
        var config = Ext.apply(eventConfig, userConfig);
        Zenoss.EventGridPanel.superclass.constructor.call(this, config);
    }
    
}); // EventGridPanel

Ext.reg('EventGridPanel', Zenoss.EventGridPanel);

function createToggleHandler(itemIndex) {
    return function(button, pressed) {
        if (pressed) {
            Ext.getCmp('cardPanel').getLayout().setActiveItem(itemIndex);
        }
    }
}

/**
 * @class Zenoss.ViewButton
 * @extends Ext.Button
 * A button that toggles between cards in a panel with a card layout.
 * @constructor
 */
Zenoss.ViewButton = Ext.extend(Ext.Button, {

    constructor: function(userConfig) {

        var baseConfig = {
            toggleHandler: createToggleHandler(userConfig.__item_index__),
            enableToggle: true,
            toggleGroup: 'view',
            allowDepress: false,
            width: 80
        };

        delete userConfig.__item_index__;
        var config = Ext.apply(baseConfig, userConfig);
        Zenoss.ViewButton.superclass.constructor.call(this, config);
    }

});

Ext.reg('ViewButton', Zenoss.ViewButton);

/**
 * @class Zenoss.DeviceEventPanel
 * @extends Ext.Button
 * A Panel with a card layout and toolbar buttons for switching between the
 * cards.
 * @constructor
 */
Zenoss.DeviceEventPanel = Ext.extend(Ext.Panel, {
    
    constructor: function(userConfig) {
        var config = Ext.apply(this.baseConfig, userConfig);
        Zenoss.DeviceEventPanel.superclass.constructor.call(this, config);
    },
    
    baseConfig: {
        id: 'cardPanel',
        layout: 'card',
        activeItem: 0,
        tbar: [
            {
                xtype: 'tbtext',
                text: _t('View: ')
            }, {
                xtype: 'ViewButton',
                id: 'devicesButton',
                text: _t('Devices'),
                __item_index__: 0,
                pressed: true
            }, {
                xtype: 'ViewButton',
                id: 'eventsButton',
                text: _t('Events'),
                __item_index__: 1
            }
        ],
        items: [
            {xtype: 'DeviceGridPanel'},
            {xtype: 'EventGridPanel'}
        ]
    }
    
});

Ext.reg('DeviceEventPanel', Zenoss.DeviceEventPanel);

})(); // end of function namespace scoping

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

var baseConfig = {
    id: 'deviceGrid',
    store: deviceStore,
    colModel: deviceColumnModel,
    autoExpandColumn: 'availability',
    stripeRows: true
}

Ext.ns('Zenoss');

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
        var config = Ext.apply(baseConfig, userConfig);
        Zenoss.DeviceGridPanel.superclass.constructor.call(this, config);
    } // constructor
    
}); // DeviceGridPanel

Ext.reg('DeviceGridPanel', Zenoss.DeviceGridPanel);

})(); // end of function namespace scoping

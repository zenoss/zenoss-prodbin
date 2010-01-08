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

// templates for the events renderer
var iconTemplate = new Ext.Template('<'+'div style="float: left;" ' + 
                     'class="severity-icon-small {severity}"><'+'/div>');
iconTemplate.compile();
                     
var countTemplate = new Ext.Template('<'+'div style="' +
        'float: left; ' +
        'vertical-align: 27%;' +
        'margin-left: .5em;' +
        'margin-right: 1.5em;">' +
        '{count}<'+'/div>');
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

Zenoss.DeviceColumnModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config) {
        var config = config || {};
        Ext.applyIf(config, {
            defaults: {
                sortable: false,
                menuDisabled: true,
                width: 200
            },
            columns: [{
                dataIndex: 'name',
                header: _t('Device'),
                id: 'name'
            },{
                id: 'ipAddress',
                dataIndex: 'ipAddress',
                header: _t('IP Address'),
                renderer: Zenoss.util.num2dot
            },{
                id: 'productionState',
                dataIndex: 'productionState',
                header: _t('Production State')
            },{
                id: 'events',
                dataIndex: 'events',
                header: _t('Events'),
                renderer: eventsRenderer
            },{
                dataIndex: 'availability',
                header: _t('Availability'), 
                id: 'availability',
                renderer: availabilityRenderer
            }] // columns
        }); // Ext.applyIf
        Zenoss.DeviceColumnModel.superclass.constructor.call(this, config);
    } // constructor
});
Ext.reg('DeviceColumnModel', Zenoss.DeviceColumnModel);


/**
 * Device data store definition
 * @constructor
 */
Zenoss.DeviceStore = Ext.extend(Ext.ux.grid.livegrid.Store, {

    constructor: function(config) {
        var config = config || {};
        Ext.applyIf(config, {
            bufferSize: 50,
            defaultSort: {field: 'name', direction:'ASC'},
            sortInfo: {field: 'name', direction:'ASC'},
            proxy: new Ext.data.DirectProxy({
                directFn: Zenoss.remote.DeviceRouter.getDevices
            }),
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'devices',
                totalProperty: 'totalCount'
            },[
                  {name: 'name', type: 'string'},
                  {name: 'ipAddress', type: 'int'},
                  {name: 'productionState', type: 'string'},
                  {name: 'events', type: 'auto'},
                  {name: 'availability', type: 'float'}
              ]
            )
        });
        Zenoss.DeviceStore.superclass.constructor.call(this, config);
    }
});

Ext.reg('DeviceStore', Zenoss.DeviceStore);


Zenoss.SimpleDeviceGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    constructor: function(config) {
        var store = {xtype:'DeviceStore'};
        if (!Ext.isEmpty(config.directFn)) {
            Ext.apply(store, {
                proxy: new Ext.data.DirectProxy({
                    directFn: config.directFn
                })
            });
        }
        var config = Ext.applyIf(config || {}, {
            cm: new Zenoss.DeviceColumnModel({
                menuDisabled: true
            }),
            sm: new Zenoss.ExtraHooksSelectionModel,
            store: store,
            enableDragDrop: false,
            border:false,
            rowSelectorDepth: 5,
            autoExpandColumn: 'name',
            stripeRows: true
        });
        Zenoss.SimpleDeviceGridPanel.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.getStore().load({params:{uid:uid}});
    }
});
Ext.reg('SimpleDeviceGridPanel', Zenoss.SimpleDeviceGridPanel);


Zenoss.DeviceGridPanel = Ext.extend(Zenoss.FilterGridPanel,{
    constructor: function(config) {
        var store = {xtype:'DeviceStore'};
        if (!Ext.isEmpty(config.directFn)) {
            Ext.apply(store, {
                proxy: new Ext.data.DirectProxy({
                    directFn: config.directFn
                })
            });
        }
        Ext.applyIf(config, {
            store: store,
            enableDragDrop: false,
            border: false,
            rowSelectorDepth: 5,
            view: new Zenoss.FilterGridView({
                nearLimit: 20,
                loadMask: {msg: 'Loading. Please wait...'}
            }),
            autoExpandColumn: 'name',
            cm: new Zenoss.DeviceColumnModel(),
            sm: new Zenoss.ExtraHooksSelectionModel(),
            stripeRows: true
        });
        Zenoss.DeviceGridPanel.superclass.constructor.call(this, config);
    }
});
Ext.reg('DeviceGridPanel', Zenoss.DeviceGridPanel);


})(); // end of function namespace scoping

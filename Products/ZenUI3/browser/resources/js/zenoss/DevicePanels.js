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


Zenoss.DeviceColumnModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            columns: [{
                dataIndex: 'name',
                header: _t('Device'),
                id: 'name',
                renderer: function(name, row, record) {
                    return Zenoss.render.Device(record.data.uid, name);
                }
            },{
                id: 'ipAddress',
                dataIndex: 'ipAddress',
                header: _t('IP Address'),
                filter: {xtype: 'ipaddressfield'},
                renderer: Zenoss.util.num2dot
            },{
                dataIndex: 'uid',
                header: _t('Device Class'), 
                id: 'deviceClass',
                renderer: Zenoss.render.DeviceClass
            },{
                id: 'productionState',
                dataIndex: 'productionState',
                width: 100,
                filter: {
                    xtype: 'multiselectmenu',
                    'text':'...',
                    'source':[{
                        'value':1000,
                        'text':'Production'
                    },{
                        'value':500,
                        'text':'Pre-Production',
                        'checked':false
                    },{
                        'value':400,
                        'text':'Test',
                        'checked':false
                    },{
                        'value':300,
                        'text':'Maintenance',
                        'checked':false
                    },{
                        'value':-1,
                        'text':'Decommissioned',
                        'checked':false
                    }]
                },
                header: _t('Production State')
            },{
                id: 'events',
                sortable: false,
                filter: false,
                dataIndex: 'events',
                header: _t('Events'),
                renderer: Zenoss.render.events
            }] // columns
        }); // Ext.applyIf
        config.defaults = Ext.applyIf(config.defaults || {}, {
            sortable: false,
            menuDisabled: true,
            width: 200
        });
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
        config = config || {};
        Ext.applyIf(config, {
            autoLoad: true,
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
                  {name: 'uid', type: 'string'},
                  {name: 'name', type: 'string'},
                  {name: 'ipAddress', type: 'int'},
                  {name: 'productionState', type: 'string'},
                  {name: 'events', type: 'auto'},
                  {name: 'availability', type: 'float'}
              ])
        });
        Zenoss.DeviceStore.superclass.constructor.call(this, config);
    },
    loadRanges: function(ranges) {
        // We actually just want to send the ranges themselves, so we'll
        // short-circuit this so it doesn't try to turn them into uids in yet
        // another server request
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
        config = Ext.applyIf(config || {}, {
            cm: new Zenoss.DeviceColumnModel({
                menuDisabled: true
            }),
            sm: new Zenoss.ExtraHooksSelectionModel(),
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
    lastHash: null,
    constructor: function(config) {
        var store = { xtype:'DeviceStore' };
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
                nearLimit: 10,
                loadMask: {msg: 'Loading. Please wait...'}
            }),
            autoExpandColumn: 'name',
            cm: new Zenoss.DeviceColumnModel({defaults:{sortable:true}}),
            sm: new Zenoss.ExtraHooksSelectionModel(),
            stripeRows: true
        });
        Zenoss.DeviceGridPanel.superclass.constructor.call(this, config);
        this.store.proxy.on('load', 
            function(proxy, o, options) {
                this.lastHash = o.result.hash || this.lastHash;
            },
            this);
    }
});
Ext.reg('DeviceGridPanel', Zenoss.DeviceGridPanel);


})(); // end of function namespace scoping

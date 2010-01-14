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

// the column model for the device grid
Zenoss.EventStore = Ext.extend(Ext.ux.grid.livegrid.Store, {
    constructor: function(config) {
        Ext.applyIf(config, {
            proxy: new Ext.data.DirectProxy({
                directFn:Zenoss.remote.EventsRouter.query
            }),
            bufferSize: 100,
            defaultSort: {field:'severity', direction:'DESC'},
            sortInfo: {field:'severity', direction:'DESC'},
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'events',
                totalProperty: 'totalCount'
                }, [
                // List all possible columns. 
                // FIXME: This should come from the server.
                    'dedupid',
                    'evid',
                    'device',
                    'device_url',
                    'component',
                    'component_url',
                    'summary',
                    'eventState',
                    'eventClass',
                    'eventClass_url',
                    'eventKey',
                    'message',
                    'eventClassKey',
                    'eventGroup',
                    'prodState',
                    'suppid',
                    'manager',
                    'agent',
                    'DeviceClass',
                    'Location',
                    'Systems',
                    'DeviceGroups',
                    'ipAddress',
                    'facility',
                    'priority',
                    'ntevid',
                    'ownerid',
                    'clearid',
                    'DevicePriority',
                    'eventClassMapping',
                    'monitor',
                    {name:'count', type:'int'},
                    {name:'severity', type:'int'},
                    {name:'firstTime', type:'date', 
                        dateFormat:Zenoss.date.ISO8601Long},
                    {name:'lastTime', type:'date', 
                        dateFormat:Zenoss.date.ISO8601Long},
                    {name:'stateChange', type:'date',
                        dateFormat:Zenoss.date.ISO8601Long}
                ] // reader columns
            ) // reader
        }); // Ext.applyIf
        Zenoss.EventStore.superclass.constructor.call(this, config);
    } // constructor
}); // Ext.extend

Ext.reg('EventStore', Zenoss.EventStore);


Zenoss.SimpleEventColumnModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config) {
        var config = Ext.applyIf(config || {}, {
            defaults: {
                sortable: false,
                menuDisabled: true,
                width: 200
            },
            columns: [{
                dataIndex: 'severity',
                header: _t('Severity'),
                id: 'severity',
                renderer: Zenoss.util.convertSeverity
            },{
                dataIndex: 'device',
                header: _t('Device')
            },{
                dataIndex: 'component',
                header: _t('Component')
            },{
                dataIndex: 'eventClass',
                header: _t('Event Class')
            },{
                dataIndex: 'summary',
                header: _t('Summary'),
                id: 'summary'
            }] // columns
        }); // Ext.applyIf
        Zenoss.SimpleEventColumnModel.superclass.constructor.call(
            this, config);
    } // constructor
}); // Ext.extend

Ext.reg('SimpleEventColumnModel', Zenoss.SimpleEventColumnModel);


Zenoss.FullEventColumnModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config) {
        // Zenoss.env.COLUMN_DEFINITIONS comes from the server, and depends on
        // the resultFields associated with the context.
        // FIXME: This shouldn't come from the server.
        var config = Ext.applyIf(config || {}, {
            columns:Zenoss.env.COLUMN_DEFINITIONS
        });
        Zenoss.FullEventColumnModel.superclass.constructor.call(this, config);
    }
});
Ext.reg('FullEventColumnModel', Zenoss.FullEventColumnModel);


/**
 * @class Zenoss.SimpleEventGridPanel
 * @extends Ext.ux.grid.livegrid.GridPanel
 * Shows events in a grid panel similar to that on the event console.
 * Fixed columns. 
 * @constructor
 */
Zenoss.SimpleEventGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    constructor: function(config) {
        var store = {xtype:'EventStore'};
        if (!Ext.isEmpty(config.directFn)) {
            Ext.apply(store, {
                proxy: new Ext.data.DirectProxy({
                    directFn: config.directFn
                })
            });
        }
        Ext.applyIf(config, {
            id: 'eventGrid',
            stripeRows: true,
            stateId: Zenoss.env.EVENTSGRID_STATEID || 'default_eventsgrid',
            enableDragDrop: false,
            stateful: true,
            border: false,
            rowSelectorDepth: 5,
            autoExpandColumn: 'summary',
            store: store,
            cm: Ext.create({xtype: 'SimpleEventColumnModel'}),
            sm: new Zenoss.ExtraHooksSelectionModel(),
            autoExpandColumn: 'summary',
            view: new Ext.ux.grid.livegrid.GridView({
                nearLimit: 20,
                loadMask: {msg: 'Loading. Please wait...'},
                listeners: {
                    beforeBuffer: function(view, ds, idx, len, total, opts) {
                        opts.params.uid = view._context;
                    }
                }
            })
        }); // Ext.applyIf
        Zenoss.SimpleEventGridPanel.superclass.constructor.call(this, config);
    }, // constructor
    setContext: function(uid) {
        this.view._context = uid;
        this.view.updateLiveRows(this.view.rowIndex, true, true);
    }
}); // SimpleEventGridPanel

Ext.reg('SimpleEventGridPanel', Zenoss.SimpleEventGridPanel);


Zenoss.EventRainbow = Ext.extend(Ext.Toolbar.TextItem, {
    constructor: function(config) {
        var config = Ext.applyIf(config || {}, {
            height: 45,
            directFn: Zenoss.remote.DeviceRouter.getInfo,
            text: Zenoss.render.events({'critical':0, 'error':0, 'warning':0})
        });
        Zenoss.EventRainbow.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.directFn({uid:uid}, function(result){
            this.setText(Zenoss.render.events(result.data.events));
        }, this);
    }
});

Ext.reg('eventrainbow', Zenoss.EventRainbow);


})(); // end of function namespace scoping

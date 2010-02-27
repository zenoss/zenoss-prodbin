/*
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
*/

(function(){

Ext.ns('Zenoss');

var InstanceColumnModel = Ext.extend(Ext.grid.ColumnModel, {

    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            defaults: {
                menuDisabled: true
            },
            columns: [{
                id: 'device',
                dataIndex: 'device',
                header: _t('Device'),
                width: 200,
                renderer: function(device, row, record){
                    return Zenoss.render.link(device.uid);
               }
            }, {
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                width: 400
            }, {
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                width: 70,
                sortable: true
            }, {
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                width: 50
            }]
        });
        InstanceColumnModel.superclass.constructor.call(this, config);
    }

});

/**
 * Device data store definition
 * @constructor
 */
Zenoss.InstanceStore = Ext.extend(Ext.ux.grid.livegrid.Store, {

    constructor: function(config) {
        Ext.applyIf(config, {
            bufferSize: 50,
            proxy: new Ext.data.DirectProxy({
                directFn: config.directFn
            }),
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'data',
                fields: [
                    {name: 'device'},
                    {name: 'name'},
                    {name: 'monitored'},
                    {name: 'status'}
                ]
            })
        });
        Zenoss.InstanceStore.superclass.constructor.call(this, config);
    }

});

Ext.reg('InstanceStore', Zenoss.InstanceStore);

Zenoss.SimpleInstanceGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    
    constructor: function(config) {
        Ext.applyIf(config, {
            border: false,
            autoExpandColumn: 'name',
            stripeRows: true,
            cm: new InstanceColumnModel(),
            store: {
                xtype:'InstanceStore',
                directFn: config.directFn
            }
        });
        Zenoss.SimpleInstanceGridPanel.superclass.constructor.call(this, config);
    },
    
    setContext: function(uid) {
        this.getStore().load({params:{uid:uid}});
    }

});

Ext.reg('SimpleInstanceGridPanel', Zenoss.SimpleInstanceGridPanel);

})();

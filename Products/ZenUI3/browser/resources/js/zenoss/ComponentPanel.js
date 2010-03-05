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

var ZC = Ext.ns('Zenoss.component');

ZC.BaseComponentPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            border: false,
            autoExpandColumn: 'name',
            stripeRows: true,
            store: new ZC.BaseComponentStore({
                autoLoad: true,
                fields:config.fields, 
                directFn:config.directFn || Zenoss.remote.DeviceRouter.getComponents
            }),
            colModel: new ZC.BaseComponentColModel({
                columns:config.columns
            }),
            selModel: new Ext.ux.grid.livegrid.RowSelectionModel(),
            view: new Ext.ux.grid.livegrid.GridView({
                listeners: {
                    beforeload: this.applyOptions,
                    beforebuffer: this.applyOptions,
                    scope: this
                }
            })
        });
        ZC.BaseComponentPanel.superclass.constructor.call(this, config);
    },
    applyOptions: function(store, options){
        Ext.applyIf(options.baseParams, {
            uid: this.contextUid,
            keys: Ext.pluck(this.getColumnModel().config, 'dataIndex'),
            meta_type: this.componentType
        });
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.view.updateLiveRows(this.view.rowIndex, true, true);
        this.ownerCt.doLayout();
    }
});

ZC.BaseComponentStore = Ext.extend(Ext.ux.grid.livegrid.Store, {
    constructor: function(config) {
        var fields = config.fields || [
            {name: 'name'},
            {name: 'monitored'},
            {name: 'status'}
        ];
        Ext.applyIf(config, {
            bufferSize: 50,
            proxy: new Ext.data.DirectProxy({
                directFn: config.directFn
            }),
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'data',
                fields: fields
            })
        });
        ZC.BaseComponentStore.superclass.constructor.call(this, config);
    }
});

ZC.BaseComponentColModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config) {
        var cols = config.columns || [{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
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
            }];
        config = Ext.applyIf(config||{}, {
            defaults: {
                menuDisabled: true
            },
            columns: cols
        });
        ZC.BaseComponentColModel.superclass.constructor.call(this, config);
    }
});

ZC.IpInterfacePanel = Ext.extend(ZC.BaseComponentPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpInterface',
            fields: [
                {name: 'name'},
                {name: 'ipAddress'},//, mapping:'ipAddress.uid'},
                {name: 'network'},//, mapping:'network.uid'},
                {name: 'macaddress'},
                {name: 'status'},
                {name: 'monitored'},
                {name: 'locking'}
            ],
            columns: [{
                id: 'name',
                dataIndex: 'name',
                header: _t('IP Interface')
            },{
                id: 'ipAddress',
                dataIndex: 'ipAddress',
                header: _t('IP Address'),
                renderer: function(ip) {
                    // ip is the marshalled Info object
                    if (ip) {
                        return Zenoss.render.link(ip.uid);
                    }
                }
            },{
                id: 'network',
                dataIndex: 'network',
                header: _t('Network'),
                renderer: function(network){
                    // network is the marshalled Info object
                    if (network) {
                        return Zenoss.render.link(network.uid, null, network.name);
                    }
                }
            },{
                id: 'macaddress',
                dataIndex: 'macaddress',
                header: _t('MAC Address'),
                width: 120
            },{
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                width: 50
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpInterfacePanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('IpInterfacePanel', ZC.IpInterfacePanel);


})();

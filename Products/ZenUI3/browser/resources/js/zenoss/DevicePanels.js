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
                width: 100,
                dataIndex: 'ipAddress',
                header: _t('IP Address'),
                renderer: function(ip, row, record) {
                    return record.data.ipAddressString;
                }
            },{
                dataIndex: 'uid',
                header: _t('Device Class'),
                id: 'deviceClass',
                width: 120,
                renderer: Zenoss.render.DeviceClass
            },{
                id: 'productionState',
                dataIndex: 'productionState',
                width: 100,
                filter: {
                    xtype: 'multiselect-prodstate'
                },
                header: _t('Production State')
            },{
                id: 'events',
                sortable: false,
                filter: false,
                dataIndex: 'events',
                header: _t('Events'),
                renderer: function(ev, ignored, record) {
                    var table = Zenoss.render.events(ev),
                        url = record.data.uid + '/devicedetail?filter=default#deviceDetailNav:device_events';
                    table = table.replace('table', 'table onclick="location.href=\''+url+'\';"');
                    return table;
                }
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
            bufferSize: 400,
            defaultSort: {field: 'name', direction:'ASC'},
            sortInfo: {field: 'name', direction:'ASC'},
            proxy: new Ext.data.DirectProxy({
                directFn: Zenoss.remote.DeviceRouter.getDevices
            }),
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'devices',
                totalProperty: 'totalCount',
                idProperty: 'uid'
            },[
                  {name: 'uid', type: 'string'},
                  {name: 'name', type: 'string'},
                  {name: 'ipAddress', type: 'int'},
                  {name: 'ipAddressString', type: 'string'},
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
                rowHeight: 24,
                nearLimit: 100,
                loadMask: {msg: 'Loading. Please wait...'}
            }),
            autoExpandColumn: 'name',
            cm: new Zenoss.DeviceColumnModel({defaults:{sortable:true}}),
            sm: new Zenoss.ExtraHooksSelectionModel(),
            stripeRows: true
        });
        Zenoss.DeviceGridPanel.superclass.constructor.call(this, config);
        this.store.proxy.on('beforeload', function(){
            this.view._loadMaskAnchor = Ext.get('center_panel_container');
            Ext.apply(this.view.loadMask,{
                msgCls : 'x-mask-loading'
            });
            this.view._loadMaskAnchor.mask(this.view.loadMask.msg, this.view.loadMask.msgCls);
            this.view.showLoadMask(true);
        }, this, {single:true});
        this.store.proxy.on('load', function(){
            this.view.showLoadMask(false);
            this.view._loadMaskAnchor = Ext.get(this.view.mainBody.dom.parentNode.parentNode);
        }, this, {single:true});
        this.store.proxy.on('load',
            function(proxy, o, options) {
                this.lastHash = o.result.hash || this.lastHash;
            },
            this);
        this.on('rowdblclick', this.onRowDblClick, this);
    }, // constructor
    onRowDblClick: function(grid, rowIndex, e) {
        window.location = grid.getStore().getAt(rowIndex).data.uid;
    }
});
Ext.reg('DeviceGridPanel', Zenoss.DeviceGridPanel);

/**********************************************************************
 *
 * Device Actions
 *
 */
function disableSendEvent() {
    var cbs = Ext.getCmp('lockingchecks').getValue(),
        sendEvent = Ext.getCmp('send-event-checkbox');
    cbs.remove(sendEvent);
    sendEvent.setDisabled(Ext.isEmpty(cbs));
}
    /**
     * Drop down of action items that you can use against
     * a device. The two required parameters are
     *@param 1. saveHandler = function to be called after the action (refresh the grid etc)
     *@param 2. deviceFetcher = function that returns the list of device records
     *@class DeviceActionMenu
     *@extends Ext.Button
     **/
    var DeviceActionMenu = Ext.extend(Ext.Button, {
        constructor: function(config) {
            config = config || {};
            if (!config.saveHandler) {
                throw "Device Action Menu did not receive a save handler";
            }
            if (!config.deviceFetcher) {
                throw "Device Action Menu did not receive a device fetcher";
            }
            var fetcher = config.deviceFetcher,
                saveHandler = config.saveHandler,
                REMOTE = Zenoss.remote.DeviceRouter;

            Ext.applyIf(config, {
                text: _t('Actions'),
                disabled: Zenoss.Security.doesNotHavePermission('Delete Device'),
                menu: {
                    items: [
                        new Zenoss.Action({
                            text: _t('Lock Devices') + '...',
                            iconCls: 'lock',
                            permission: 'Change Device',
                            handler: function() {
                                var win = new Zenoss.FormDialog({
                                    title: _t('Lock Devices'),
                                    modal: true,
                                    width: 310,
                                    height: 220,
                                    items: [{
                                        xtype: 'checkboxgroup',
                                        id: 'lockingchecks',
                                        columns: 1,
                                        style: 'margin: 0 auto',
                                        items: [{
                                            name: 'updates',
                                            id: 'lock-updates-checkbox',
                                            boxLabel: _t('Lock from updates'),
                                            handler: disableSendEvent
                                        },{
                                            name: 'deletion',
                                            id: 'lock-deletion-checkbox',
                                            boxLabel: _t('Lock from deletion'),
                                            handler: disableSendEvent
                                        },{
                                            name: 'sendEvent',
                                            id: 'send-event-checkbox',
                                            boxLabel: _t('Send an event when an action is blocked'),
                                            disabled: true
                                        }]
                                    }],
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        text: _t('Lock'),
                                        handler: function() {
                                            var cbs = Ext.getCmp('lockingchecks').getValue(),
                                            opts = fetcher();
                                            Ext.each(cbs, function(cb) {
                                                opts[cb.name] = true;
                                            });
                                            REMOTE.lockDevices(opts, saveHandler);
                                        }
                                    }, Zenoss.dialog.CANCEL
                                             ]
                                });
                                win.show();
                            }
                        }),
                        new Zenoss.Action({
                            text: _t('Reset IP'),
                            iconCls: 'set',
                            permission: 'Change Device',
                            handler: function(){
                                Ext.Msg.show({
                                    title: _t('Reset IP'),
                                    msg: _t('Are you sure you want to reset the IP addresses of ' +
                                            'these devices to the results of a DNS lookup?'),
                                    buttons: Ext.Msg.YESNO,
                                    fn: function(r){
                                        switch(r) {
                                          case 'no':
                                            break;
                                          case 'yes':
                                            REMOTE.resetIp(fetcher(), saveHandler);
                                            break;
                                        default:
                                            break;
                                        }
                                    }
                                });
                            }
                        }),
                        /*
                         * Currently causes a bus error on multiple devices: http://dev.zenoss.org/trac/ticket/6142
                         * Commenting out until that is fixed
                         *
                        resetCommunity: new Zenoss.Action({
                            text: _t('Reset Community'),
                            iconCls: 'set',
                            permission: 'Change Device',
                            handler: function(){
                                Ext.Msg.show({
                                    title: _t('Reset Community'),
                                    msg: _t('Are you sure you want to reset the SNMP '+
                                            'community strings of these devices?'),
                                    buttons: Ext.Msg.YESNO,
                                    fn: function(r) {
                                        switch(r) {
                                          case 'no':
                                            break;
                                          case 'yes':
                                            REMOTE.resetCommunity(gridOptions(), resetGrid);
                                            break;
                                        default:
                                            break;
                                        }
                                    }
                                });
                            }
                        }),
                        */
                        new Zenoss.Action({
                            text: _t('Set Production State')+'...',
                            iconCls: 'set',
                            permission: 'Change Device Production State',
                            handler: function(){
                                var win = new Zenoss.FormDialog({
                                    title: _t('Set Production State'),
                                    modal: true,
                                    width: 310,
                                    height: 150,
                                    items: [{
                                        xtype: 'ProductionStateCombo',
                                        fieldLabel: _t('Select a production state'),
                                        id: 'prodstate',
                                        listeners: {
                                            'select': function(){
                                                Ext.getCmp('prodstateok').enable();
                                            }
                                        }
                                    }],
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        id: 'prodstateok',
                                        disabled: true,
                                        text: _t('OK'),
                                        handler: function(){
                                            var opts = Ext.apply(fetcher(), {
                                                prodState:Ext.getCmp('prodstate').getValue()
                                            });
                                            REMOTE.setProductionState(opts, saveHandler);
                                        }
                                    }, Zenoss.dialog.CANCEL
                                             ]
                                });
                                win.show();
                            }
                        }),
                        new Zenoss.Action({
                            text: _t('Set Priority')+'...',
                            iconCls: 'set',
                            permission: 'Change Device',
                            handler: function(){
                                var win = new Zenoss.FormDialog({
                                    title: _t('Set Priority'),
                                    modal: true,
                                    width: 310,
                                    height: 150,
                                    items: [{
                                        xtype: 'PriorityCombo',
                                        id: 'priority',
                                        fieldLabel: _t('Select a priority'),
                                        listeners: {
                                            'select': function(){
                                                Ext.getCmp('priorityok').enable();
                                            }
                                        }
                                    }],
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        id: 'priorityok',
                                        disabled: true,
                                        text: _t('OK'),
                                        handler: function(){
                                            var opts = Ext.apply(fetcher(), {
                                                priority: Ext.getCmp('priority').getValue()
                                            });
                                            REMOTE.setPriority(opts, saveHandler);
                                        }
                                    }, Zenoss.dialog.CANCEL
                                             ]
                                });
                                win.show();
                            }
                        }),
                        new Zenoss.Action({
                            text: _t('Set Collector') + '...',
                            iconCls: 'set',
                            permission: 'Change Device',
                            handler: function(){
                                var win = new Zenoss.FormDialog({
                                    title: _t('Set Collector'),
                                    modal: true,
                                    width: 310,
                                    height: 150,
                                    items: [{
                                        xtype: 'combo',
                                        fieldLabel: _t('Select a collector'),
                                        id: 'collector',
                                        mode: 'local',
                                        store: new Ext.data.ArrayStore({
                                            data: Zenoss.env.COLLECTORS,
                                            fields: ['name']
                                        }),
                                        valueField: 'name',
                                        displayField: 'name',
                                        forceSelection: true,
                                        editable: false,
                                        listeners: {
                                            'select': function(){
                                                Ext.getCmp('collectorok').enable();
                                            }
                                        }
                                    }],
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        id: 'collectorok',
                                        disabled: true,
                                        text: _t('OK'),
                                        handler: function(){
                                            var opts = Ext.apply(fetcher(), {
                                                collector: Ext.getCmp('collector').getValue()
                                            });
                                            REMOTE.setCollector(opts, saveHandler);
                                        }
                                    }, Zenoss.dialog.CANCEL
                                             ]
                                });
                                win.show();
                            }
                        })]
                }
            });
            DeviceActionMenu.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('deviceactionmenu', DeviceActionMenu);


})(); // end of function namespace scoping

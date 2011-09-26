/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

(function(){

Ext.ns('Zenoss');

function objectRenderer(obj) {
    if (obj) {
        return obj.name;
    }
    return "";
}
    var deviceColumns = [
        {
        dataIndex: 'name',
        header: _t('Device'),
        id: 'titleOrId',
        flex: 1,
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
        sortable: false,
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
        id: 'getHWSerialNumber',
        dataIndex: 'serialNumber',
        width: 100,
        hidden: true,
        header: _t('Serial Number')
    },{
        id: 'getHWTag',
        dataIndex: 'tagNumber',
        width: 100,
        hidden: true,
        header: _t('Tag Number')
    },{
        id: 'getHWManufacturerName',
        dataIndex: 'hwManufacturer',
        width: 100,
        header: _t('Hardware Manufacturer'),
        hidden: true,
        renderer: objectRenderer
    },{
        id: 'getHWProductClass',
        dataIndex: 'hwModel',
        hidden: true,
        width: 100,
        header: _t('Hardware Model'),
        renderer: objectRenderer
    },{
        id: 'getOSManufacturerName',
        dataIndex: 'osManufacturer',
        width: 100,
        header: _t('OS Manufacturer'),
        hidden: true,
        renderer: objectRenderer
    },{
        id: 'getOSProductName',
        dataIndex: 'osModel',
        width: 150,
        hidden: true,
        header: _t('OS Model'),
        renderer: objectRenderer
    },{
        id: 'getPerformanceServerName',
        dataIndex: 'collector',
        width: 100,
        hidden: true,
        header: _t('Collector')
    },{
        id: 'getPriorityString',
        dataIndex: 'priority',
        width: 100,
        hidden: true,
        header: _t('Priority')
    },{
        id: 'getSystemNames',
        dataIndex: 'systems',
        width: 100,
        hidden: true,
        sortable: false,
        header: _t('Systems'),
        renderer: function(systems) {
            var links = [];
            if (systems) {
                Ext.each(systems, function(system){
                    links.push(Zenoss.render.DeviceSystem(system.uid, system.name));
                });
            }
            return links.join(" | ");
        }
    },{
        id: 'getDeviceGroupNames',
        dataIndex: 'groups',
        width: 100,
        hidden: true,
        sortable: false,
        header: _t('Groups'),
        renderer: function(groups) {
            var links = [];
            if (groups) {
                Ext.each(groups, function(group){
                    links.push(Zenoss.render.DeviceGroup(group.uid, group.name));
                });
            }
            return links.join(" | ");

        }
    },{
        id: 'getLocationName',
        dataIndex: 'location',
        width: 100,
        hidden: true,
        sortable: false,
        header: _t('Location'),
        renderer: function(loc){
            if (loc){
                return Zenoss.render.DeviceLocation(loc.uid, loc.name);
            }
            return '';
        }
    },{
        id: 'worstevents',
        sortable: false,
        filter: false,
        width: 75,
        dataIndex: 'events',
        header: _t('Events'),
        renderer: function(ev, ignored, record) {
            var table = Zenoss.render.worstevents(ev),
            url = record.data.uid + '/devicedetail?filter=default#deviceDetailNav:device_events';
            if (table){
                table = table.replace('table', 'table onclick="location.href=\''+url+'\';"');
            }
            return table;
        }
    }];
Ext.define('Zenoss.device.DeviceModel',{
    extend: 'Ext.data.Model',
    fields: [
        {name: 'uid', type: 'string'},
        {name: 'name', type: 'string'},
        {name: 'ipAddress', type: 'int'},
        {name: 'ipAddressString', type: 'string'},
        {name: 'productionState', type: 'string'},
        {name: 'serialNumber', type: 'string'},
        {name: 'tagNumber', type: 'string'},
        {name: 'hwManufacturer', type: 'object'},
        {name: 'hwModel', type: 'object'},
        {name: 'osManufacturer', type: 'object'},
        {name: 'osModel', type: 'object'},
        {name: 'collector', type: 'string'},
        {name: 'priority', type: 'string'},
        {name: 'systems', type: 'object'},
        {name: 'groups', type: 'object'},
        {name: 'location', type: 'object'},
        {name: 'events', type: 'auto'},
        {name: 'availability', type: 'float'}
    ],
    idProperty: 'uid'
});

/**
 * @class Zenoss.DeviceStore
 * @extend Zenoss.DirectStore
 * Direct store for loading devices
 */
Ext.define("Zenoss.DeviceStore", {
    alias: ['widget.DeviceStore'],
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            autoLoad: false,
            pageSize: 200,
            model: 'Zenoss.device.DeviceModel',
            initialSortColumn: "name",
            directFn: Zenoss.remote.DeviceRouter.getDevices,
            root: 'devices'
        });
        this.callParent(arguments);
    }
});

/**
 * @class Zenoss.DeviceGridPanel
 * @extends Zenoss.FilterGridPanel
 * Main grid panel for displaying a device. Used on the It Infrastructure page.
 **/
Ext.define("Zenoss.DeviceGridPanel", {
    extend: "Zenoss.FilterGridPanel",
    alias: ['widget.DeviceGridPanel', 'widget.SimpleDeviceGridPanel'],
    lastHash: null,
    constructor: function(config) {
        var storeConfig = config.storeCfg || {};
        var store = Ext.create('Zenoss.DeviceStore', storeConfig);

        Ext.applyIf(config, {
            store: store,
            columns: deviceColumns
        });
        this.callParent(arguments);
        this.on('rowdblclick', this.onRowDblClick, this);
    },

    onRowDblClick: function(grid, rowIndex, e) {
        window.location = grid.getStore().getAt(rowIndex).data.uid;
    }
});

/**********************************************************************
 *
 * Device Actions
 *
 */
function disableSendEvent() {
    var cbs = Ext.getCmp('lockingchecks').getValue(),
        sendEvent = Ext.getCmp('send-event-checkbox');

    if (cbs.sendEvent){
        delete cbs.sendEvent;
    }
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
    Ext.define("Zenoss.DeviceActionMenu", {
        alias: ['widget.deviceactionmenu'],
        extend: "Ext.Button",
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
            Zenoss.DeviceActionMenu.superclass.constructor.apply(this, arguments);
        }
    });


})(); // end of function namespace scoping

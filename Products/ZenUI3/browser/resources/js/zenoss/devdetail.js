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

Ext.onReady(function(){

var REMOTE = Zenoss.remote.DeviceRouter,
    UID = Zenoss.env.device_uid;

Zenoss.nav.register({
    Device: [{
        id: 'Overview',
        nodeType: 'subselect',
        text: _t('Device Overview'),
        action: function(node, target){
            target.layout.setActiveItem('device_overview');
        }
    },{
        id: 'Components',
        nodeType: 'subselect',
        text: _t('Components'),
        action: function(node, target) {
            target.layout.setActiveItem('component_browser');
        }
    }]
});

var componentBrowser = new Zenoss.component.Browser({
    region: 'north',
    height: 150,
    uid: UID,
    split: true,
    directFn: REMOTE.getComponentTree
});

var componentCard = {
    id: 'component_browser',
    layout: 'border',
    border: false,
    items:[
        componentBrowser,
        {
            xtype: 'contextcardpanel',
            id: 'component_detail_panel',
            split: true,
            border: false,
            bodyStyle: 'border-top: 1px solid gray',
            region: 'center'
        }
    ]
}

var deviceInformation = {
    xtype: 'fieldset',
    layout: 'column',
    title: _t('Device Information'),
    defaults: {
        columnWidth: 0.5,
        border: false
    },
    items: [{
        layout: 'form',
        defaultType: 'displayfield',
        items: [{
            name: 'name',
            fieldLabel: _t('Host Name')
        },{
            name: 'deviceClass',
            fieldLabel: _t('Device Class')
        },{
            name: 'groups',
            fieldLabel: _t('Custom Groups')
        },{
            name: 'systems',
            fieldLabel: _t('Systems')
        },{
            name: 'location',
            fieldLabel: _t('Location')
        },{
            name: 'locking',
            fieldLabel: _t('Locking')
        },{
            name: 'lastChanged',
            fieldLabel: _t('Last Changed')
        },{
            name: 'lastCollected',
            fieldLabel: _t('Last Collected')
        }]
    },{
        layout: 'form',
        items: [{
            xtype: 'editabletextarea',
            name: 'description',
            fieldLabel: _t('Description')
        },{
            xtype: 'editabletextarea',
            name: 'comments',
            fieldLabel: _t('Comments')
        },{
            xtype: 'displayfield',
            name: 'links',
            fieldLabel: _t('Links')
        }]
    }]
};

var snmpInformation = {
    xtype: 'fieldset',
    defaultType: 'displayfield',
    title: _t('SNMP Information'),
    items: [{
        name: 'snmpSysName',
        fieldLabel: _t('SNMP SysName')
    },{
        name: 'snmpContact',
        fieldLabel: _t('SNMP Contact')
    },{
        name: 'snmpLocation',
        fieldLabel: _t('SNMP Location')
    },{
        name: 'snmpAgent',
        fieldLabel: _t('SNMP Agent')
    }]
};

var hwosInformation = {
    xtype: 'fieldset',
    defaultType: 'displayfield',
    title: _t('Hardware/OS Information'),
    items: [{
        name: 'hwManufacturer',
        fieldLabel: _t('Hardware Manufacturer')
    },{
        name: 'hwModel',
        fieldLabel: _t('Hardware Model')
    },{
        name: 'osManufacturer',
        fieldLabel: _t('OS Manufacturer')
    },{
        name: 'osModel',
        fieldLabel: _t('OS Model')
    },{
        xtype: 'editable',
        name: 'tagNumber',
        fieldLabel: _t('Tag Number')
    },{
        xtype: 'editable',
        name: 'serialNumber',
        fieldLabel: _t('Serial Number')
    },{
        xtype: 'editable',
        name: 'rackSlot',
        fieldLabel: _t('Rack Slot')
    }]
};

var overview = {
    id: 'device_overview',
    layout: 'border',
    border: false,
    defaults: {border:false},
    items: [{
        id: 'detail_panel',
        region: 'center',
        xtype: 'form',
        border: false,
        split: true,
        autoScroll: true,
        bodyStyle: 'padding: 15px;',
        listeners: {
            render: function(){
                this.api.load(this.baseParams, function(result){
                    var systems = [], groups = [], D = result.data;
                    D.deviceClass = Zenoss.render.link(
                        D.deviceClass.uid);
                    D.location = D.location ? Zenoss.render.link(D.location.uid) : 'None';
                    Ext.each(D.systems, function(i){
                        systems.push(Zenoss.render.link(i.uid));
                    });
                    D.systems = systems.join(', ') || 'None';
                    Ext.each(D.groups, function(i){
                        groups.push(Zenoss.render.link(i.uid));
                    });
                    D.groups = groups.join(', ') || 'None';
                    if (D.locking) {
                        D.locking = Zenoss.render.locking(D.locking);
                    }
                    if (D.hwManufacturer) {
                        D.hwManufacturer = Zenoss.render.link(D.hwManufacturer.uid);
                    } else {
                        D.hwManufacturer = 'None';
                    }
                    if (D.hwModel) {
                        D.hwModel = Zenoss.render.link(D.hwModel.uid);
                    } else {
                        D.hwModel = 'None';
                    }
                    if (D.osManufacturer) {
                        D.osManufacturer = Zenoss.render.link(D.osManufacturer.uid);
                    } else {
                        D.osManufacturer = 'None';
                    }
                    if (D.osModel) {
                        D.osModel = Zenoss.render.link(D.osModel.uid);
                    } else {
                        D.osModel = 'None';
                    }
                    this.getForm().setValues(D);
                }, this);
            }
        },
        api: {
            load: REMOTE.getInfo,
            submit: REMOTE.setInfo
        },
        baseParams: {
            uid: UID
        },
        labelAlign: 'top',
        defaults:{
            anchor: Ext.isIE ? '98%' : '100%'
        },
        items: [
            deviceInformation,
            {
                border: false,
                layout: 'column',
                defaults:{
                    columnWidth: 0.5,
                    bodyStyle: 'padding:5px',
                    border: false
                },
                items: [{
                    items: hwosInformation
                },{
                    items: snmpInformation
                }]
            }
        ]
    },{
        region: 'south',
        id: 'bottom_detail_panel',
        split: true,
        xtype: 'SimpleEventGridPanel',
        height: 250,
        listeners: {
            render: function(me) {
                me.setContext(UID);
            }
        },
        collapsed: true,
        tbar: {
            xtype: 'consolebar',
            title: 'Events'
        },
        columns: Zenoss.env.COLUMN_DEFINITIONS
    }]
};

Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border':false
    },
    tbar: {
        xtype: 'devdetailbar',
        listeners: {
            render: function(me) {
                me.setContext(UID);
            }
        }
    },
    items: [{
        region: 'west',
        split: 'true',
        id: 'master_panel',
        width: 275,
        items: [{
            xtype: 'treepanel',
            border: false,
            selModel: new Ext.tree.DefaultSelectionModel({
                listeners: {
                    selectionchange: function(sm, node){
                        var target = Ext.getCmp('detail_card_panel');
                        node.attributes.action(node, target);
                    }
                }
            }),
            rootVisible: false,
            root: {
                nodeType: 'async',
                children: Zenoss.nav.Device
            }
        }]
    },{
        xtype: 'contextcardpanel',
        id: 'detail_card_panel',
        split: true,
        activeItem: 0,
        region: 'center',
        items: [overview, componentCard]
    }]
});

});

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

var ZEvActions = Zenoss.events.EventPanelToolbarActions;

function setEventButtonsDisplayed(bool) {
    var actions = [
        ZEvActions.acknowledge,
        ZEvActions.close,
        ZEvActions.newwindow
    ];
    var method = bool ? 'show' : 'hide';
    Ext.each(actions, function(action) {
        action[method]();
    });
}

Zenoss.nav.register({
    Device: [{
        id: 'Overview',
        nodeType: 'subselect',
        text: _t('Device Overview'),
        action: function(node, target){
            target.layout.setActiveItem('device_overview');
            var panel = Ext.getCmp('devdetail_bottom_detail_panel');
            if (panel.collapsed) {
                panel.topToolbar.togglebutton.setIconClass('expand');
            } else {
                panel.topToolbar.togglebutton.setIconClass('collapse');
                setEventButtonsDisplayed(true);
            }
        }
    },{
        id: 'Components',
        nodeType: 'subselect',
        text: _t('Components'),
        action: function(node, target) {
            target.layout.setActiveItem('component_browser');
            setEventButtonsDisplayed(true);
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
            xtype: 'inheritfield',
            id: 'myinheritfield',
            items: [{
                xtype: 'textfield',
                fieldLabel: 'Value'
            }]
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
        id: 'overview_detail_panel',
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
        id: 'devdetail_bottom_detail_panel',
        split: true,
        xtype: 'SimpleEventGridPanel',
        height: 250,
        listeners: {
            render: function(me) {
                me.setContext(UID);
            },
            collapse: function(me) {
                setEventButtonsDisplayed(false);
            },
            beforeexpand: function(me) {
                setEventButtonsDisplayed(true);
            }
        },
        collapsed: true,
        tbar: {
            xtype: 'consolebar',
            title: _t('Event Console'),
            items: [
                ZEvActions.acknowledge,
                ZEvActions.close,
                ZEvActions.newwindow
            ]
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
            xtype: 'detailnav',
            target: 'detail_card_panel',
            menuIds: ['More','Add','TopLevel','Manage'],
            listeners:{
                render: function(panel) {
                    this.setContext(UID);
                }
            },
            filterNav: function(navpanel, config){
                //nav items to be excluded
                var excluded = [
                    'status',
                    'os',
                    'edit',
                    'events',
                    'resetcommunity',
                    'pushconfig',
                    'modeldevice',
                    'historyevents'
                ];
                return (excluded.indexOf(config.id)==-1);
            },
            onGetNavConfig: function(contextId) {
                return Zenoss.nav.Device;
            },
            onSelectionChange: function(detailNav, node) {
                var target = Ext.getCmp('detail_card_panel'),
                    action = node.attributes.action || function(node, target) {
                        var id = node.attributes.id;
                        if (!(id in target.items.map)) {
                            var config = detailNav.panelConfigMap[id];
                            Ext.applyIf(config, {refreshOnContextChange: true});
                            if(config) {
                                target.add(config);
                                target.doLayout();
                            }
                        }
                        target.items.map[node.attributes.id].setContext(detailNav.contextId);
                        target.layout.setActiveItem(node.attributes.id);
                    };
                action(node, target);
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

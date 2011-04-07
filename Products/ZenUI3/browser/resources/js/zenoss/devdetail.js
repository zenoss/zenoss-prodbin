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

REMOTE.getProductionStates({}, function(d){
    Zenoss.env.PRODUCTION_STATES = d;
});

REMOTE.getPriorities({}, function(d){
    Zenoss.env.PRIORITIES = d;
});

function selectOnRender(n) {
    if (n.rendered) {
        n.select();
    } else {
        n.render = n.render.createSequence(function(){
            n.select();
        }, n);
    }
}

function deviceColumnDefinitions() {
    var defs = Zenoss.env.COLUMN_DEFINITIONS;
    return Zenoss.util.filter(defs, function(d){
        return d.id != "device";
    });
}


function refreshComponentTreeAndGrid(compType) {
    var tree = Ext.getCmp('deviceDetailNav').treepanel,
        sm = tree.getSelectionModel(),
        sel = sm.getSelectedNode(),
        compsNode = tree.getRootNode().findChildBy(function(n){
            return n.text=='Components';
        });
    compType = compType || sel.id;
    sm.suspendEvents();
    compsNode.reload(function(){
        sm.resumeEvents();
        var node = compsNode.findChildBy(function(n){return n.id==compType;});
        if (!node) {
            node = compsNode.firstChild;
        }
        if (!sel) {
            node.select();
        }
    });
}

Zenoss.env.componentReloader = function(compType) {
    return function(form, action) {
        refreshComponentTreeAndGrid(compType);
    };
};

Zenoss.ComponentNodeUI = Ext.extend(Zenoss.HierarchyTreeNodeUI, {
    renderElements: function(n, a, targetNode, bulkRender) {
        a.text.text = Zenoss.component.displayName(a.text.text)[1]; // [1] is plural
        Zenoss.ComponentNodeUI.superclass.renderElements.apply(this, arguments);
    }
});

Zenoss.nav.register({
    Device: [{
        id: 'device_overview',
        nodeType: 'subselect',
        text: _t('Overview')
    },{
        id: 'device_events',
        nodeType: 'subselect',
        text: _t('Events')
    },{
        id: UID,
        nodeType: 'async',
        text: _t('Components'),
        // hide the node; show it only when it's determined we have components
        hidden: true,
        expanded: true,
        leaf: false,
        listeners: {
            beforeclick: function(node, e) {
                node.firstChild.select();
            },
            beforeappend: function(tree, me, node){
                node.attributes.action = function(node, target) {
                    target.layout.setActiveItem('component_card');
                    target.layout.activeItem.setContext(UID, node.id);
                };
            },
            load: function(node) {
                var card = Ext.getCmp('component_card'),
                    tbar = card.getGridToolbar();
                if (node.hasChildNodes()) {
                    node.ui.show();
                    if (tbar) {
                        tbar.show();
                    }
                } else {
                    node.ui.hide();
                    if (tbar){
                        tbar.hide();
                    }
                    card.detailcontainer.removeAll();
                    try {
                        // This can fail if the device has no components at
                        // all, but it fails deep in Ext. Also it's irrelevant
                        // in that case, so just fail quietly.
                        card.componentnav.reset();
                    } catch(e) {}
                }
            }
        },
        action: function(node, target) {
            var child = node.firstChild;
            if (!child) {
                node.on('append', function(tree,me,n){
                    selectOnRender(n);
                }, node, {single:true});
            } else {
                selectOnRender(child);
            }
        },
        loader: new Ext.tree.TreeLoader({
            directFn: Zenoss.remote.DeviceRouter.getComponentTree,
            baseAttrs: {
                uiProvider: Zenoss.ComponentNodeUI
            },
            listeners: {
                load: function(loader, node, response) {
                    var tree = node.getOwnerTree(),
                        sm = tree.getSelectionModel(),
                        sel = sm.getSelectedNode(),
                        token = Ext.History.getToken(),
                        panelid = tree.ownerCt.id;
                    if (!sel && token && token.slice(0,panelid.length)==panelid) {
                        var parts = token.split(Ext.History.DELIMITER),
                            type = parts[1],
                            rest = parts.slice(2).join(Ext.History.DELIMITER);
                        if (type) {
                            var tosel = node.findChild('id', type);
                            if (tosel) {
                                selectOnRender(tosel);
                            }
                            var card = Ext.getCmp('component_card');
                            card.selectByToken(unescape(rest));
                        }
                    }
                }
            }
        })
    }]
});

function componentGridOptions() {
    var grid = Ext.getCmp('component_card').componentgrid,
        sm = grid.getSelectionModel(),
        rows = sm.getSelections(),
        ranges = sm.getPendingSelections(true),
        pluck = Ext.pluck,
        uids = pluck(pluck(rows, 'data'), 'uid'),
        name = Ext.getCmp('component_searchfield').getValue();
    return {
        uids: uids,
        ranges: ranges,
        name: name,
        hashcheck: grid.lastHash
    };
}

function showMonitoringDialog() {
    var win = new Ext.Window({
        height: 115,
        width: 200,
        title: _t('Monitoring'),
        bodyStyle: 'padding:8px;padding-top:2px',
        buttonAlign: 'left',
        plain: true,
        border: false,
        buttons: [{
            text: _t('Submit'),
            handler: function(btn) {
                var mon = Ext.getCmp('monitoring-checkbox'),
                    opts = {
                        monitor: mon.getValue()
                    };
                Ext.apply(opts, componentGridOptions());
                btn.ownerCt.ownerCt.destroy();
                REMOTE.setComponentsMonitored(opts, function(r){
                    refreshComponentTreeAndGrid();
                });
            }
        },{
            text: _t('Cancel'),
            handler: function(btn){
                btn.ownerCt.ownerCt.destroy();
            }
        }],
        items: [{
            xtype: 'checkbox',
            name: 'monitor',
            submitValue: false,
            id: 'monitoring-checkbox',
            boxLabel: _t('Monitor these components'),
            checked: true
        }]
    });
    win.show();
    win.doLayout();
}

function showComponentLockingDialog() {
    function disableSendEvent() {
        var del = Ext.getCmp('lock-deletion-checkbox'),
            sendEvent = Ext.getCmp('send-event-checkbox');
        sendEvent.setDisabled(!del.getValue());
    }
    var win = new Ext.Window({
        height: 150,
        width: 300,
        title: _t('Locking'),
        bodyStyle: 'padding:8px;padding-top:2px',
        buttonAlign: 'left',
        plain: true,
        layout: 'fit',
        buttons: [{
            text: _t('Submit'),
            handler: function(btn) {
                var del = Ext.getCmp('lock-deletion-checkbox'),
                    upd = Ext.getCmp('lock-updates-checkbox'),
                    send = Ext.getCmp('send-event-checkbox'),
                    opts = {
                        deletion: del.getValue(),
                        updates: upd.getValue(),
                        sendEvent: send.getValue()
                    };
                Ext.apply(opts, componentGridOptions());
                btn.ownerCt.ownerCt.destroy();
                REMOTE.lockComponents(opts, function(r){
                    refreshComponentTreeAndGrid();
                });
            }
        },{
            text: _t('Cancel'),
            handler: function(btn){
                btn.ownerCt.ownerCt.destroy();
            }
        }],
        items: [{
            xtype: 'container',
            frame: false,
            border: false,
            layout: 'vbox',
            defaults: {
                xtype: 'checkbox',
                flex: 1,
                align: 'stretch'
            },
            id: 'lockingchecks',
            items: [{
                name: 'updates',
                submitValue: false,
                id: 'lock-updates-checkbox',
                boxLabel: _t('Lock from updates'),
                handler: disableSendEvent.createInterceptor(function(){
                    var del = Ext.getCmp('lock-deletion-checkbox');
                    if (this.getValue()) {
                        del.setValue(true);
                        del.disable();
                    } else {
                        del.enable();
                    }
                })
            },{
                name: 'deletion',
                submitValue: false,
                id: 'lock-deletion-checkbox',
                boxLabel: _t('Lock from deletion'),
                handler: disableSendEvent
            },{
                name: 'sendEventWhenBlocked',
                id: 'send-event-checkbox',
                boxLabel: _t('Send an event when an action is blocked'),
                disabled: true
            }]
        }]
    });
    win.show();
    win.doLayout();
}

var componentCard = {
    xtype: 'componentpanel',
    id: 'component_card',
    gridtbar: [{
        xtype: 'tbtext',
        id: 'component_type_label',
        style: 'font-size:10pt;font-weight:bold'
    },'-',{
        iconCls: 'customize',
        disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
        menu: [{
            text: _t('Locking...'),
            handler: showComponentLockingDialog
        },{
            id: 'component_monitor_menu_item',
            text: _t('Monitoring...'),
            handler: showMonitoringDialog
        }]
    },{
        iconCls: 'delete',
        disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
        handler: function() {
            Ext.Msg.show({
                title: _t('Delete Components'),
                msg: _t("Are you sure you want to delete these components?"),
                buttons: Ext.Msg.YESNO,
                fn: function(btn) {
                    if (btn=="yes") {
                        REMOTE.deleteComponents(componentGridOptions(), function(){
                            refreshComponentTreeAndGrid();
                        });
                    } else {
                        Ext.Msg.hide();
                    }
                }
            });
        }
    },{
        text: _t('Select'),
        disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
        menu: [{
            text: _t('All'),
            handler: function(){
                var grid = Ext.getCmp('component_card').componentgrid;
                grid.getSelectionModel().selectRange(0, grid.store.totalLength);
            }
        },{
            text: _t('None'),
            handler: function(){
                var grid = Ext.getCmp('component_card').componentgrid;
                grid.getSelectionModel().clearSelections();
            }
        }]
    },'->',{
        xtype: 'searchfield',
        id: 'component_searchfield',
        validateOnBlur: false,
        emptyText: _t('Type to filter by name...'),
        enableKeyEvents: true,
        filterGrid: function() {
            var grid = Ext.getCmp('component_card').componentgrid;
            grid.filter(this.getValue());
        },
        listeners: {
            valid: function(field) {
                if (Zenoss.settings.enableLiveSearch) {
                    field.filterGrid();
                }
            },
            keypress: function(field, e) {
                if (e.getKey() === e.ENTER) {
                    field.filterGrid();
                }
            }
        }
    }],
    listeners: {
        contextchange: function(me, uid, type){
            Ext.getCmp('component_type_label').setText(Zenoss.component.displayName(type)[1]);
            var sf = Ext.getCmp('component_searchfield');
            sf.setRawValue(sf.emptyText);
            sf.el.addClass(sf.emptyClass);
        }
    }
};

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
    xtype: 'deviceoverview',
    id: 'device_overview'
};

Zenoss.EventActionManager.configure({
    onFinishAction: function() {
        Ext.getCmp('device_events').updateRows();
        Ext.getCmp('devdetailbar').refresh();
    },
    findParams: function() {
        return Ext.getCmp('device_events').getSelectionParameters();
    }
});

var event_console = Ext.create({
    xtype: 'EventGridPanel',
    id: 'device_events',
    stateId: 'device_events',
    newwindowBtn: true,
    actionsMenu: false,
    commandsMenu: false,
    columns: deviceColumnDefinitions()
});

Zenoss.DeviceDetailNav = Ext.extend(Zenoss.DetailNavPanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            target: 'detail_card_panel',
            menuIds: ['More','Add','TopLevel','Manage'],
            listeners:{
                render: function(panel) {
                    this.setContext(UID);
                },
                navloaded: function() {
                    Ext.History.init(function(mgr){
                        Ext.History.selectByToken(mgr.getToken());
                    });
                },
                scope: this
            }
        });
        Zenoss.DeviceDetailNav.superclass.constructor.call(this, config);
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
            'historyevents',
            'objtemplates'
        ];
        return (excluded.indexOf(config.id)==-1);
    },
    onGetNavConfig: function(contextId) {
        return Zenoss.nav.get('Device');
    },
    selectByToken: function(token) {
        var root = this.treepanel.getRootNode(),
            loader = this.treepanel.loader,
            sm = this.treepanel.getSelectionModel(),
            sel = sm.getSelectedNode(),
            findAndSelect = function() {
                var node = root.findChildBy(function(n){
                    return n.id==token;
                });
                if (node && sel!=node) {
                    selectOnRender(node);
                }
            };
        if (root.childNodes.length===0) {
            loader.on('load', findAndSelect);
        } else {
            findAndSelect();
        }
    },
    onSelectionChange: function(node) {
        var target, action;
        target = Ext.getCmp('detail_card_panel');
        if ( node.attributes.action ) {
            action = node.attributes.action;
        } else {
            action = function(node, target) {
                var id = node.attributes.id;
                if (!(id in target.items.map)) {
                    var config = this.panelConfigMap[id];
                    Ext.applyIf(config, {refreshOnContextChange: true});
                    if(config) {
                        target.add(config);
                        target.doLayout();
                    }
                }
                target.items.map[node.attributes.id].setContext(this.contextId);
                target.layout.setActiveItem(node.attributes.id);
            }.createDelegate(this);
        }
        var token = Ext.History.getToken(),
            mytoken = this.id + Ext.History.DELIMITER + node.id;
        if (!token || token.slice(0, mytoken.length)!=mytoken) {
            Ext.History.add(mytoken);
        }
        action(node, target);
    }
});
Ext.reg('devicedetailnav', Zenoss.DeviceDetailNav);


Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border':false
    },
    tbar: {
        xtype: 'devdetailbar',
        id: 'devdetailbar',
        listeners: {
            render: function(me) {
                me.setContext(UID);
            },
            contextchange: function(bar, data) {
                Zenoss.env.deviceUUID = data.uuid;
            }

        }

    },
    items: [{
        region: 'west',
        split: 'true',
        id: 'master_panel',
        width: 275,
        autoScroll: true,
        items: {
            xtype: 'detailcontainer',
            id: 'detailContainer',
            items: [{
                xtype: 'devicedetailnav',
                id: 'deviceDetailNav'
            }, {
                xtype: 'montemplatetreepanel',
                id: 'templateTree',
                detailPanelId: 'detail_card_panel',
                listeners: {
                    afterrender: function(me) {
                        me.setContext(UID);
                    }
                }
            }]
        }
    },{
        xtype: 'contextcardpanel',
        id: 'detail_card_panel',
        split: true,
        activeItem: 0,
        region: 'center',
        items: [overview, event_console, componentCard]
    }]
});

Ext.create({
    xtype: 'bindtemplatesdialog',
    id: 'bindTemplatesDialog',
    context: UID
});

Ext.create({
    xtype: 'resettemplatesdialog',
    id: 'resetTemplatesDialog',
    context: UID
});

Ext.create({
    xtype: 'overridetemplatesdialog',
    id: 'overrideTemplatesDialog',
    context: UID
});

Ext.create({
    xtype: 'addlocaltemplatesdialog',
    id: 'addLocalTemplatesDialog',
    context: UID
});

Ext.create({
    xtype: 'removelocaltemplatesdialog',
    id: 'removeLocalTemplatesDialog',
    context: UID
});


Ext.getCmp('footer_bar').add([{
    xtype: 'ContextConfigureMenu',
    id: 'component-add-menu',
    iconCls: 'add',
    menuIds: ['IpInterface', 'WinService', 'OSProcess', 'IpService', 'FileSystem', 'IpRouteEntry'],
    listeners: {
        render: function(){
            this.setContext(UID);
        }
    }
},{
    xtype: 'ContextConfigureMenu',
    id: 'device_configure_menu',
    listeners: {
        render: function(){
            this.setContext(UID);
        }
    },
    menuItems: [{
        xtype: 'menuitem',
        text: _t('Bind Templates'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('bindTemplatesDialog').show();
        }
    },{
        xtype: 'menuitem',
        text: _t('Add Local Template'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('addLocalTemplatesDialog').show();
        }
    },{
        xtype: 'menuitem',
        text: _t('Remove Local Template'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('removeLocalTemplatesDialog').show();
        }
    },{
        xtype: 'menuitem',
        text: _t('Reset Bindings'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('resetTemplatesDialog').show();
        }
    },{
        xtype: 'menuitem',
        text: _t('Override Template Here'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('overrideTemplatesDialog').show();
        }
    },'-',{
        xtype: 'menuitem',
        text: _t('Reset/Change IP Address') + '...',
        hidden: Zenoss.Security.doesNotHavePermission('Admin Device'),
        handler: function() {
            var win = new Zenoss.FormDialog({
                title: 'Reset/Change IP Address',
                items: [{
                    xtype: 'textfield',
                    vtype: 'ipaddress',
                    name: 'ip',
                    ref: '../ipaddressfield',
                    fieldLabel: _t('IP Address (blank to use DNS)')
                }],
                buttons: [{
                    text: _t('Save'),
                    ref: '../savebtn',
                    handler: function() {
                        REMOTE.resetIp({
                            ip: this.refOwner.ipaddressfield.getValue(),
                            uids: [UID],
                            hashcheck: null
                        }, function(){
                            win.destroy();
                            Ext.getCmp('devdetailbar').setContext(UID);
                        });
                    }
                },{
                    text: _t('Cancel'),
                    handler: function(){
                        win.destroy();
                    }
                }]
            });
            win.show();
            win.doLayout();
        }
    },{
        xtype: 'menuitem',
        text: _t('Push Changes') + '...',
        hidden: Zenoss.Security.doesNotHavePermission('Manage Device'),
        handler: function() {
            Ext.Msg.show({
                title: 'Push Changes',
                msg: _t('Are you sure you want to push changes to the collectors?'),
                buttons: Ext.Msg.YESNO,
                fn: function (btnid) {
                    if (btnid!='yes') {
                        return;
                    }
                    REMOTE.pushChanges({
                        uids: [UID],
                        hashcheck: null
                    }, Ext.emptyFn);
                }
            });
        }
    },{
        xtype: 'menuitem',
        text: _t('Model Device') + '...',
        hidden: Zenoss.Security.doesNotHavePermission('Manage Device'),
        handler: function() {
            var win = new Zenoss.CommandWindow({
                uids: [UID],
                target: 'run_model',
                title: _t('Model Device')
            });
            win.show();
        }
    }]
},{
    id: 'commands-menu',
    text: _t('Commands'),
    hidden: Zenoss.Security.doesNotHavePermission('Run Commands'),
    listeners: {
        render: function() {
            var menu = this.menu;
            REMOTE.getUserCommands({uid:UID}, function(data){
                menu.removeAll();
                Ext.each(data, function(d){
                    menu.add({
                        text:d.id,
                        tooltip:d.description,
                        handler: function(item) {
                            var win = new Zenoss.CommandWindow({
                                uids: [UID],
                                target: UID + '/run_command',
                                command: item.text
                            });
                            win.show();
                        }
                    });
                });
            });
        }
    },
    menu: {}
}]);


});

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

Ext.onReady(function(){

Ext.ns('Zenoss.devices');

// Extensions used on this page
Ext.ns('Zenoss.extensions');
var EXTENSIONS_adddevice = Zenoss.extensions.adddevice instanceof Array ?
                           Zenoss.extensions.adddevice : [];

// page level variables
var REMOTE = Zenoss.remote.DeviceRouter,
    treesm,
    treeId = 'groups',
    nodeType = 'Organizer';

REMOTE.getProductionStates({}, function(d){
    Zenoss.env.PRODUCTION_STATES = d;
});

REMOTE.getPriorities({}, function(d){
    Zenoss.env.PRIORITIES = d;
});

REMOTE.getCollectors({}, function(d){
    var collectors = [];
    Ext.each(d, function(r){collectors.push([r]);});
    Zenoss.env.COLLECTORS = collectors;
});

var resetCombo = function(combo, manufacturer) {
    combo.clearValue();
    combo.getStore().setBaseParam('manufacturer', manufacturer);
    delete combo.lastQuery;
    //combo.doQuery(combo.allQuery, true);
};

var hwManufacturers = {
    xtype: 'manufacturercombo',
    name: 'hwManufacturer',
    fieldLabel: _t('HW Manufacturer'),
    listeners: {'select': function(combo, record, index){
        var productCombo = Ext.getCmp('hwproductcombo');
        resetCombo(productCombo, record.data.name);
    }}
};

var hwProduct = {
    xtype: 'productcombo',
    prodType: 'HW',
    minListWidth: 250,
    resizable: true,
    name: 'hwProductName',
    fieldLabel: _t('HW Product'),
    id: 'hwproductcombo'
};

var osManufacturers = {
    xtype: 'manufacturercombo',
    name: 'osManufacturer',
    fieldLabel: _t('OS Manufacturer'),
    listeners: {'select': function(combo, record, index){
        var productCombo = Ext.getCmp('osproductcombo');
        resetCombo(productCombo, record.data.name);
    }}
};

var osProduct = {
    xtype: 'productcombo',
    prodType: 'OS',
    minListWidth: 250,
    resizable: true,
    name: 'osProductName',
    id: 'osproductcombo',
    fieldLabel: _t('OS Product')
};

var deviceClassCombo = {
    xtype: 'combo',
    minListWidth: 250,
    resizable: true,
    width: 160,
    name: 'deviceClass',
    fieldLabel: _t('Device Class'),
    id: 'add-device_class',
    store: new Ext.data.DirectStore({
        id: 'deviceClassStore',
        root: 'deviceClasses',
                totalProperty: 'totalCount',
        fields: ['name'],
        directFn: REMOTE.getDeviceClasses
    }),
    triggerAction: 'all',
    selectOnFocus: true,
    valueField: 'name',
    displayField: 'name',
    forceSelection: true,
    editable: false,
    allowBlank: false,
    listeners: {
        'afterrender': function(component) {
            var selnode = treesm.getSelectedNode();
            var isclass = selnode.attributes.uid.startswith('/zport/dmd/Devices');
            if(selnode.attributes.uid === "/zport/dmd/Devices" || !isclass ){
                //root node doesn't have a path attr
                component.setValue('/');
            }
            else if (isclass) {
                var path = selnode.attributes.path;
                path = path.replace(/^Devices/,'');
                component.setValue(path);
            }

        }
    }
};

function setDeviceButtonsDisabled(bool){
    // must also check permissions before enable/disable the
    // 'deleteDevices' button
    Zenoss.devices.deleteDevices.setDisabled(bool ||
        Zenoss.Security.doesNotHavePermission('Delete Device'));
    Ext.getCmp('commands-menu').setDisabled(bool ||
        Zenoss.Security.doesNotHavePermission('Run Commands'));
    Ext.getCmp('actions-menu').setDisabled(bool ||
        Zenoss.Security.doesNotHavePermission('Manage Device'));

}

function resetGrid() {
    Ext.getCmp('device_grid').view.nonDisruptiveReset();
    setDeviceButtonsDisabled(true);
}

treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function(sm, newnode, oldnode){
            if (newnode) {
                var uid = newnode.attributes.uid;
                Zenoss.util.setContext(uid, 'detail_panel', 'organizer_events',
                                       'commands-menu', 'footer_bar');
                setDeviceButtonsDisabled(true);

                // explicitly set the new security context (to update permissions)
                Zenoss.Security.setContext(uid);

                //should "ask" the DetailNav if there are any details before showing
                //the button
                Ext.getCmp('master_panel').items.each(function(card){
                    card.navButton.setVisible(!newnode.attributes.hidden);
                });
            }
        }
    }
});

function gridOptions() {
    var grid = Ext.getCmp('device_grid'),
    sm = grid.getSelectionModel(),
    rows = sm.getSelections(),
    ranges = sm.getPendingSelections(true),
    pluck = Ext.pluck,
    uids = pluck(pluck(rows, 'data'), 'uid'),
    opts = Ext.apply(grid.view.getFilterParams(true), {
        uids: uids,
        ranges: ranges
    });
    return opts;
}

function disableSendEvent() {
    var cbs = Ext.getCmp('lockingchecks').getValue(),
        sendEvent = Ext.getCmp('send-event-checkbox');
    cbs.remove(sendEvent);
    sendEvent.setDisabled(Ext.isEmpty(cbs));
}

Ext.apply(Zenoss.devices, {
    deleteDevices: new Zenoss.Action({
        //text: _t('Delete Devices'),
        iconCls: 'delete',
        id: 'delete-button',
        permission: 'Delete Device',
        handler: function(btn, e) {
            var grid = Ext.getCmp('device_grid'),
                selnode = treesm.getSelectedNode(),
                isclass = Zenoss.types.type(selnode.attributes.uid)=='DeviceClass',
                grpText = selnode.attributes.text.text;
            var win = new Zenoss.FormDialog({
                title: _t('Remove Devices'),
                modal: true,
                width: 300,
                height: 220,
                items: [{
                    xtype: 'panel',
                    bodyStyle: 'font-weight: bold; text-align:center',
                    html: _t('Are you sure you want to remove these devices? '+
                             'There is no undo.')
                },{
                    xtype: 'radiogroup',
                    id: 'removetype',
                    style: 'margin: 0 auto',
                    columns: 1,
                    items: [{
                        value: 'remove',
                        id: 'remove-radio',
                        name: 'removetype',
                        boxLabel: _t('Just remove from ') + grpText,
                        disabled: isclass,
                        checked: !isclass
                    },{
                        value: 'delete',
                        id: 'delete-radio',
                        name: 'removetype',
                        boxLabel: _t('Delete completely'),
                        checked: isclass
                    }]
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Remove'),
                    handler: function(b) {
                        grid.view.showLoadMask(true);
                        var opts = Ext.apply(gridOptions(), {
                            action: Ext.getCmp('removetype').getValue().value
                        });
                        if (opts.uids.length > 0) {
                            Zenoss.remote.DeviceRouter.removeDevices(opts,
                                 function(response) {
                                     var devtree = Ext.getCmp('devices'),
                                         loctree = Ext.getCmp('locs'),
                                         systree = Ext.getCmp('systems'),
                                         grptree = Ext.getCmp('groups'),
                                         deviceIds = [],
                                         flare;
                                     resetGrid();
                                     devtree.update(response.devtree);
                                     loctree.update(response.loctree);
                                     grptree.update(response.grptree);
                                     systree.update(response.systree);
                                     grid.view.showLoadMask(false);
                                     if (!Ext.isDefined(response.success) || response.success) {
                                         Ext.each(opts.uids, function(uid) {
                                             deviceIds.push( uid.split('/')[uid.split('/').length-1] );
                                         });
                                         if (['delete', 'remove'].indexOf(opts.action) !== -1) {
                                             Zenoss.message.info('Successfully {0}d device{1}: {2}',
                                                                 opts.action,
                                                                 opts.uids.length > 1 ? 's' : '',
                                                                 deviceIds.join(', '));
                                         }
                                     }
                                 }
                            );
                        }
                    }
                },
                Zenoss.dialog.CANCEL
                ]
            });
            win.show();
        }
    }),
    addDevice: new Zenoss.Action({
        text: _t('Add a Single Device') + '...',
        id: 'addsingledevice-item',
        permissions: 'Manage DMD',
        handler: function() {
            var selnode = treesm.getSelectedNode();
            var isclass = Zenoss.types.type(selnode.attributes.uid) == 'DeviceClass';
            var grpText = selnode.attributes.text.text;
            var win = new Zenoss.dialog.CloseDialog({
                width: 800,
                title: _t('Add a Single Device'),
                items: [{
                    xtype: 'form',
                    buttonAlign: 'left',
                    monitorValid: true,
                    labelAlign: 'top',
                    footerStyle: 'padding-left: 0',
                    border: false,
                    ref: 'childPanel',
                    listeners: {
                        beforeDestroy: function(component) {
                            if (Ext.isDefined(component.refOwner)) {
                                component.refOwner.destroy();
                            }
                        }
                    },
                    items: [{
                        xtype: 'panel',
                        layout: 'column',
                        border: false,
                        items: [{
                            columnWidth: 0.5,
                            border: false,
                            layout: 'form',
                            items: [{
                                xtype: 'textfield',
                                name: 'deviceName',
                                fieldLabel: _t('Name or IP'),
                                id: "add-device-name",
                                allowBlank: false
                            }, deviceClassCombo, {
                                xtype: 'combo',
                                width: 160,
                                name: 'collector',
                                fieldLabel: _t('Collector'),
                                id: 'add-device-collector',
                                mode: 'local',
                                store: new Ext.data.ArrayStore({
                                    data: Zenoss.env.COLLECTORS,
                                    fields: ['name']
                                }),
                                valueField: 'name',
                                displayField: 'name',
                                forceSelection: true,
                                editable: false,
                                allowBlank: false,
                                triggerAction: 'all',
                                selectOnFocus: true,
                                listeners: {
                                    'afterrender': function(component) {
                                        var index = component.store.find('name', 'localhost');
                                        if (index >= 0) {
                                            component.setValue('localhost');
                                        }
                                    }
                                }
                            }, {
                                xtype: 'checkbox',
                                name: 'model',
                                fieldLabel: _t('Model Device'),
                                id: 'add-device-protocol',
                                checked: true
                            }]
                        }, {
                            columnWidth: 0.5,
                            layout: 'form',
                            border: false,
                            items: [{
                                xtype: 'textfield',
                                name: 'title',
                                fieldLabel: _t('Title')
                            }, {
                                xtype: 'ProductionStateCombo',
                                name: 'productionState',
                                minListWidth: 160,
                                id: 'production-combo',
                                width: 160,
                                allowBlank: false,
                                listeners: {
                                    'afterrender': function(component) {
                                        component.store.load({callback:function(){
                                            var index = component.store.find('value', '1000');
                                            if (index>=0) {
                                                component.setValue('1000');
                                            }
                                        }});
                                    }
                                }
                            }, {
                                xtype: 'PriorityCombo',
                                name: 'priority',
                                minListWidth: 160,
                                width: 160,
                                allowBlank: false,
                                listeners: {
                                    'afterrender': function(component) {
                                        component.store.load({callback:function(){
                                            var index = component.store.find('value', '3');
                                            if (index>=0) {
                                                component.setValue('3');
                                            }
                                        }});
                                    }
                                }
                            }]
                        }]
                    }, {
                        xtype: 'panel',
                        border: false,
                        html: '<a href="#">More...</a>',
                        toggleAttrs: function() {
                            var attrs = Ext.getCmp('add_attrs');
                            if (attrs.collapsed) {
                                attrs.expand();
                                this.body.update('<a href="#">Less</a>');
                            }
                            else {
                                attrs.collapse();
                                this.body.update('<a href="#">More...</a>');
                            }
                        },
                        listeners: {
                            'afterrender': function(component) {
                                var el = component.getEl();
                                el.on('click', this.toggleAttrs, component);
                            }
                        }
                    }, {
                        id: 'add_attrs',
                        collapsible: true,
                        collapsed: true,
                        hideCollapseTool: true,
                        hideLabel: true,
                        xtype: 'panel',
                        border: false,
                        layout: 'column',
                        ref: "moreAttributes",
                        listeners: {
                            expand: function(){
                                this.refOwner.refOwner.center();
                            },
                            collapse: function(){
                                this.refOwner.refOwner.center();
                            }
                        },
                        items: [{
                            columnWidth: 0.33,
                            layout: 'form',
                            border: false,
                            items: [{
                                xtype: 'textfield',
                                name: 'snmpCommunity',
                                fieldLabel: _t('Snmp Community')
                            }, {
                                xtype: 'numberfield',
                                name: 'snmpPort',
                                fieldLabel: _t('Snmp Port'),
                                value: 161,
                                allowBlank: false,
                                allowNegative: false,
                                allowDecimals: false,
                                maxValue: 65535
                            }, {
                                xtype: 'textfield',
                                name: 'tag',
                                fieldLabel: _t('Tag Number')
                            }, {
                                xtype: 'textfield',
                                name: 'rackSlot',
                                fieldLabel: _t('Rack Slot')
                            }, {
                                xtype: 'textfield',
                                name: 'serialNumber',
                                fieldLabel: _t('Serial Number')
                            }]
                        }, {
                            columnWidth: 0.33,
                            layout: 'form',
                            border: false,
                            items: [hwManufacturers, hwProduct, osManufacturers, osProduct]
                        }, {
                            columnWidth: 0.34,
                            layout: 'form',
                            border: false,
                            items: [{
                                xtype: 'textarea',
                                name: 'comments',
                                width: '200',
                                fieldLabel: _t('Comments')
                            }]
                        }]
                    }],
                    buttons: [{
                        xtype: 'DialogButton',
                        id: 'addsingledevice-submit',
                        text: _t('Add'),
                        formBind: true,
                        handler: function(b) {
                            var form = b.ownerCt.ownerCt.getForm();
                            var opts = form.getFieldValues();
                            Zenoss.remote.DeviceRouter.addDevice(opts, function(response) {
                                if (response.success) {
                                    Zenoss.message.success(_t('Add Device Job submitted. <a href="/zport/dmd/JobManager/jobs/{0}/viewlog">View Job Log</a>'), response.jobId);
                                }
                                else {
                                    Zenoss.message.error(_t('Error adding device job.'));
                                }
                            });
                        }
                    }, Zenoss.dialog.CANCEL]
                }]
            });
            win.show();
        }
    }),
    addMultiDevicePopUP: new Zenoss.Action({
        text: _t('Add Multiple Devices') + '...',
        id: 'addmultipledevices-item',
        permission: 'Manage Device',
        handler: function(btn, e){
            Ext.util.Cookies.set('newui', 'yes');

            window.open('/zport/dmd/easyAddDevice', "multi_add",
            "menubar=0,toolbar=0,resizable=0,height=580, width=800,location=0");
        }
    })
});

function commandMenuItemHandler(item) {
    var command = item.text,
        grid = Ext.getCmp('device_grid'),
        sm = grid.getSelectionModel(),
        ranges = sm.getPendingSelections(true),
        selections = sm.getSelections(),
        devids = Ext.pluck(Ext.pluck(selections, 'data'), 'uid');
    function showWindow() {
        var win = new Zenoss.CommandWindow({
            uids: devids,
            target: treesm.getSelectedNode().attributes.uid + '/run_command',
            command: command
        });
        win.show();
    }
    if (!Ext.isEmpty(ranges)) {
        var opts = Ext.apply(grid.view.getFilterParams(true),{ranges:ranges});
        REMOTE.loadRanges(opts, function(data){
            devids.concat(data);
            showWindow();
        });
    } else {
        showWindow();
    }
}


function updateNavTextWithCount(node) {
    var sel = treesm.getSelectedNode();
    if (sel && Ext.isDefined(sel.attributes.text.count)) {
        var count = sel.attributes.text.count;
        node.setText('Devices ('+count+')');
    }
}


function initializeTreeDrop(tree) {
    Ext.apply(tree, {
        ddGroup: 'devicegriddd',
        enableDD: Zenoss.Security.hasPermission('Change Device')
    });

    // when the user is about to drop a node, let them know if it will be
    // successful or not as far as we can tell
    tree.on('nodedragover', function(e){
        var targetnode = e.target,
            targetuid = targetnode.attributes.uid,
            organizerUid;

        if ( e.data.node) {
            organizerUid = e.data.node.attributes.uid;
            if (organizerUid && targetuid) {
                return tree.canMoveOrganizer(organizerUid, targetuid);
            }
        }
        // let before node drop figure it out
        return true;
    });

    // fired when the user actually drops a node
    tree.on('beforenodedrop', function(e) {
        var grid = Ext.getCmp('device_grid'),
            targetnode = e.target,
            targetuid = targetnode.attributes.uid,
            ranges = grid.getSelectionModel().getPendingSelections(true),
            devids,
            me = this,
            success = true;
        if ( Ext.isArray(e.data.selections) ) {
            devids = Ext.pluck(Ext.pluck(e.data.selections, 'data'), 'uid');

            // show a confirmation for moving devices
            Ext.Msg.show({
                title: _t('Move Devices'),
                msg: String.format(_t("Are you sure you want to move these {0} device(s) to {1}?"), devids.length, targetnode.attributes.text.text),
                buttons: Ext.Msg.OKCANCEL,
                fn: function(btn) {
                    if (btn=="ok") {
                        grid.view.showLoadMask(true);

                        // move the devices
                        var opts = Ext.apply(grid.view.getFilterParams(true), {
                            uids: devids,
                            ranges: ranges,
                            target: targetuid
                        });

                        REMOTE.moveDevices(opts, function(data){
                            if(data.success) {
                                resetGrid();
                                me.update(data.tree);
                                if(data.exports) {
                                    Ext.Msg.show({
                                        title: _t('Remodel Required'),
                                        msg: String.format(_t("Not all of the configuration could be preserved, so a remodel of the device(s) is required. Performance templats have been reset to the defaults for the device class.")),
                                        buttons: Ext.Msg.OK});
                                }
                            } else {
                                grid.view.showLoadMask(false);
                            }
                        }, me);

                    } else {
                        Ext.Msg.hide();
                        success = false;
                    }
                }
            });

            // we want Ext to complete the drop, thus return true
            return success;
        }else {
            var organizerUid = e.data.node.attributes.uid;

            if (!tree.canMoveOrganizer(organizerUid, targetuid)) {
                return false;
            }

            // show a confirmation for organizer move
            Ext.Msg.show({
                title: _t('Move Organizer'),
                msg: String.format(_t("Are you sure you want to move {0} to {1}?"), e.data.node.attributes.text.text, targetnode.attributes.text.text),
                buttons: Ext.Msg.OKCANCEL,
                fn: function(btn) {
                    if (btn=="ok") {
                        grid.view.showLoadMask(true);

                        // move the devices
                        var params = {
                            organizerUid: organizerUid,
                            targetUid: targetuid
                        };

                        REMOTE.moveOrganizer(params, function(data){
                            if(data.success) {
                                // add the new node to our history
                                Ext.History.add(me.id + Ext.History.DELIMITER + data.data.uid.replace(/\//g, '.'));
                                tree.getRootNode().reload({
                                    callback: resetGrid
                                });
                                grid.view.showLoadMask(false);
                            } else {
                                grid.view.showLoadMask(false);
                            }
                        }, me);

                    } else {
                        Ext.Msg.hide();
                    }
                }
            });
            // Ext shows the node as already moved when we are awaiting the
            // dialog confirmation, so always tell Ext that the move didn't work
            // here. If the move was successful the tree will redraw itself with
            // the new nodes in place
            return false;
        }

    }, tree);
}

/*
* Special history manager selection to deal with the second level of nav
* on the "Details" panel.
*/
function detailSelectByToken(nodeId) {
    var parts = nodeId.split(Ext.History.DELIMITER),
        master = Ext.getCmp('master_panel'),
        container = master.layout,
        node = treesm.getSelectedNode(),
        item = Ext.getCmp('detail_nav');
    function changeDetail() {
        item.un('navloaded', item.selectFirst, item);
        container.setActiveItem(1);
        item.selectByToken(parts[1]);
    }
    if (parts[1]) {
        if (master.items.items.indexOf(container.activeItem)==1 ||
            (node && node.id==parts[0])) {
            Zenoss.HierarchyTreePanel.prototype.selectByToken.call(this, parts[0]);
            changeDetail();
        } else {
            treesm.on('selectionchange', changeDetail, treesm, {single:true});
            Zenoss.HierarchyTreePanel.prototype.selectByToken.call(this, parts[0]);
        }
    } else {
        container.setActiveItem(0);
        Zenoss.HierarchyTreePanel.prototype.selectByToken.call(this, parts[0]);
    }
}

var devtree = {
    xtype: 'HierarchyTreePanel',
    loadMask: false,
    id: 'devices',
    searchField: true,
    directFn: REMOTE.getTree,
    allowOrganizerMove: false,
    ddAppendOnly: true,
    root: {
        id: 'Devices',
        uid: '/zport/dmd/Devices',
        text: 'Device Classes'
    },
    selectByToken: detailSelectByToken,
    selModel: treesm,
    router: REMOTE,
    nodeName: 'Device',
    listeners: {
        render: initializeTreeDrop,
        filter: function(e) {
            Ext.getCmp('locs').filterTree(e);
            Ext.getCmp('groups').filterTree(e);
            Ext.getCmp('systems').filterTree(e);
        }
    }
};

var grouptree = {
    xtype: 'HierarchyTreePanel',
    loadMask: false,
    id: 'groups',
    searchField: false,
    directFn: REMOTE.getTree,
    ddAppendOnly: true,
    selectByToken: detailSelectByToken,
    root: {
        id: 'Groups',
        uid: '/zport/dmd/Groups'
    },
    nodeName: 'Group',
    selModel: treesm,
    router: REMOTE,
    selectRootOnLoad: false,
    listeners: { render: initializeTreeDrop }
};

var systree = {
    xtype: 'HierarchyTreePanel',
    loadMask: false,
    id: 'systems',
    searchField: false,
    directFn: REMOTE.getTree,
    ddAppendOnly: true,
    selectByToken: detailSelectByToken,
    root: {
        id: 'Systems',
        uid: '/zport/dmd/Systems'
    },
    nodeName: 'System',
    router: REMOTE,
    selectRootOnLoad: false,
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};

var loctree = {
    xtype: 'HierarchyTreePanel',
    loadMask: false,
    id: 'locs',
    searchField: false,
    directFn: REMOTE.getTree,
    ddAppendOnly: true,
    selectByToken: detailSelectByToken,
    root: {
        id: 'Locations',
        uid: '/zport/dmd/Locations'
    },
    nodeName: 'Location',
    router: REMOTE,
    addNodeFn: REMOTE.addLocationNode,
    selectRootOnLoad: false,
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};

var treepanel = {
    xtype: 'HierarchyTreePanelSearch',
    items: [devtree, grouptree, systree, loctree]
};

Zenoss.nav.register({
    DeviceGroup: [
        {
            id: 'device_grid',
            text: 'Devices',
            listeners: {
                render: updateNavTextWithCount
            }
        },
        {
            id: 'events_grid',
            text: _t('Events')
        },
        {
            id: 'modeler_plugins',
            text: _t('Modeler Plugins'),
            contextRegex: '^/zport/dmd/Devices'
        },{
            id: 'configuration_properties',
            text: _t('Configuration Properties'),
            contextRegex: '^/zport/dmd/Devices'
        }
    ]
});

Zenoss.InfraDetailNav = Ext.extend(Zenoss.DetailNavPanel, {
    constructor: function(config){
        Ext.applyIf(config, {
            text: _t('Details'),
            target: 'detail_panel',
            menuIds: ['More','Add','TopLevel','Manage'],
            listeners:{
                nodeloaded: function( detailNavPanel, navConfig){
                    var excluded = {
                        'device_grid': true,
                        'events_grid': true,
                        'collectorplugins': true,
                        'configuration properties': true
                    };

                    if (!excluded[navConfig.id]){
                        var config = detailNavPanel.panelConfigMap[navConfig.id];
                        if(config && !Ext.getCmp(config.id)){
                            Ext.applyIf(config, {refreshOnContextChange: true});

                            //create the panel in the center panel if needed
                            var detail_panel = Ext.getCmp('detail_panel');
                            detail_panel.add(config);
                            detail_panel.doLayout();
                        }
                    }
                }
            }
        });
        Zenoss.InfraDetailNav.superclass.constructor.call(this, config);
    },
    selectByToken: function(nodeId) {
        var selNode = function () {
            var sel = this.getSelectionModel().getSelectedNode();
            if ( !(sel && nodeId === sel.id) ) {
                var n = this.navtreepanel.root.findChild('id', nodeId);
                if (n) {
                    n.select();
                }
            }
            this.un('navloaded', this.selectFirst, this);
            this.on('navloaded', this.selectFirst, this);
        }.createDelegate(this);
        if (this.loaded) {
            selNode();
        } else {
            this.on('navloaded', selNode, this, {single:true});
        }
    },
    filterNav: function(navpanel, config){
        //nav items to be excluded
        var excluded = {
            'status': true,
            'classes': true,
            'events': true,
            'templates': true,
            'performancetemplates': true,
            'historyevents':true,
            'collectorplugins': true,
            'configuration properties': true
        };
        var uid = Zenoss.env.PARENT_CONTEXT;
        if (config.contextRegex) {
            var re = RegExp(config.contextRegex);
            return re.test(uid);
        }
        return !excluded[config.id];
    },
    onGetNavConfig: function(contextId) {
        return Zenoss.nav.get('DeviceGroup');
    },
    onSelectionChange: function(node) {
        if ( node ) {
            var detailPanel = Ext.getCmp('detail_panel');
            var contentPanel = Ext.getCmp(node.attributes.id);
            contentPanel.setContext(this.contextId);
            detailPanel.layout.setActiveItem(node.attributes.id);
            var orgnode = treesm.getSelectedNode();
            Ext.History.add([orgnode.getOwnerTree().id, orgnode.id, node.id].join(Ext.History.DELIMITER));
        }
    }
});
Ext.reg('infradetailnav', Zenoss.InfraDetailNav);

var device_grid = new Zenoss.DeviceGridPanel({
    ddGroup: 'devicegriddd',
    id: 'device_grid',
    enableDrag: true,
    header: true,
    sm: new Ext.ux.grid.livegrid.RowSelectionModel({
        listeners: {
            selectionchange: function(sm) {
                setDeviceButtonsDisabled(!sm.getSelected());
            }
        }
    }),
    setContext: function(uid) {
        var view = this.getView();
        view.contextUid = uid;
        view.nonDisruptiveReset();

        this.getSelectionModel().clearSelections();


        REMOTE.getInfo({uid: uid, keys: ['name', 'description', 'address']}, function(result) {
            var title = result.data.name;
            var qtip;

            this.header.child('span').child('span.title').update(title);

            var desc = [];
            if ( result.data.address ) {
                desc.push(result.data.address);
            }
            if ( result.data.description ) {
                desc.push(result.data.description);
            }

            if ( desc ) {
                Ext.QuickTips.register({target: this.header, text: Ext.util.Format.nl2br(desc.join('<hr>')), title: result.data.name});
            }

            this.header.child('span').child('span.desc').update(desc.join(' - '));
        }, this);
    },
    headerCfg: {
        tag: 'div',
        cls: 'x-panel-header',
        children: [
            { tag: 'span', cls: 'title', html: '' },
            { tag: 'span', cls: 'desc' }
        ]
    },
    tbar: {
        xtype: 'largetoolbar',
        id: 'detail-toolbar',
        items: [
            {
                xtype: 'eventrainbow',
                id: 'organizer_events',
                listeners: {
                    'render': function(me) {
                        me.getEl().on('click', function(){
                            Ext.History.add(Ext.History.getToken() + ':events_grid');
                        });
                    }
                }
            },
            '-',
            {
                id: 'adddevice-button',
                iconCls: 'adddevice',
                disabled: Zenoss.Security.doesNotHavePermission("Manage Device"),
                menu:{
                    items: [
                        Zenoss.devices.addDevice,
                        Zenoss.devices.addMultiDevicePopUP
                    ].concat(EXTENSIONS_adddevice)
                }
            },
            Zenoss.devices.deleteDevices,
            {
                id: 'refreshdevice-button',
                iconCls: 'refresh',
                tooltip: _t('Refresh Device List'),
                handler: function(btn) {
                    var grid = Ext.getCmp('device_grid'),
                        view = grid.getView();
                    view.updateLiveRows(view.rowIndex, true, true);
                }
            }, {
                text: _t('Select'),
                menu:[
                    {
                        text: _t('All'),
                        handler: function() {
                            var grid = Ext.getCmp('device_grid');
                            grid.getSelectionModel().selectRange(0, grid.store.totalLength);
                        }
                    },
                    {
                        text: _t('None'),
                        handler: function() {
                            var grid = Ext.getCmp('device_grid');
                            grid.getSelectionModel().clearSelections();
                        }
                    }
                ]
            },
            '->',
            {
                id: 'actions-menu',
                xtype: 'deviceactionmenu',
                deviceFetcher: gridOptions,
                saveHandler: resetGrid
            },
            {
                id: 'commands-menu',
                text: _t('Commands'),

                setContext: function(uid) {
                    var me = Ext.getCmp('commands-menu'),
                            menu = me.menu;
                    REMOTE.getUserCommands({uid:uid}, function(data) {
                        menu.removeAll();
                        Ext.each(data, function(d) {
                            menu.add({
                                text:d.id,
                                tooltip:d.description,
                                handler: commandMenuItemHandler
                            });
                        });
                    });
                },
                menu: {}
            }
        ]
    }
});

/**
 * Toggle buttons based on permissions everytime they click a different tree node
 **/
Zenoss.Security.onPermissionsChange(function(){
    Ext.getCmp('master_panel').details.setDisabled(Zenoss.Security.doesNotHavePermission('Manage DMD'));
    Ext.getCmp('commands-menu').setDisabled(Zenoss.Security.doesNotHavePermission('Run Commands'));
    Ext.getCmp('adddevice-button').setDisabled(Zenoss.Security.doesNotHavePermission('Manage DMD'));
});

Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border': false
    },
    items: [{
        xtype: 'horizontalslide',
        id: 'master_panel',
        text: _t('Infrastructure'),
        region: 'west',
        split: true,
        width: 275,
        items: [{
            text: _t('Infrastructure'),
            buttonText: _t('Details'),
            buttonRef: 'details',
            layout: 'fit',
            items: [treepanel]
        },{
            xtype: 'detailcontainer',
            buttonText: _t('See All'),
            buttonRef: 'seeAll',
            items: [{
                xtype: 'infradetailnav',
                id: 'detail_nav'
            }, {
                xtype: 'montemplatetreepanel',
                id: 'templateTree',
                detailPanelId: 'detail_panel'
            }]
        }],
        listeners: {
            beforecardchange: function(me, card, index, from, fromidx) {
                var node, selectedNode;
                if (index==1) {
                    node = treesm.getSelectedNode().attributes;
                    card.setHeaderText(node.text.text, node.path);
                } else if (index===0) {
                    Ext.getCmp('detail_nav').items.each(function(item){
                        selectedNode = item.getSelectionModel().getSelectedNode();
                        if ( selectedNode ) {
                            selectedNode.unselect();
                        }
                    });
                    Ext.getCmp('detail_panel').layout.setActiveItem(0);
                }
            },
            cardchange: function(me, card, index, from , fromidx) {
                var node = treesm.getSelectedNode(),
                    footer = Ext.getCmp('footer_bar');
                if (index===1) {
                    card.card.setContext(node.attributes.uid);
                    footer.buttonAdd.disable();
                    footer.buttonDelete.disable();
                } else if (index===0) {
                    Ext.History.add([node.getOwnerTree().id, node.id].join(Ext.History.DELIMITER));
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        footer.buttonAdd.enable();
                        footer.buttonDelete.enable();
                    }

                }
            }
        }
    },{
        xtype: 'contextcardpanel',
        id: 'detail_panel',
        region: 'center',
        activeItem: 0,
        split: true,
        items: [
            device_grid,
            {
                xtype: 'EventGridPanel',
                id: 'events_grid',
                stateId: 'organizer_event_panel',
                newwindowBtn: true,
                columns: Zenoss.env.COLUMN_DEFINITIONS,
                initComponent: Zenoss.EventGridPanel.prototype.initComponent.createSequence(function(){
                    var events_grid = Ext.getCmp('events_grid');
                    Zenoss.EventActionManager.configure({
                        onFinishAction: function() {
                            events_grid.updateRows();
                        },
                        findParams: function() {
                            return events_grid.getSelectionParameters();
                        }
                    });
               })
            },
            {
                id: 'modeler_plugins',
                xtype: 'modelerpluginpanel'
            },{
                id: 'configuration_properties',
                xtype: 'configpropertypanel'
            }
        ]
    }]
});


var bindTemplatesDialog = Ext.create({
    xtype: 'bindtemplatesdialog',
    id: 'bindTemplatesDialog'
});

var resetTemplatesDialog = Ext.create({
    xtype: 'resettemplatesdialog',
    id: 'resetTemplatesDialog'
});

function getOrganizerFields(mode) {
    var items = [];

    if ( mode == 'add' ) {
        items.push({
            xtype: 'textfield',
            id: 'id',
            fieldLabel: _t('Name'),
            allowBlank: false
        });
    }

    items.push({
        xtype: 'textfield',
        id: 'description',
        fieldLabel: _t('Description'),
        allowBlank: true
    });

    var rootId = treesm.getSelectedNode().getOwnerTree().getRootNode().attributes.id;
    if ( rootId === loctree.root.id ) {
        items.push({
            xtype: 'textarea',
            id: 'address',
            fieldLabel: _t('Address'),
            allowBlank: true
        });
    }

    return items;
}

var footerBar = Ext.getCmp('footer_bar');
    Zenoss.footerHelper(
    '',
    footerBar,
    {
        hasOrganizers: false,

        // this footer bar has an add to zenpack option, but it defines its
        // own in contrast to using the canned one in footerHelper
        addToZenPack: false,

        onGetDeleteMessage: function (itemName) {
            var node = treesm.getSelectedNode(),
                tree = node.getOwnerTree(),
                rootId = tree.getRootNode().attributes.id,
                msg = _t('Are you sure you want to delete the {0} {1}? <br/>There is <strong>no</strong> undo.');
            if (rootId==devtree.root.id) {
                msg = [msg, '<br/><br/><strong>',
                       _t('WARNING'), '</strong>:',
                       _t(' This will also delete all devices in this {0}.'),
                       '<br/>'].join('');
            }
            return String.format(msg, itemName.toLowerCase(), '/'+node.attributes.path);
        },
        onGetAddDialogItems: function () { return getOrganizerFields('add'); },
        onGetItemName: function() {
            var node = treesm.getSelectedNode();
            if ( node ) {
                var tree = node.getOwnerTree();
                return tree.nodeName=='Device'?'Device Class':tree.nodeName;
            }
        },
        customAddDialog: {
        },
        buttonContextMenu: {
        xtype: 'ContextConfigureMenu',
            onSetContext: function(uid) {
                bindTemplatesDialog.setContext(uid);
                resetTemplatesDialog.setContext(uid);
                Zenoss.env.PARENT_CONTEXT = uid;

            },
            onGetMenuItems: function(uid) {
                var menuItems = [];
                if (uid.match('^/zport/dmd/Devices')) {
                    menuItems.push([
                        {
                            xtype: 'menuitem',
                            text: _t('Bind Templates'),
                            hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
                            handler: function() {
                                bindTemplatesDialog.show();
                            }
                        },
                        {
                            xtype: 'menuitem',
                            text: _t('Reset Bindings'),
                            hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
                            handler: function(){
                                resetTemplatesDialog.show();
                            }
                        }
                    ]);
                }

                menuItems.push({
                    xtype: 'menuitem',
                    text: _t('Clear Geocode Cache'),
                    hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function() {
                        REMOTE.clearGeocodeCache({}, function(data) {
                            var msg = (data.success) ?
                                    _t('Geocode Cache has been cleared') :
                                    _t('Something happened while trying to clear Geocode Cache');
                            var dialog = new Zenoss.dialog.SimpleMessageDialog({
                                message: msg,
                                buttons: [
                                    {
                                        xtype: 'DialogButton',
                                        text: _t('OK')
                                    }
                                ]
                            });
                            dialog.show();
                        });
                    }
                });

                menuItems.push({
                    xtype: 'menuitem',
                    text: _t('Edit'),
                    hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function() {
                        var node = treesm.getSelectedNode();

                        var dialog = new Zenoss.SmartFormDialog({
                            title: _t('Edit Organizer'),
                            formId: 'editDialog',
                            items: getOrganizerFields(),
                            formApi: {
                                load: REMOTE.getInfo
                            }
                        });

                        dialog.setSubmitHandler(function(values) {
                            values.uid = node.attributes.uid;
                            REMOTE.setInfo(values);
                        });

                        dialog.getForm().load({
                            params: { uid: node.attributes.uid, keys: ['id', 'description', 'address'] },
                            success: function(form, action) {
                                dialog.show();
                            },
                            failure: function(form, action) {
                                Ext.Msg.alert('Error', action.result.msg);
                            }
                        });

                    }
                });

                return menuItems;
            }
        }
    }
);

footerBar.on('buttonClick', function(actionName, id, values) {
    var tree = treesm.getSelectedNode().getOwnerTree();
    switch (actionName) {
        // All items on this are organizers, no classes
        case 'addClass': tree.addChildNode(Ext.apply(values, {type: 'organizer'})); break;
        case 'addOrganizer': throw new Ext.Error('Not Implemented');
        case 'delete': tree.deleteSelectedNode(); break;
        default: break;
    }
});

}); // Ext. OnReady

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

Ext.ns('Zenoss.devices');


// page level variables
var REMOTE = Zenoss.remote.DeviceRouter;
var treeId = 'groups';
var nodeType = 'Organizer';
var deleteDeviceMessage = _t('Warning! This will delete all of the devices in this group!');
var ZEvActions = Zenoss.events.EventPanelToolbarActions;

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
            var type = Zenoss.types.type(selnode.attributes.uid);
                    var isclass = type === 'DeviceClass';
            if(selnode.attributes.uid === "/zport/dmd/Devices" ){
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
    Ext.getCmp('commands-menu').setDisabled(bool);
    Ext.getCmp('actions-menu').setDisabled(bool);
}

function resetGrid() {
    Ext.getCmp('device_grid').view.nonDisruptiveReset();
    setDeviceButtonsDisabled(true);
}

var treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function(sm, newnode, oldnode){
            if (newnode) {
                var uid = newnode.attributes.uid;
                Zenoss.util.setContext(uid, 'detail_panel', 'organizer_events',
                                       'commands-menu', 'context-configure-menu');
                setDeviceButtonsDisabled(true);
                var card = Ext.getCmp('master_panel').getComponent(0);
                //should "ask" the DetailNav if there are any details before showing
                //the button
                card.navButton.show();
                Ext.getCmp('master_panel').getComponent(1).navButton.show();
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
    lockDevices: new Zenoss.Action({
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
                            opts = gridOptions();
                        Ext.each(cbs, function(cb) {
                            opts[cb.name] = true;
                        });
                        REMOTE.lockDevices(opts, resetGrid);
                    }
                }, Zenoss.dialog.CANCEL
                ]
            });
            win.show();
        }
    }),
    resetIP: new Zenoss.Action({
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
                            REMOTE.resetIp(gridOptions(), resetGrid);
                            break;
                        default:
                            break;
                    }
                }
            });
        }
    }),
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
    setProdState: new Zenoss.Action({
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
                        var opts = Ext.apply(gridOptions(), {
                            prodState:Ext.getCmp('prodstate').getValue()
                        });
                        REMOTE.setProductionState(opts, resetGrid);
                    }
                }, Zenoss.dialog.CANCEL
                ]
            });
            win.show();
        }
    }),
    setPriority: new Zenoss.Action({
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
                        var opts = Ext.apply(gridOptions(), {
                            priority: Ext.getCmp('priority').getValue()
                        });
                        REMOTE.setPriority(opts, resetGrid);
                    }
                }, Zenoss.dialog.CANCEL
                ]
            });
            win.show();
        }
    }),
    setCollector: new Zenoss.Action({
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
                        var opts = Ext.apply(gridOptions(), {
                            collector: Ext.getCmp('collector').getValue()
                        });
                        REMOTE.setCollector(opts, resetGrid);
                    }
                }, Zenoss.dialog.CANCEL
                ]
            });
            win.show();
        }
    }),
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
                        Zenoss.remote.DeviceRouter.removeDevices(opts,
                             function(response) {
                                 var devtree = Ext.getCmp('devices'),
                                 loctree = Ext.getCmp('locs'),
                                 grptree = Ext.getCmp('groups');
                                 resetGrid();
                                 devtree.update(response.devtree);
                                 loctree.update(response.loctree);
                                 grptree.update(response.grptree);
                                 grid.view.showLoadMask(false);
                             }
                        );
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
                                var success = response.success;
                                if (success) {
                                    var dialog = new Zenoss.dialog.SimpleMessageDialog({
                                        message: 'Add Device Job submitted',
                                        buttons: [{
                                            xtype: 'DialogButton',
                                            text: _t('OK')
                                        }, {
                                            xtype: 'button',
                                            text: _t('View Job Log'),
                                            handler: function() {
                                                var url = '/zport/dmd/JobManager/jobs/' +
                                                response.jobId +
                                                '/viewlog';
                                                window.location = url;
                                            }
                                        }]
                                    });
                                    dialog.show();
                                }
                                var jobId = response.jobId;
                                Zenoss.message('add device submitted', success);
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
        permission: 'Manage DMD',
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
            target: treesm.getSelectedNode().attributes.uid,
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


function initializeTreeDrop(g) {
    var dz = new Ext.tree.TreeDropZone(g, {
        ddGroup: 'devicegriddd',
        getTargetFromEvent: function(e) {
            return e.getTarget('.x-tree-node-el');
        },
        onNodeOver : function(target, dd, e, data){
            // Return the class that makes the check mark
            return Ext.dd.DropZone.prototype.dropAllowed;
        },
        onNodeDrop: function(target, dd, e, data) {
            var nodeid = target.getAttribute('ext:tree-node-id'),
                grid = Ext.getCmp('device_grid'),
                tree = this.tree,
                targetnode = tree.getNodeById(nodeid),
                targetuid = targetnode.attributes.uid,
                ranges = grid.getSelectionModel().getPendingSelections(true),
                devids;

            devids = Ext.pluck(Ext.pluck(data.selections, 'data'), 'uid');

            grid.view.showLoadMask(true);

            var opts = Ext.apply(grid.view.getFilterParams(true), {
                uids: devids,
                ranges: ranges,
                target: targetuid
            });

            REMOTE.moveDevices(opts, function(data){
                if(data.success) {
                    resetGrid();
                    tree.update(data.tree);
                } else {
                    grid.view.showLoadMask(false);
                }
            }, this);
        }
    });
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
    id: 'devices',
    searchField: true,
    directFn: REMOTE.getTree,
    root: {
        id: 'Devices',
        uid: '/zport/dmd/Devices',
        text: 'Device Classes'
    },
    selectByToken: detailSelectByToken,
    selModel: treesm,
    router: REMOTE,
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
    id: 'groups',
    searchField: false,
    directFn: REMOTE.getTree,
    selectByToken: detailSelectByToken,
    root: {
        id: 'Groups',
        uid: '/zport/dmd/Groups'
    },
    selModel: treesm,
    router: REMOTE,
    selectRootOnLoad: false,
    listeners: { render: initializeTreeDrop }
};

var systree = {
    xtype: 'HierarchyTreePanel',
    id: 'systems',
    searchField: false,
    directFn: REMOTE.getTree,
    selectByToken: detailSelectByToken,
    root: {
        id: 'Systems',
        uid: '/zport/dmd/Systems'
    },
    router: REMOTE,
    selectRootOnLoad: false,
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};

var loctree = {
    xtype: 'HierarchyTreePanel',
    id: 'locs',
    searchField: false,
    directFn: REMOTE.getTree,
    selectByToken: detailSelectByToken,
    root: {
        id: 'Locations',
        uid: '/zport/dmd/Locations'
    },
    router: REMOTE,
    addNodeFn: REMOTE.addLocationNode,
    selectRootOnLoad: false,
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};

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
                        'events_grid': true
                    };
                    if (!excluded[navConfig.id]){
                        var config = detailNavPanel.panelConfigMap[navConfig.id];
                        Ext.applyIf(config, {refreshOnContextChange: true});
                        if(config && !Ext.getCmp(config.id)){
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
            'historyevents':true
        };
        return !excluded[config.id];
    },
    onGetNavConfig: function(contextId) {
        var deviceNav = [{
            id: 'device_grid',
            text: 'Devices',
            listeners: {
                render: updateNavTextWithCount
            }
        },{
            id: 'events_grid',
            text: _t('Events')
        }];
        var otherNav = [];
        switch (Zenoss.types.type(contextId)) {
            case 'DeviceLocation':
                break;
            case 'DeviceClass':
                break;
            default:
                break;
        }
        return deviceNav.concat(otherNav);
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
            items: [devtree, grouptree, systree, loctree],
            autoScroll: true
        },{
            xtype: 'detailcontainer',
            buttonText: _t('See All'),
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
                var node = treesm.getSelectedNode();
                if (index==1) {
                    card.card.setContext(node.attributes.uid);
                } else if (index===0) {
                    Ext.History.add([node.getOwnerTree().id, node.id].join(Ext.History.DELIMITER));
                }
            }
        }
    },{
        xtype: 'contextcardpanel',
        id: 'detail_panel',
        region: 'center',
        activeItem: 0,
        split: true,
        items: [{
            xtype: 'DeviceGridPanel',
            ddGroup: 'devicegriddd',
            id: 'device_grid',
            enableDrag: true,
            sm: new Ext.ux.grid.livegrid.RowSelectionModel({
                listeners: {
                    selectionchange: function(sm) {
                        setDeviceButtonsDisabled(!sm.getSelected());
                    }
                }
            }),
            tbar: {
                xtype: 'largetoolbar',
                items: [{
                    xtype: 'eventrainbow',
                    id: 'organizer_events'
                }, '-', {
                    id: 'adddevice-button',
                    iconCls: 'adddevice',
                    disabled: Zenoss.Security.doesNotHavePermission("Manage DMD"),
                    menu:{
                        items: [
                        Zenoss.devices.addDevice,
                        Zenoss.devices.addMultiDevicePopUP
                        ]
                    }
                }, Zenoss.devices.deleteDevices, {
                    text: _t('Select'),
                    menu:[{
                        text: _t('All'),
                        handler: function() {
                            var grid = Ext.getCmp('device_grid');
                            grid.getSelectionModel().selectRange(0, grid.store.totalLength);
                        }
                    },{
                        text: _t('None'),
                        handler: function() {
                            var grid = Ext.getCmp('device_grid');
                            grid.getSelectionModel().clearSelections();
                        }
                    }]
                },
                '->',
                {
                    id: 'actions-menu',
                    text: _t('Actions'),
                    disabled: Zenoss.Security.doesNotHavePermission('Delete Device'),
                    menu: {
                        items: [
                            Zenoss.devices.lockDevices,
                            Zenoss.devices.resetIP,
                            Zenoss.devices.resetCommunity,
                            Zenoss.devices.setProdState,
                            Zenoss.devices.setPriority,
                            Zenoss.devices.setCollector
                        ]
                    }
                },{
                    id: 'commands-menu',
                    text: _t('Commands'),
                    setContext: function(uid) {
                        var me = Ext.getCmp('commands-menu'),
                            menu = me.menu;
                        REMOTE.getUserCommands({uid:uid}, function(data){
                            menu.removeAll();
                            Ext.each(data, function(d){
                                menu.add({
                                    text:d.id,
                                    tooltip:d.description,
                                    handler: commandMenuItemHandler
                                });
                            });
                        });
                    },
                    menu: {}
                }]
            }
        },{
            xtype: 'SimpleEventGridPanel',
            id: 'events_grid',
            stateful: false,
            columns: Zenoss.env.COLUMN_DEFINITIONS,
            tbar: {
                xtype: 'toolbar',
                cls: 'largetoolbar consolebar',
                height: 35,
                items: [{
                    xtype: 'tbtext',
                    text: _t('Event Console')
                },
                    '-',
                    ZEvActions.acknowledge,
                    ZEvActions.close
                ]
            }
        }]
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
            xtype: 'textfield',
            id: 'address',
            fieldLabel: _t('Address'),
            allowBlank: true
        });
    }

    return items;
}

var footerBar = Ext.getCmp('footer_bar');
    Zenoss.footerHelper(
    _t('Tree Node'),
    footerBar,
    {
        hasOrganizers: false,

        // this footer bar has an add to zenpack option, but it defines its
        // own in contrast to using the canned one in footerHelper
        addToZenPack: false,

        onGetDeleteMessage: function (itemName) {
            var rootId = treesm.getSelectedNode().getOwnerTree().getRootNode().attributes.id;
            if ( rootId === devtree.root.id ) {
                return deleteDeviceMessage;
            }
            else {
                return String.format(_t('The selected {0} will be deleted.'), itemName.toLowerCase());
            }
        },
        onGetAddDialogItems: function () { return getOrganizerFields('add') },
        customAddDialog: {
            title: _t('Add Tree Node')
        },
        buttonContextMenu: {
        xtype: 'ContextConfigureMenu',
            onSetContext: function(uid) {
                bindTemplatesDialog.setContext(uid);
                resetTemplatesDialog.setContext(uid);
            },
            onGetMenuItems: function(uid) {
                var menuItems = [];
                if (uid.match('^/zport/dmd/Devices')) {
                    menuItems.push([
                        {
                            xtype: 'menuitem',
                            text: _t('Bind Templates'),
                            handler: function() {
                                bindTemplatesDialog.show();
                            }
                        },
                        {
                            xtype: 'menuitem',
                            text: _t('Reset Bindings'),
                            handler: function(){
                                resetTemplatesDialog.show();
                            }
                        }
                    ]);
                }

                menuItems.push({
                    xtype: 'menuitem',
                    text: _t('Clear Geocode Cache'),
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
        case 'addOrganizer': throw new Ext.Error('Not Implemented'); break;
        case 'delete': tree.deleteSelectedNode(); break;
        default: break;
    }
});

}); // Ext. OnReady

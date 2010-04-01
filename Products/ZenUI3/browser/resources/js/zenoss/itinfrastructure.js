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
                
// These are the fields that will display on the "Add a Node form" 
var addNodeDialogItems = [{
        // since they can only have organizer, we will just use a hidden field
        xtype: 'hidden',
        id: 'typeCombo',
        value: nodeType
    }, {
        xtype: 'textfield',
        id: 'idTextfield',
        width: 270,
        fieldLabel: _t('ID'),
        allowBlank: false        
    }
];
    
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

Zenoss.devices.PriorityCombo = Ext.extend(Ext.form.ComboBox, {
    constructor: function(config) {
        config = Ext.apply(config || {}, {
            fieldLabel: _t('Priority'),
            mode: 'local',
            store: new Ext.data.ArrayStore({
                data: Zenoss.env.PRIORITIES,
                fields: ['name', 'value']
            }),
            valueField: 'value',
            displayField: 'name',
            forceSelection: true,
            editable: false,
            autoSelect: true,
            triggerAction: 'all'
        });
        Zenoss.devices.PriorityCombo.superclass.constructor.call(this, config);
    }
});

Ext.reg('PriorityCombo', Zenoss.devices.PriorityCombo);


Zenoss.devices.ProductionStateCombo = Ext.extend(Ext.form.ComboBox, {
    constructor: function(config) {
        config = Ext.apply(config || {}, {
            fieldLabel: _t('Production State'),
            mode: 'local',
            store: new Ext.data.ArrayStore({
                data: Zenoss.env.PRODUCTION_STATES,
                fields: ['name', 'value']
            }),
            valueField: 'value',
            displayField: 'name',
            forceSelection: true,
            editable: false,
            autoSelect: true,
            triggerAction: 'all'
        });
        Zenoss.devices.ProductionStateCombo.superclass.constructor.call(this, config);
        
    }
});

Ext.reg('ProductionStateCombo', Zenoss.devices.ProductionStateCombo);

var resetCombo = function(combo, manufacturer) {
    combo.clearValue();
    combo.getStore().setBaseParam('manufacturer', manufacturer);
    delete combo.lastQuery;
    //combo.doQuery(combo.allQuery, true);
};

var manufacturerDataStore = new Ext.data.DirectStore({
        id: 'manufacturersStore',
        root: 'manufacturers',
        totalProperty: 'totalCount',
        fields: ['name'],
        directFn: REMOTE.getManufacturerNames
    });

var hwManufacturers = {
    xtype: 'combo',
    name: 'hwManufacturer',
    fieldLabel: _t('HW Manufacturer'),
    store: manufacturerDataStore,
    triggerAction: 'all',
    selectOnFocus: true,
    valueField: 'name',
    displayField: 'name',
    forceSelection: true,
    editable: false,
    width: 160,
    listeners: {'select': function(combo, record, index){
        var productCombo = Ext.getCmp('hwproductcombo');
        resetCombo(productCombo, record.data.name);
    }}
};

var hwProduct = {
    xtype: 'combo',
    minListWidth: 250,
    resizable: true,
    name: 'hwProductName',
    fieldLabel: _t('HW Product'),
    id: 'hwproductcombo',
    store: new Ext.data.DirectStore({
        id: 'hwProductsStore',
        root: 'productNames',
        totalProperty: 'totalCount',
        fields: ['name'],
        directFn: REMOTE.getHardwareProductNames
    }),
    triggerAction: 'all',
    selectOnFocus: true,
    valueField: 'name',
    displayField: 'name',
    forceSelection: true,
    editable: false,
    width: 160
};

var osManufacturers = {
    xtype: 'combo',
    name: 'osManufacturer',
    fieldLabel: _t('OS Manufacturer'),
    store: manufacturerDataStore,
    triggerAction: 'all',
    selectOnFocus: true,
    valueField: 'name',
    displayField: 'name',
    forceSelection: true,
    editable: false,
    width: 160,
    listeners: {'select': function(combo, record, index){
        var productCombo = Ext.getCmp('osproductcombo');
        resetCombo(productCombo, record.data.name);
    }}
};

var osProduct = {
    xtype: 'combo',
    minListWidth: 250,
    resizable: true,
    name: 'osProductName',
    id: 'osproductcombo',
    fieldLabel: _t('OS Product'),
    store: new Ext.data.DirectStore({
        id: 'osProductsStore',
        root: 'productNames',
        totalProperty: 'totalCount',
        fields: ['name'],
        directFn: REMOTE.getOSProductNames
    }),
    triggerAction: 'all',
    selectOnFocus: true,
    valueField: 'name',
    displayField: 'name',
    forceSelection: true,
    editable: false,
    width: 160
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
    Zenoss.devices.deleteDevices.setDisabled(bool);
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
            // set the footer_bar to bubble to new node
            var footer = Ext.getCmp('footer_bar');
            footer.bubbleTargetId = newnode.id;
            
            // Even after changing the ID I was not able to have 
            // each tree have their own instance of a deleteNodeDialog, so I
            // modified it to allow you to change the message
            var dialog = Ext.getCmp('deleteNodeDialog');
            if (newnode.id.match('Device')){
                dialog.setDeleteMessage(deleteDeviceMessage);
            }else{
                dialog.setDeleteMessage(null);
            }
            
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
        permission: 'Change Device',
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
                                        var index = component.store.find('value', '1000');
                                        if (index >= 0) {
                                            component.setValue('1000');
                                        }
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
                                        var index = component.store.find('value', '3');
                                        if (index >= 0) {
                                            component.setValue('3');
                                        }
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

var devtree = {
    xtype: 'HierarchyTreePanel',
    id: 'devices',
    searchField: true,
    deleteMessage: _t('The selected node will be deleted'),
    directFn: REMOTE.getTree,
    root: {
        id: 'Devices',
        uid: '/zport/dmd/Devices',
        text: 'Device Classes'
    },
    selModel: treesm,
    router: REMOTE,
    addNodeDialogItems: addNodeDialogItems,
    listeners: { 
        render: initializeTreeDrop, 
        filter: function(e) {
            Ext.getCmp('locs').filterTree(e);
            Ext.getCmp('groups').filterTree(e);
        }
    }
};

var grouptree = {
    xtype: 'HierarchyTreePanel',
    id: 'groups',
    searchField: false,
    directFn: REMOTE.getTree,
    deleteMessage: _t('The selected node will be deleted'),
    root: {
        id: 'Groups',
        uid: '/zport/dmd/Groups'
    },
    router: REMOTE,
    addNodeDialogItems: addNodeDialogItems,
    selectRootOnLoad: false,
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};

var loctree = {
    xtype: 'HierarchyTreePanel',
    id: 'locs',
    searchField: false,
    directFn: REMOTE.getTree,
    root: {
        id: 'Locations',
        uid: '/zport/dmd/Locations'
    },
    router: REMOTE,
    addNodeDialogItems: addNodeDialogItems,
    selectRootOnLoad: false,
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};

Zenoss.MonTemplateTreePanel = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config){
        Ext.applyIf(config, {
            id: 'templateTree',
            useArrows: true,
            border: false,
            cls: 'x-tree-noicon',
            selModel: new Ext.tree.DefaultSelectionModel({
                listeners: {
                    beforeselect: function(sm, node) {
                        return node.isLeaf();
                    },
                    selectionchange: function(sm, node) {
                        var itemSelModel, detail;
                        if (node) {
                            this.ownerCt.items.each(function(item){
                                itemSelModel = item.getSelectionModel();
                                if ( itemSelModel !== sm && itemSelModel.getSelectedNode() ) {
                                    itemSelModel.getSelectedNode().unselect(true);
                                }
                            });
                            detail = Ext.getCmp('detail_panel');
                            if ( ! detail.items.containsKey('montemplate') ) {
                                detail.add({
                                    xtype: 'templatecontainer',
                                    id: 'montemplate',
                                    ref: 'montemplate'
                                });
                            }
                            detail.montemplate.setContext(node.attributes.uid);
                            detail.getLayout().setActiveItem('montemplate');
                        }
                    },
                    scope: this
                }
            }),
            loader: {
                directFn: REMOTE.getTemplates,
                baseAttrs: {singleClickExpand: true}
            },
            root: {
                nodeType: 'async',
                id: '/zport/dmd/Devices',
                text: _t('Monitoring Templates'),
                expanded: true
            }
        });
        Zenoss.MonTemplateTreePanel.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        if ( uid.match('^/zport/dmd/Devices') ) {
            this.getRootNode().setId(uid);
            this.getRootNode().reload();
            this.show();
        } else {
            this.hide();
        }
    }
});
Ext.reg('montemplatetreepanel', Zenoss.MonTemplateTreePanel);

Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border': false
    },
    items: [{
        xtype: 'horizontalslide',
        id: 'master_panel',
        text: _t('IT Infrastructure'),
        region: 'west',
        split: true,
        width: 275,
        items: [{
            text: _t('IT Infrastructure'),
            buttonText: _t('Details'),
            items: [devtree, grouptree, loctree],
            autoScroll: true
        },{
            id: 'detail_nav',
            xtype: 'detailnav',
            text: _t('Details'),
            target: 'detail_panel',
            buttonText: _t('See All'),
            menuIds: ['More','Add','TopLevel','Manage'],
            items: [{
                xtype: 'montemplatetreepanel'
            }],
            listeners:{
                navloaded: function( detailNavPanel, navConfig){
                    if (navConfig.id != 'device_grid'){
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
            },
            filterNav: function(navpanel, config){
                //nav items to be excluded
                var excluded = {
                    'status': true,
                    'classes': true,
                    'events': true,
                    'templates': true,
                    'performancetemplates': true
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
            onSelectionChange: function(detailNav, node) {
                var detailPanel = Ext.getCmp('detail_panel');
                var contentPanel = Ext.getCmp(node.attributes.id);
                contentPanel.setContext(detailNav.contextId); 
                detailPanel.layout.setActiveItem(node.attributes.id);
            }
        }],
        listeners: {
            beforecardchange: function(me, card, index, from, fromidx) {
                var node, selectedNode;
                if (index==1) {
                    node = treesm.getSelectedNode().attributes;
                    card.setHeaderText(node.text.text);
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
                if (index==1) {
                    var node = treesm.getSelectedNode().attributes;
                    card.card.setContext(node.uid);
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
            sm: new Zenoss.ExtraHooksSelectionModel({
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
                }, Zenoss.devices.deleteDevices,
                '->', 
                {
                    id: 'actions-menu',
                    text: _t('Actions'),
                    disabled: Zenoss.Security.doesNotHavePermission('Change Device'),
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
        }]
    }]
});


/*
 *
 *   footer_panel - the add/remove tree node buttons at the bottom
 *
 */ 
var footerPanel = Ext.getCmp('footer_panel');
footerPanel.removeAll();


footerPanel.add({
    xtype: 'TreeFooterBar',
    id: 'footer_bar',
    bubbleTargetId: treeId
});

var footerBar = Ext.getCmp('footer_bar');

footerBar.add({
    xtype: 'ContextConfigureMenu'
});
}); // Ext. OnReady

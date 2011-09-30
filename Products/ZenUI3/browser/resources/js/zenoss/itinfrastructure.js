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
    width: 250,
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
            var isclass = selnode.data.uid.startswith('/zport/dmd/Devices');

            if(selnode.data.uid === "/zport/dmd/Devices" || !isclass ){
                //root node doesn't have a path attr
                component.setValue('/');
            }
            else if (isclass) {
                var path = selnode.data.path;
                path = path.replace(/^Devices/,'');
                component.setRawValue(path);
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
    Ext.getCmp('device_grid').refresh();
    setDeviceButtonsDisabled(true);
}

treesm = Ext.create('Zenoss.TreeSelectionModel', {
    mode: 'single',
    listeners: {
        'selectionchange': function(sm, newnodes, oldnode){
            if (newnodes.length) {
                var newnode = newnodes[0];
                var uid = newnode.data.uid;
                Zenoss.util.setContext(uid, 'detail_panel', 'organizer_events',
                                       'commands-menu', 'footer_bar');
                setDeviceButtonsDisabled(true);

                // explicitly set the new security context (to update permissions)
                Zenoss.Security.setContext(uid);

                //should "ask" the DetailNav if there are any details before showing
                //the button
                Ext.getCmp('master_panel').items.each(function(card){
                    card.navButton.setVisible(!newnode.data.hidden);
                });
            }
        }
    }
});

function gridOptions() {
    var grid = Ext.getCmp('device_grid'),
    sm = grid.getSelectionModel(),
    rows = sm.getSelections(),
    pluck = Ext.pluck,
    uids = pluck(pluck(rows, 'data'), 'uid'),
    opts = Ext.apply(grid.filterRow.getSearchValues(), {
        uids: uids,
        // FIXME: Actually implement hashcheck
        hashcheck: null
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
                isclass = Zenoss.types.type(selnode.data.uid)=='DeviceClass',
                grpText = selnode.data.text.text;
            var win = new Zenoss.FormDialog({
                title: _t('Remove Devices'),
                modal: true,
                width: 300,
                height: 320,
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
                        inputValue: 'remove',
                        id: 'remove-radio',
                        name: 'removetype',
                        boxLabel: _t('Just remove from ') + grpText,
                        disabled: isclass,
                        checked: !isclass
                    },{
                        inputValue: 'delete',
                        id: 'delete-radio',
                        name: 'removetype',
                        boxLabel: _t('Delete completely'),
                        checked: isclass,
                        listeners: {
                            check: function(chbox, isChecked) {
                                Ext.getCmp('delete-device-events').setDisabled(!isChecked);
                                Ext.getCmp('delete-device-perf-data').setDisabled(!isChecked);
                            }
                        }
                    }]
                },{
                    id: 'delete-device-events',
                    fieldLabel: _t('Delete Events?'),
                    xtype: 'checkbox',
                    checked: true,
                    disabled: !isclass
                },{
                    id: 'delete-device-perf-data',
                    fieldLabel: _t('Delete performance data?'),
                    xtype: 'checkbox',
                    checked: true,
                    disabled: !isclass
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Remove'),
                    handler: function(b) {
                        var opts = Ext.apply(gridOptions(), {
                            uid: Zenoss.env.PARENT_CONTEXT,
                            action: Ext.getCmp('removetype').getValue().removetype,
                            deleteEvents: Ext.getCmp('delete-device-events').getValue(),
                            deletePerf: Ext.getCmp('delete-device-perf-data').getValue()
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
                                     devtree.refresh();
                                     loctree.refresh();
                                     grptree.refresh();
                                     systree.refresh();
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
            var isclass = Zenoss.types.type(selnode.data.uid) == 'DeviceClass';
            var grpText = selnode.data.text.text;
            var win = new Zenoss.dialog.CloseDialog({
                width: 800,
                autoScroll: true,
                title: _t('Add a Single Device'),
                addOrganizers: function(response){
                    if (Ext.isDefined(response.systems)) {
                        this.systems = Ext.pluck(response.systems, 'name');
                    }

                    if (Ext.isDefined(response.groups)) {
                        this.groups = Ext.pluck(response.groups, 'name');
                    }

                    var panel = Ext.getCmp('add-device-organizer-column');
                    if (Ext.isDefined(this.systems) && Ext.isDefined(this.groups)) {

                        panel.add([{
                            xtype: 'multiselect',
                            fieldLabel: _t('Groups'),
                            name: 'groupPaths',
                            width: 200,
                            store: this.groups,
                            cls: 'multiselect-form-field',
                            // there is a bug in the multi select libarary to where
                            // clientvalidation calls getValue before the control is properly setup.
                            // The control is set up in OnRender which is not called yet because it is hidden
                            // until the user presses the "more" link"
                            // We get around that by creating a dummy view on the multi-selects
                            view: new Ext.ListView({
                                columns: [{ header: 'Value', width: 1, dataIndex: "test" }]
                            })
                        },{
                            xtype: 'multiselect',
                            fieldLabel: _t('Systems'),
                            name: 'systemPaths',
                            width: 200,
                            store: this.systems,
                            cls: 'multiselect-form-field',
                            view: new Ext.ListView({
                                columns: [{ header: 'Value', width: 1, dataIndex: "test" }]
                            })
                        }]);
                        panel.doLayout();
                    }

                },
                listeners: {
                    show: function(panel) {
                        if (!Ext.isDefined(this.systems) && !(Ext.isDefined(this.groups))) {
                            REMOTE.getSystems({}, panel.addOrganizers.createDelegate(panel));
                            REMOTE.getGroups({}, panel.addOrganizers.createDelegate(panel));
                        }
                    }
                },
                items: [{
                    xtype: 'form',
                    buttonAlign: 'left',
                    monitorValid: true,
                    labelAlign: 'top',
                    footerStyle: 'padding-left: 0',
                    border: false,
                    ref: 'childPanel',
                    items: [{
                        xtype: 'panel',
                        layout: 'column',
                        border: false,
                        items: [{
                            columnWidth: 0.5,
                            border: false,
                            layout: 'anchor',
                            items: [{
                                xtype: 'textfield',
                                name: 'deviceName',
                                width:250,
                                fieldLabel: _t('Name or IP'),
                                id: "add-device-name",
                                allowBlank: false
                            }, deviceClassCombo, {
                                xtype: 'combo',
                                width: 250,
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
                                width:250,
                                fieldLabel: _t('Model Device'),
                                id: 'add-device-protocol',
                                checked: true
                            }]
                        }, {
                            columnWidth: 0.5,
                            layout: 'anchor',
                            border: false,
                            items: [{
                                xtype: 'textfield',
                                name: 'title',
                                width:250,
                                fieldLabel: _t('Title')
                            }, {
                                xtype: 'ProductionStateCombo',
                                name: 'productionState',
                                minListWidth: 250,
                                id: 'production-combo',
                                width: 250,
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
                                minListWidth: 250,
                                width: 250,
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
                                win.center();
                                win.doLayout();
                            },
                            collapse: function(){
                                win.center();
                                win.doLayout();
                            }
                        },
                        items: [{
                            columnWidth: 0.33,
                            layout: 'anchor',
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
                            layout: 'anchor',
                            border: false,
                            items: [hwManufacturers, hwProduct, osManufacturers, osProduct]
                        }, {
                            columnWidth: 0.34,
                            layout: 'anchor',
                            id: 'add-device-organizer-column',
                            border: false,
                            items: [{
                                xtype: 'textarea',
                                name: 'comments',
                                width: '200',
                                fieldLabel: _t('Comments'),
                                emptyText: _t('None...'),
                                width: 200
                            },{
                                xtype: 'locationdropdown',
                                name: 'locationPath',
                                fieldLabel: _t('Location'),
                                emptyText: _t('None...'),
                                width: 200
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
                            var opts = form.getValues();
                            // adjust the system paths and grouppaths
                            if (opts.systemPaths) {
                                opts.systemPaths = opts.systemPaths.split(",");
                            }
                            if (opts.groupPaths) {
                                opts.groupPaths = opts.groupPaths.split(",");
                            }
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
        // only global roles can do this action
        permissionContext: '/zport/dmd/Devices',
        handler: function(btn, e){
            window.open('/zport/dmd/easyAddDevice', "multi_add",
            "menubar=0,toolbar=0,resizable=0,height=580, width=800,location=0");
        }
    })
});

function commandMenuItemHandler(item) {
    var command = item.text,
        grid = Ext.getCmp('device_grid'),
        sm = grid.getSelectionModel(),
        selections = sm.getSelections(),
        devids = Ext.pluck(Ext.pluck(selections, 'data'), 'uid');
    function showWindow() {
        var win = new Zenoss.CommandWindow({
            uids: devids,
            target: treesm.getSelectedNode().data.uid + '/run_command',
            command: command
        });
        win.show();
    }

    showWindow();

}


function updateNavTextWithCount(node) {
    var sel = treesm.getSelectedNode();
    if (sel && Ext.isDefined(sel.data.text.count)) {
        var count = sel.data.text.count;
        node.setText('Devices ('+count+')');
    }
}


function getTreeDropWarnings(dropTargetNode, droppedRecords) { 
    // if we're moving a device to a device class whose underlying python class does not match, also warn
    // about the potentially destructive operation.
    var additionalWarnings = [""];
    if (dropTargetNode && droppedRecords) {
        var dropTargetClass = dropTargetNode.data.zPythonClass || "Products.ZenModel.Device";
        var droppedClasses = Ext.Array.map(droppedRecords, function(r){return r.data.pythonClass});
        if(Ext.Array.some(droppedClasses, function(droppedClass) { return dropTargetClass!=droppedClass;})) {
            additionalWarnings = additionalWarnings.concat(_t("WARNING: This may result in the loss of all components and configuration under these devices."));
        }
    }
    return additionalWarnings.join('<br><br>');
}


function initializeTreeDrop(tree) {

    // fired when the user actually drops a node
    tree.getView().on('beforedrop', function(element, e, targetnode) {
        var grid = Ext.getCmp('device_grid'),
            targetuid = targetnode.data.uid,
            ranges = grid.getSelectionModel().getSelections(),
            devids,
            me = this,
            isOrganizer = true,
            success = true;
        if (e.records) {
            // the tree drag and drop wraps the model in a node interface so we
            // need to look at the uid to figure out what they are dropping
            isOrganizer = e.records[0].get("uid").indexOf('/devices/') == -1;
        }

        if (!isOrganizer ) {
            // move devices to the target node
            devids = Ext.pluck(Ext.pluck(e.records, 'data'), 'uid');
            // show the confirmation about devices
            Ext.Msg.show({
                title: _t('Move Devices'),
                msg: String.format(_t("Are you sure you want to move these {0} device(s) to {1}?") + getTreeDropWarnings(targetnode, e.records),
                                   devids.length, targetnode.data.text.text),
                buttons: Ext.Msg.OKCANCEL,
                fn: function(btn) {

                    if (btn =="ok") {
                        // move the devices
                        var opts= {
                            uids: devids,
                            ranges: [],
                            target: targetuid
                        };
                        REMOTE.moveDevices(opts, function(data){
                            if(data.success) {
                                resetGrid();
                                Ext.History.add(me.id + Ext.History.DELIMITER + targetnode.data.uid.replace(/\//g, '.'));
                                me.refresh();
                                if(data.exports) {
                                    Ext.Msg.show({
                                        title: _t('Remodel Required'),
                                        msg: String.format(_t("Not all of the configuration could be preserved, so a remodel of the device(s) is required. Performance templates have been reset to the defaults for the device class.")),
                                        buttons: Ext.Msg.OK});
                                }
                            }
                        }, me);
                    }else {
                        Ext.Msg.hide();
                    }
                }
            });
            // if we return true a dummy node will be appended to the tree
            return false;
        }else {

            // move the organizer under the target node
            var record = e.records[0];
            var organizerUid = record.get("uid");
            if (!tree.canMoveOrganizer(organizerUid, targetuid)) {
                return false;
            }

            // show the confirmation about organizers
            // show a confirmation for organizer move
            Ext.Msg.show({
                title: _t('Move Organizer'),
                msg: String.format(_t("Are you sure you want to move {0} to {1}?"), record.get("text").text, targetnode.get("text").text),
                buttons: Ext.Msg.OKCANCEL,
                fn: function(btn) {
                    if (btn=="ok") {
                        // move the organizer
                        var params = {
                            organizerUid: organizerUid,
                            targetUid: targetuid
                        };
                        REMOTE.moveOrganizer(params, function(data){
                            if(data.success) {
                                // add the new node to our history
                                Ext.History.add(me.id + Ext.History.DELIMITER + data.data.uid.replace(/\//g, '.'));
                                tree.refresh({
                                    callback: resetGrid
                                });
                            }
                        }, me);
                    }else {
                        Ext.msg.hide();
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

        // switch to the "details" panel
        container.setActiveItem(1);

        // wait until the nav has loaded from the server to
        // select the nav item
        item.on('navloaded', function(){
            item.selectByToken(parts[1]);
        }, item, {single: true});
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

var treeLoaderFn = REMOTE.getTree, treeStateful = true;
if (Zenoss.settings.incrementalTreeLoad) {
    // treeLoaderFn = REMOTE.asyncGetTree;
    // treeStateful = false;
}

var devtree = {
    xtype: 'HierarchyTreePanel',
    loadMask: false,
    id: 'devices',
    searchField: true,
    // directFn: Zenoss.util.isolatedRequest(treeLoaderFn),
    directFn: treeLoaderFn,
    extraFields: [{name: 'zPythonClass', type: 'string'}],
    allowOrganizerMove: false,
    stateful: treeStateful,
    stateId: 'device_tree',
    ddAppendOnly: true,
    root: {
        id: 'Devices',
        uid: '/zport/dmd/Devices',
        text: 'Device Classes'
    },
    ddGroup: 'devicegriddd',
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
    directFn: treeLoaderFn,
    stateful: treeStateful,
    stateId: 'group_tree',
    ddAppendOnly: true,
    selectByToken: detailSelectByToken,
    root: {
        id: 'Groups',
        uid: '/zport/dmd/Groups'
    },
    ddGroup: 'devicegriddd',
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
    stateful: treeStateful,
    stateId: 'systems_tree',
    searchField: false,
    directFn: treeLoaderFn,
    ddAppendOnly: true,
    selectByToken: detailSelectByToken,
    root: {
        id: 'Systems',
        uid: '/zport/dmd/Systems'
    },
    ddGroup: 'devicegriddd',
    nodeName: 'System',
    router: REMOTE,
    selectRootOnLoad: false,
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};

var loctree = {
    xtype: 'HierarchyTreePanel',
    loadMask: false,
    stateful: treeStateful,
    stateId: 'loc_tree',
    id: 'locs',
    searchField: false,
    directFn: treeLoaderFn,
    ddAppendOnly: true,
    selectByToken: detailSelectByToken,
    root: {
        id: 'Locations',
        uid: '/zport/dmd/Locations'
    },
    ddGroup: 'devicegriddd',
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

Ext.define("Zenoss.InfraDetailNav", {
    alias:['widget.infradetailnav'],
    extend:"Zenoss.DetailNavPanel",
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
                var navtree = this.down('detailnavtreepanel');
                var n = navtree.getRootNode().findChild('id', nodeId);
                if (n) {
                    navtree.getSelectionModel().select(n);
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
    onSelectionChange: function(nodes) {
        var node;
        if ( nodes.length ) {
            node = nodes[0];
            var detailPanel = Ext.getCmp('detail_panel');
            var contentPanel = Ext.getCmp(node.data.id);
            contentPanel.setContext(this.contextId);
            detailPanel.layout.setActiveItem(node.data.id);
            var orgnode = treesm.getSelectedNode();
            Ext.History.add([orgnode.getOwnerTree().id, orgnode.get("uid"), node.get("id")].join(Ext.History.DELIMITER));
        }
    }
});

var device_grid = Ext.create('Zenoss.DeviceGridPanel', {
    ddGroup: 'devicegriddd',
    id: 'device_grid',
    multiSelect: true,
    title: _t('/'),
    viewConfig: {
        plugins: {
            ptype: 'gridviewdragdrop',
            dragGroup: 'devicegriddd'
        }
    },
    listeners: {
        contextchange: function(grid, uid) {
            REMOTE.getInfo({uid: uid, keys: ['name', 'description', 'address']}, function(result) {
                var title = result.data.name,
                qtip,
                desc = [];
                if ( result.data.address ) {
                    desc.push(result.data.address);
                }
                if ( result.data.description ) {
                    desc.push(result.data.description);
                }

                if ( desc ) {
                    Ext.QuickTips.register({target: this.headerCt, text: Ext.util.Format.nl2br(desc.join('<hr>')), title: result.data.name});
                    this.setTitle(Ext.String.format("{0} - {1}", title, desc.join(' - ')));
                }else {
                    this.setTitle(title);
                }

            }, this);
        },
        scope: device_grid
    },
    selModel: new Zenoss.ExtraHooksSelectionModel({
        mode: 'MULTI',
        listeners: {
            selectionchange: function(sm) {
                setDeviceButtonsDisabled(!sm.hasSelection());
            }
        }
    }),
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
                width:210,
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
                menu:{
                    items: [
                        Zenoss.devices.addDevice,
                        Zenoss.devices.addMultiDevicePopUP
                    ].concat(EXTENSIONS_adddevice)
                }
            },
            Zenoss.devices.deleteDevices,
             {
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
            },'->',{
                id: 'refreshdevice-button',
                xtype: 'refreshmenu',
                ref: 'refreshmenu',
                stateId: 'devicerefresh',
                iconCls: 'refresh',
                text: _t('Refresh'),
                tooltip: _t('Refresh Device List'),
                handler: function(btn) {
                    Ext.getCmp('device_grid').refresh();
                    Ext.getCmp('organizer_events').setContext(Zenoss.env.PARENT_CONTEXT);
                }
            },
            {
                id: 'actions-menu',
                xtype: 'deviceactionmenu',
                deviceFetcher: gridOptions,
                saveHandler: function(){
                    resetGrid();
                    // show any errors
                    Zenoss.messenger.checkMessages();
                }
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
    var cmp = Ext.getCmp('master_panel_details');
    var btn = cmp.query("button[ref='details']")[0];
    if (btn) {
        btn.setDisabled(Zenoss.Security.doesNotHavePermission('Manage DMD'));
    }
    Ext.getCmp('commands-menu').setDisabled(Zenoss.Security.doesNotHavePermission('Run Commands'));
    Ext.getCmp('addsingledevice-item').setDisabled(Zenoss.Security.doesNotHavePermission('Manage DMD'));
    Ext.getCmp('actions-menu').setDisabled(Zenoss.Security.doesNotHavePermission('Change Device'));
});

function getInfrastructureDeviceColumns() {
    var columns = [
        'severity',
        'device',
        'component',
        'eventClass',
        'summary',
        'firstTime',
        'lastTime',
        'status',
        'count'
    ];
    var defs = Zenoss.env.COLUMN_DEFINITIONS;
    return  Zenoss.util.filter(defs, function(d){
        return Ext.Array.contains(columns, d.id);
    });
}

var event_console = Ext.create('Zenoss.EventGridPanel', {
    id: 'events_grid',
    stateId: 'infrastructure_events',
    columns: getInfrastructureDeviceColumns(),
    newwindowBtn: true,
    actionsMenu: false,
    commandsMenu: false,
    store: Ext.create('Zenoss.events.Store', {})
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
        cls: 'x-zenoss-master-panel',
        text: _t('Infrastructure'),
        region: 'west',
        split: true,
        width: 275,
        maxWidth: 275,
        items: [{
            id: 'master_panel_details',
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
                id: 'detail_nav',
                padding: '0 0 10px 0'
            }, {
                xtype: 'montemplatetreepanel',
                id: 'templateTree',
                detailPanelId: 'detail_panel'
            }]
        }],
        listeners: {
            beforecardchange: function(me, card, index, from, fromidx) {
                var node, selectedNode, tree;
                if (index==1) {
                    node = treesm.getSelectedNode().data;
                    card.setHeaderText(node.text.text, node.path);
                } else if (index===0) {
                    tree = Ext.getCmp('detail_nav').treepanel;
                    Ext.getCmp('detail_nav').items.each(function(item){
                        selectedNode = item.getSelectionModel().getSelectedNode();
                        if ( selectedNode ) {
                            tree.getSelectionModel().deselect(selectedNode);
                        }
                    });
                    Ext.getCmp('detail_panel').layout.setActiveItem(0);
                }
            },
            cardchange: function(me, card, index, from , fromidx) {
                var node = treesm.getSelectedNode(),
                    footer = Ext.getCmp('footer_bar');
                if (index===1) {
                    card.card.setContext(node.data.uid);
                    Ext.getCmp('footer_add_button').disable();
                    Ext.getCmp('footer_delete_button').disable();
                } else if (index===0) {
                    Ext.History.add([node.getOwnerTree().id, node.get("id")].join(Ext.History.DELIMITER));
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        Ext.getCmp('footer_add_button').enable();
                        Ext.getCmp('footer_delete_button').enable();
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
            event_console,
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


var bindTemplatesDialog = Ext.create('Zenoss.BindTemplatesDialog',{
    id: 'bindTemplatesDialog'
});

var resetTemplatesDialog = Ext.create('Zenoss.ResetTemplatesDialog', {
    id: 'resetTemplatesDialog'
});

function getOrganizerFields(mode) {
    var items = [];

    if ( mode == 'add' ) {
        items.push({
            xtype: 'textfield',
            id: 'id',
            name: 'id',
            fieldLabel: _t('Name'),
            allowBlank: false
        });
    }

    items.push({
        xtype: 'textfield',
        id: 'description',
        name: 'description',
        fieldLabel: _t('Description'),
        allowBlank: true
    });

    var rootId = treesm.getSelectedNode().getOwnerTree().root.id;
    if ( rootId === loctree.root.id ) {
        items.push({
            xtype: 'textarea',
            id: 'address',
            name: 'address',
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
                rootId = tree.getRootNode().data.id,
                msg = _t('Are you sure you want to delete the {0} {1}? <br/>There is <strong>no</strong> undo.');
            if (rootId==devtree.root.id) {
                msg = [msg, '<br/><br/><strong>',
                       _t('WARNING'), '</strong>:',
                       _t(' This will also delete all devices in this {0}.'),
                       '<br/>'].join('');
            }
            return String.format(msg, itemName.toLowerCase(), '/'+node.data.path);
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
                            values.uid = node.get("uid");
                            REMOTE.setInfo(values);
                        });
                        dialog.getForm().load({
                            params: { uid: node.data.uid, keys: ['id', 'description', 'address'] },
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

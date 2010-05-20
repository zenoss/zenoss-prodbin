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
Ext.ns('Zenoss', 'Zenoss.Network', 'Zenoss.Form');

Ext.onReady(function () {

//********************************************
// Add/remove sub-network buttons and dialog
//********************************************

var addNetwork = function(id) {
    var tree = Ext.getCmp('networks');

    tree.router.addNode({newSubnet: id},
        function(data) {
            if (data.success) {
                tree.getRootNode().reload(
                    function() {
//                        tree.expandAll();
//                        tree.collapseAll();
//                        tree.expandPath(
//                            tree.getNodeById(data.newNode.id).getPath());
                    }
                );
            }
        }
    );
};

var deleteNetwork = function() {
    var tree = Ext.getCmp('networks'),
        node = tree.getSelectionModel().getSelectedNode(),
        parentNode = node.parentNode,
        uid = node.attributes.uid;

    tree.router.deleteNode({uid:uid},
        function(data) {
            if (data.success) {
                tree.getRootNode().reload(
                    function() {
                        tree.getNodeById(parentNode.id).select();
                    }
                );
            }
        }
    );
};

var discoverDevicesDialogSubmit = function() {
    var tree = Ext.getCmp('networks'),
        node = tree.getSelectionModel().getSelectedNode();

    tree.router.discoverDevices( {uid: node.attributes.uid},
        function(data) {
            if (data.success) {
                var dialog = new Zenoss.dialog.SimpleMessageDialog( {
                    message: _t('Discover subnetwork job submitted'),
                    buttons: [{
                        xtype: 'DialogButton',
                        text: _t('OK')
                    }, {
                        xtype: 'button',
                        text: _t('View Job Log'),
                        handler: function() {
                            window.location = String.format(
                                '/zport/dmd/JobManager/jobs/{0}/viewlog',
                                data.jobId);
                        }
                    }]
                });
                dialog.show();
            }
        }
    );
};

var addNetworkDialogConfig = {
    title: _t('Add a Subnetwork'),
    items: [{
        xtype: 'textfield',
        name: 'id',
        fieldLabel: _t('Network / Subnet mask'),
        allowBlank: false
    }]
};

var discoverDevicesDialog = new Zenoss.MessageDialog({
    id: 'discoverDevicesDialog',
    title: _t('Discover Devices'),
    message: _t('Devices on the selected subnetwork will be discovered.'),
    okHandler: discoverDevicesDialogSubmit
});

//********************************************
// Navigation tree (select subnetwork)
//********************************************

var treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function (sm, newnode) {
            if (!newnode) return;
            Ext.getCmp('networkForm').setContext(newnode.attributes.uid);
            Ext.getCmp('ipAddressGrid').setContext(newnode.attributes.uid);

            if (Zenoss.Security.doesNotHavePermission('Manage DMD')) return;
            var fb = Ext.getCmp('footer_bar');
            fb.buttonDelete.setDisabled((newnode.attributes.id == 'Network') );
            fb.buttonContextMenu.menu.buttonDiscoverDevices.setDisabled(
                (newnode.attributes.id == 'Network') );
        }
    }
});


var network_tree = new Zenoss.HierarchyTreePanel({
    id: 'networks',
    searchField: true,
    directFn: Zenoss.remote.NetworkRouter.getTree,
    router: Zenoss.remote.NetworkRouter,
    root: {
        id: 'Network',
        uid: '/zport/dmd/Networks',
        text: null, // Use the name loaded from the remote
        allowDrop: false
    },
    selModel: treesm
});

Ext.getCmp('master_panel').add(network_tree);

//********************************************
// IP Addresses grid
//********************************************

var statusRenderer = function (statusNum) {
    var color = 'red',
        desc = _t('Down');
    if (statusNum === 0) {
        color = 'green';
        desc = _t('Up');
    }
    else if (statusNum == 5) {
        color = 'gray';
        desc = _t('N/A');
    }
    return '<span style="color:' + color + '">' + desc + '</span>';
};

var ipAddressColumnConfig = {
    defaults: {
        menuDisabled: true
    },
    columns: [{
            id: 'name',
            dataIndex: 'name',
            header: _t('Address'),
            width: 50
        }, {
            id: 'device',
            dataIndex: 'device',
            header: _t('Device'),
            width: 200,
            renderer: function(device, row, record){
                if (device === null) return 'No Device';
                return Zenoss.render.link(device.uid, undefined,
                                          device.name);
           }
        }, {
            id: 'interface',
            dataIndex: 'interface',
            header: _t('Interface'),
            width: 200,
            renderer: function(iface, row, record){
                if (iface === null) return 'No Interface';
                return iface.name;
           }
        }, {
            id: 'pingstatus',
            dataIndex: 'pingstatus',
            header: _t('Ping'),
            width: 50,
            renderer: function(pingNum, row, record){
                return statusRenderer(pingNum);
           }
        }, {
            id: 'snmpstatus',
            dataIndex: 'snmpstatus',
            header: _t('SNMP'),
            width: 50,
            renderer: function(snmpNum, row, record){
                return statusRenderer(snmpNum);
           }
        }
    ]
};

var ipAddressStoreConfig = {
        bufferSize: 50,
        proxy: new Ext.data.DirectProxy({
            directFn: Zenoss.remote.NetworkRouter.getIpAddresses
        }),
        reader: new Ext.ux.grid.livegrid.JsonReader({
            root: 'data',
            fields: [
                {name: 'name'},
                {name: 'device'},
                {name: 'interface'},
                {name: 'pingstatus'},
                {name: 'snmpstatus'}
            ]
        })
    };

var ipAddressGridConfig = {
        id: 'ipAddressGrid',
        border: false,
        autoExpandColumn: 'name',
        stripeRows: true,
        tbar: {
                items: [ { xtype: 'tbtext', text: _t('IP Addresses') } ]
        },
        cm: new Ext.grid.ColumnModel(ipAddressColumnConfig),
        store: new Ext.ux.grid.livegrid.Store(ipAddressStoreConfig)
    };

var ipAddressGrid = new Ext.ux.grid.livegrid.GridPanel(ipAddressGridConfig);

ipAddressGrid.setContext = function(uid) {
    this.contextUid = uid;
    this.getStore().load({ params: {uid: uid} });
}.createDelegate(ipAddressGrid);

Ext.getCmp('bottom_detail_panel').add(ipAddressGrid);

//********************************************
// Network form
//********************************************

// *** Form functions

var resetForm = function() {
    Ext.getCmp('networkForm').getForm().reset();
};

// *** Form field declarations

var addressDisplayField = {
    xtype: 'displayfield',
    id: 'addressDisplayField',
    fieldLabel: _t('Address'),
    name: 'name',
    width: "100%"
};

var ipcountDisplayField = {
    xtype: 'displayfield',
    id: 'ipcountDisplayField',
    fieldLabel: _t('IPs Used/Free'),
    name: 'ipcount',
    width: "100%"
};

var descriptionTextField = {
    xtype: 'textarea',
    id: 'descriptionTextArea',
    fieldLabel: _t('Description'),
    name: 'description',
    grow: true,
    width: "100%"
};

// *** Configuration Properties

var zAutoDiscover = {
    xtype: 'zprop',
    ref: '../../zAutoDiscover',
    title: _t('Perform Auto-discovery? (zAutoDiscover)'),
    name: 'zAutoDiscover',
    localField: {
        xtype: 'select',
        mode: 'local',
        store: [[true, 'Yes'], [false, 'No']]
    }
};

var zDefaultNetworkTree = {
    xtype: 'zprop',
    ref: '../../zDefaultNetworkTree',
    title: _t('Prefix Lengths of Organizers (zDefaultNetworkTree)'),
    name: 'zDefaultNetworkTree',
    localField: {
        xtype: 'textfield',
        width: '100%'
    }
};

var zPingFailThresh = {
    xtype: 'zprop',
    ref: '../../zPingFailThresh',
    title: _t('Number of Ping Failures for Down Device (zPingFailThresh)'),
    name: 'zPingFailThresh',
    localField: {
        xtype: 'numberfield'
    }
};

var zDrawMapLinks = {
    xtype: 'zprop',
    ref: '../../zDrawMapLinks',
    title: _t('Draw Map Links? (zDrawMapLinks)'),
    name: 'zDrawMapLinks',
    localField: {
        xtype: 'select',
        mode: 'local',
        store: [[true, 'Yes'], [false, 'No']]
    }
};

var zIcon = {
    xtype: 'zprop',
    ref: '../../zIcon',
    title: _t('Icon to Represent the Network (zIcon)'),
    name: 'zIcon',
    localField: {
        xtype: 'textfield'
    }  
};

var formItems = {
    layout: 'column',
    border: false,
    defaults: {
        layout: 'form',
        border: false,
        bodyStyle: 'padding: 15px',
        columnWidth: 0.5
    },
    items: [{
        items: [
            addressDisplayField,
            ipcountDisplayField,
            descriptionTextField
        ]
    }, {
        items: [
            zAutoDiscover,
            zDefaultNetworkTree,
            zPingFailThresh,
            zDrawMapLinks,
            zIcon
        ]
    }]
};

var formConfig = {
    xtype: 'form',
    id: 'networkForm',
    paramsAsHash: true,
    items: formItems,
    border: false,
    labelAlign: 'top',
    autoScroll: true,
    trackResetOnLoad: true,
    bbar: {
        xtype: 'largetoolbar',
        items: [{
            xtype: 'button',
            id: 'saveButton',
            ref: '../saveButton',
            text: _t('Save'),
            disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
            handler: function(){
                this.refOwner.getForm().submit({
                    params: {
                        uid: Ext.getCmp('networkForm').contextUid
                    }
                });
            }
        }, {
            xtype: 'button',
            id: 'cancelButton',
            text: _t('Cancel'),
            handler: resetForm
        }]
    },
    api: {
        load: Zenoss.remote.NetworkRouter.getInfo,
        submit: Zenoss.form.createDirectSubmitFunction(Zenoss.remote.NetworkRouter)
    }
};

var networkForm = new Ext.form.FormPanel(formConfig);
networkForm.setContext = function(uid) {
    this.contextUid = uid;
    this.load({ params: {uid: uid} });
}.createDelegate(networkForm);

Ext.getCmp('top_detail_panel').add(networkForm);

//********************************************
// Footer
//********************************************

var dispatcher = function(actionName, value) {
    switch (actionName) {
        case 'addClass': addNetwork(value); break;
        case 'delete': deleteNetwork(); break;
        default: break;
    }
};


var fb = Ext.getCmp('footer_bar');
fb.on('buttonClick', dispatcher);
Zenoss.footerHelper('Subnetwork', fb, {
    hasOrganizers: false,
    addToZenPack: false,
    customAddDialog: addNetworkDialogConfig
});
fb.buttonContextMenu.menu.add({
    tooltip: _t('Discover devices on selected subnetwork'),
    text: _t('Discover Devices'),
    iconCls: 'adddevice',
    ref: 'buttonDiscoverDevices',
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    handler: discoverDevicesDialog.show.createDelegate(discoverDevicesDialog)
});

});

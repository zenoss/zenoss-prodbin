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

    tree.router.addNode({newSubnet: id, contextUid: Zenoss.env.PARENT_CONTEXT},
        function(data) {
            if (data.success) {
                tree.getRootNode().reload(
                    function() {
                        tree.getRootNode().expandChildNodes();
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
            if (!newnode) {
                return;
            }
            var uid = newnode.attributes.uid,
                fb = Ext.getCmp('footer_bar');

            Ext.getCmp('networkForm').setContext(uid);
            Ext.getCmp('detail_panel').detailCardPanel.setContext(uid);

            if (Zenoss.Security.doesNotHavePermission('Manage DMD')) {
                return;
            }

            fb.buttonContextMenu.setContext(uid);
            Zenoss.env.PARENT_CONTEXT = uid;

            fb.buttonDelete.setDisabled(
                (newnode.attributes.id == '.zport.dmd.Networks'));
        }
    }
});

var NetworkNavTree = Ext.extend(Zenoss.HierarchyTreePanel, {

    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            listeners: {
                scope: this,
                load: this.onLoad
            },
            id: 'networks',
            directFn: Zenoss.remote.NetworkRouter.getTree,
            router: Zenoss.remote.NetworkRouter,
            searchField: true,
            selModel: treesm,
            root: {
                id: '.zport.dmd.Networks',
                uid: '/zport/dmd/Networks',
                text: null, // Use the name loaded from the remote
                allowDrop: false
            }
        });
        NetworkNavTree.superclass.constructor.call(this, config);
    },

    onLoad: function(node){
        // when a TreePanel load event fires for a parent node, all of its
        // child nodes have been registered, and getNodeById which is used in
        // selectByToken returns the node instead of null. This is a good time
        // to select the correct node based on the history token in the URL.

        // example token: 'networks:.zport.dmd.Networks.204.12.105.0.204.12.105.192'
        var token = Ext.History.getToken();

        if (token) {

            // Ext.History.DELIMITER is ':'
            var tokenRightPart = unescape( token.split(Ext.History.DELIMITER).slice(1) );
            var tokenNodeId = tokenRightPart.split('.ipaddresses.')[0];
            var tokenNodeIdParts = tokenNodeId.split('.');

            // strip the last network id off the token id
            // example tokenParentId: '.zport.dmd.Networks.204.12.105.0'
            var tokenParentId = tokenNodeIdParts.slice(0, tokenNodeIdParts.length - 4).join('.');

            if ( node.id === tokenParentId ) {
                this.selectByToken(tokenRightPart);
                
            } else if ( tokenParentId.indexOf(node.id) === 0 ) {
                // for nodes that aren't expanded by default, expand this 
                // loaded ancestor so it loads its children
                var ancestorIdLength = node.id.split('.').length + 4;
                var ancestorId = tokenNodeIdParts.slice(0, ancestorIdLength).join('.');
                var ancestorNode = this.getNodeById(ancestorId);
                if (ancestorNode) {
                    ancestorNode.expand();
                }
            }
            
        }
        
    },

    selectByToken: function(tokenRightPart) {
        // called from onLoad and Ext.History.selectByToken defined in
        // HistoryManager.js. If node is null when called fomr the History 
        // change event, then the TreePanel load event will call this function
        // when getNodeById is ready.
        var subParts = unescape(tokenRightPart).split('.ipaddresses.');
        var tokenNodeId = subParts[0];
        var node = this.getNodeById(tokenNodeId);
        if (node) {
            this.selectPath(node.getPath(), null, function(){
                var ipAddress = subParts[1];
                var instanceGrid = Ext.getCmp('ipAddressGrid');
                var store = instanceGrid.getStore();
                var selModel = instanceGrid.getSelectionModel();
                
                function selectIpAddress() {
                    store.un('load', selectIpAddress);
                    store.each(function(record){
                        if ( record.data.name === ipAddress ) {
                            selModel.selectRow( store.indexOf(record) );
                            return false;
                        }
                    });
                }
                
                selectIpAddress();
                
                if ( ! selModel.hasSelection() ) {
                    // no row selectected, wait for the store to load and try again
                    store.on('load', selectIpAddress);
                }
            });
        }
    }

});

Ext.reg('networknavtree', NetworkNavTree);

Ext.getCmp('master_panel').add(new NetworkNavTree());

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
                return Zenoss.render.link(iface.uid, null, iface.name);
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
        cm: new Ext.grid.ColumnModel(ipAddressColumnConfig),
        store: new Ext.ux.grid.livegrid.Store(ipAddressStoreConfig),
        sm: new Ext.ux.grid.livegrid.RowSelectionModel({
            singleSelect: true,
            listeners: {
                rowselect: function(selModel, rowIndex, record) {
                    var token = Ext.History.getToken();
                    var network = token.split('.ipaddresses.')[0];
                    Ext.History.add(network + '.ipaddresses.' + record.data.name);
                }
            }
        })
    };

var ipAddressGrid = new Ext.ux.grid.livegrid.GridPanel(ipAddressGridConfig);

ipAddressGrid.setContext = function(uid) {
    this.contextUid = uid;
    this.getStore().load({
        params: {
            uid: uid,
            start: 0,
            limit: 300
        }
    });
}.createDelegate(ipAddressGrid);

Ext.getCmp('detail_panel').add({
    xtype: 'instancecardpanel',
    ref: 'detailCardPanel',
    region: 'south',
    split: true,
    router: Zenoss.remote.NetworkRouter,
    instances: ipAddressGrid,
    instancesTitle: 'IP Addresses',
    zPropertyEditListeners: {
        frameload: function() {
            var formPanel = Ext.getCmp('networkForm');
            if (formPanel.contextUid) {
                formPanel.setContext(formPanel.contextUid);
            }
        }
    }
});

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

var zSnmpStrictDiscovery = {
    xtype: 'zprop',
    ref: '../../zSnmpStrictDiscovery',
    title: _t('Only Create Devices If SNMP Succeeds? (zSnmpStrictDiscovery)'),
    name: 'zSnmpStrictDiscovery',
    localField: {
        xtype: 'select',
        mode: 'local',
        store: [[true, 'Yes'], [false, 'No']]
    }
};

var zPreferSnmpNaming = {
    xtype: 'zprop',
    ref: '../../zPreferSnmpNaming',
    title: _t('Prefer Name Discovered Via SNMP to DNS? (zPreferSnmpNaming)'),
    name: 'zPreferSnmpNaming',
    localField: {
        xtype: 'select',
        mode: 'local',
        store: [[true, 'Yes'], [false, 'No']]
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
            zPreferSnmpNaming,
            zSnmpStrictDiscovery,
            zDrawMapLinks,
            zIcon
        ]
    }]
};

var networkFormConfig =  {
    xtype: 'basedetailform',
    trackResetOnLoad: true,
    id: 'networkForm',
    permission: 'Manage DMD',
    region: 'center',
    items: formItems,
    router: Zenoss.remote.NetworkRouter
}

var networkForm = Ext.getCmp('detail_panel').add(networkFormConfig);

networkForm.getForm().on('actioncomplete', function(basicForm, action){
    if (action.type == 'directsubmit') {
        var uid = Ext.getCmp('networks').getSelectionModel().getSelectedNode().attributes.uid;
        Ext.getCmp('detail_panel').detailCardPanel.setContext(uid);
    }
});

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
    customAddDialog: addNetworkDialogConfig,
    buttonContextMenu: {
        xtype: 'ContextConfigureMenu',
        id: 'network_context_menu',
        menuIds: ['Network'],
        onGetMenuItems: function(uid) {
            return [{
                tooltip: _t('Discover devices on selected subnetwork'),
                text: _t('Discover Devices'),
                iconCls: 'adddevice',
                ref: 'buttonDiscoverDevices',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                handler: discoverDevicesDialog.show.createDelegate(discoverDevicesDialog)
            }];
        }
    }
});

});

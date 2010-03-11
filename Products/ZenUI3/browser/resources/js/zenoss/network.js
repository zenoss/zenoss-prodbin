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
Ext.ns('Zenoss.Network');

Ext.onReady(function () {

// Adds a network or sub-network
addNetwork = function(e) {
    alert('add subnetwork -- disabled (debug)');
}

/*
 * Delete a network or subnetwork
 */
deleteNetwork = function(e) {
    alert('del subnetwork -- disabled (debug)');
}

//********************************************
// Navigation tree (select subnetwork)
//********************************************

Zenoss.NetworkTreeNodeUI = Ext.extend(Zenoss.HierarchyTreeNodeUI, {
    render: function (bulkRender) {
        var n = this.node;

        n.attributes.iconCls = 'severity-icon-small clear';
        
        if (n.isLeaf())
            n.text = n.attributes.text;
        else
            n.text = this.buildNodeText(this.node);

        Zenoss.NetworkTreeNodeUI.superclass.render.call(this,
                bulkRender);
    },
    onTextChange : function (node, text, oldText) {
        if ((this.rendered) && (!node.isLeaf())) {
            this.textNode.innerHTML = this.buildNodeText(node);
        }
    }
});

Zenoss.NetworkTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {
    constructor: function (config) {
        config.loader = {
            xtype: 'treeloader',
            directFn: Zenoss.remote.NetworkRouter.getTree,
            uiProviders: {
                'network': Zenoss.NetworkTreeNodeUI
            },
            getParams: function (node) {
                return [node.attributes.uid];
            }
        };
        Zenoss.NetworkTreePanel.superclass.constructor.call(this,
                config);
    }
});

var treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function (sm, newnode) {
            Ext.getCmp('networkForm').setContext(newnode.attributes.uid);
            Ext.getCmp('ipAddressGrid').setContext(newnode.attributes.uid);
        }
    }
});

var network_tree = new Zenoss.NetworkTreePanel({
    id: 'networks',
    searchField: true,
    router: Zenoss.remote.NetworkRouter,
    root: {
        id: 'Network',
        uid: '/zport/dmd/Networks',
        text: _t('Subnetworks'),
        allowDrop: false
    },
    selModel: treesm
});

Ext.getCmp('master_panel').add(network_tree);

//********************************************
// IP Addresses grid
//********************************************

statusRenderer = function (statusNum) {
    var color = 'red',
        desc = 'Down';
    if (statusNum == 0) {
        color = 'green';
        desc = 'Up';
    }
    else if (statusNum == 5) {
        color = 'gray';
        desc = 'N/A';
    }
    return '<span style="color:' + color + '">' + desc + '</span>';
}

ipAddressColumnConfig = {
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

ipAddressStoreConfig = {
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

ipAddressGridConfig = {
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

ipAddressGrid = new Ext.ux.grid.livegrid.GridPanel(ipAddressGridConfig);

ipAddressGrid.setContext = function(uid) {
    this.contextUid = uid;
    this.getStore().load({ params: {uid: uid} });
}.createDelegate(ipAddressGrid);

Ext.getCmp('bottom_detail_panel').add(ipAddressGrid);

//********************************************
// Network form
//********************************************
saveForm = function() {
    alert('save description -- disabled (debug)');
}

resetForm = function() {
    Ext.getCmp('networkForm').getForm().reset();
}

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
}

var descriptionTextField = {
    xtype: 'textfield',
    id: 'descriptionTextField',
    fieldLabel: _t('Description'),
    name: 'description',
    width: "100%"
};

formItems = {
    layout: 'column',
    border: false,
    defaults: {
        layout: 'form',
        border: false,
        bodyStyle: 'padding: 15px',
        labelSeparator: ' ',
        columnWidth: 0.5
    },
    items: [ {items: [addressDisplayField, ipcountDisplayField,
                      descriptionTextField] } ]
};

formConfig = {
    xtype: 'form',
    id: 'networkForm',
    paramsAsHash: true,
    items: formItems,
    border: false,
    labelAlign: 'top',
    autoScroll: true,
    trackResetOnLoad: true,
    bbar: {xtype: 'largetoolbar', items: [ {
        xtype: 'button',
        id: 'saveButton',
        text: _t('Save'),
        handler: saveForm
        }, {
        xtype: 'button',
        id: 'cancelButton',
        text: _t('Cancel'),
        handler: resetForm
        }
    ]},
    api: {
        load: Zenoss.remote.NetworkRouter.getInfo,
        submit: Zenoss.remote.NetworkRouter.setInfo
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

Ext.getCmp('footer_bar').add({
    id: 'add-button',
    tooltip: _t('Add a subnetwork'),
    iconCls: 'add',
    handler: addNetwork
});

Ext.getCmp('footer_bar').add({
    id: 'delete-button',
    tooltip: _t('Delete a subnetwork'),
    iconCls: 'delete',
    handler: deleteNetwork
});

});

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

var treeConfigs = new Ext.util.MixedCollection(false, function(config) {
    return config.root.uid;
});

treeConfigs.addAll([{
    id: 'networks',
    root: {
        id: '.zport.dmd.Networks',
        uid: '/zport/dmd/Networks',
        text: null, // Use the name loaded from the remote
        allowDrop: false
    },
    directFn: Zenoss.remote.NetworkRouter.asyncGetTree,
    router: Zenoss.remote.NetworkRouter
}, {
    id: 'ipv6networks',
    root: {
        id: '.zport.dmd.IPv6 Networks',
        uid: '/zport/dmd/IPv6 Networks',
        text: null, // Use the name loaded from the remote
        allowDrop: false
    },
    directFn: Zenoss.remote.Network6Router.asyncGetTree,
    router: Zenoss.remote.Network6Router
}]);

var getRootId = function(fn) {
    var config;
    treeConfigs.each(function(item) {
        if (Zenoss.env.PARENT_CONTEXT.indexOf(item.root.uid) === 0) {
            config = item;
            return false; //stops iteration
        }
        return true;
    });
    if (fn) {
        return fn(config);
    }
    return config.id;
};

var addNetwork = function(id) {
    var tree = Ext.getCmp(getRootId());

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
    var tree = Ext.getCmp(getRootId()),
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
    var tree = Ext.getCmp(getRootId()),
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

            Ext.getCmp('detail_panel').detailCardPanel.setContext(uid);

            if (Zenoss.Security.doesNotHavePermission('Manage DMD')) {
                return;
            }

            fb.buttonContextMenu.setContext(uid);
            Zenoss.env.PARENT_CONTEXT = uid;

            fb.buttonDelete.setDisabled(treeConfigs.containsKey(uid));
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
            selModel: treesm
        });
        NetworkNavTree.superclass.constructor.call(this, config);
    },

    onLoad: function(node){
        // when a TreePanel load event fires for a parent node, all of its
        // child nodes have been registered, and getNodeById which is used in
        // selectByToken returns the node instead of null. This is a good time
        // to select the correct node based on the history token in the URL.

        // example token:
        //'networks:.zport.dmd.Networks.204.12.105.0.ipaddresses.204.12.105.192'
        var token = Ext.History.getToken();

        if (token) {
            // Ext.History.DELIMITER is ':'
            var fromIndex = token.indexOf(Ext.History.DELIMITER)
                    + Ext.History.DELIMITER.length,
                tokenTreePath = token.substring(fromIndex);

            function expandToHistory(anode) {
                anode.expand();
                Ext.each(anode.childNodes, function(item) {
                    if (tokenTreePath.indexOf(item.id) === 0) {
                        expandToHistory(item);
                    }
                });
            };
            expandToHistory(node);

            this.selectByToken(tokenTreePath);
        } else {
            var networktree = Ext.getCmp("networks");
            networktree.selectByToken(networktree.root.id);
        }
    },

    selectByToken: function(tokenTreePath) {
        // called from onLoad and Ext.History.selectByToken defined in
        // HistoryManager.js. If node is null when called from the History
        // change event, then the TreePanel load event will call this function
        // when getNodeById is ready.
        var subParts = unescape(tokenTreePath).split('.ipaddresses.');
        var tokenNodeId = subParts[0];
        var node = this.getNodeById(tokenNodeId);
        if (node) {
            this.selectPath(node.getPath(), null, function(){
                var ipAddress = subParts[1];
                var instanceGrid = Ext.getCmp('detail_panel').detailCardPanel.instancesGrid;
                var store = instanceGrid.getStore();
                var selModel = instanceGrid.getSelectionModel();

                function selectIpAddress() {
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
                    store.on('load', selectIpAddress, store, {single:true});
                }
            });
        }
    },

    afterRender: function() {
        NetworkNavTree.superclass.afterRender.call(this);

        Ext.getCmp("networkSearchField").addListener('valid',
                this.filterTree,
                this);
    }

});

Ext.reg('networknavtree', NetworkNavTree);

var treePanelItems = [{
    id: 'networkSearchField',
    xtype: 'searchfield',
    bodyStyle: {padding: 10}
}];
treeConfigs.each(function() {
    treePanelItems.push(new NetworkNavTree(this));
    return true;
});

Ext.getCmp('master_panel').add({items: treePanelItems});

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
            header: _t('Address / Netmask'),
            width: 50,
            renderer: function(name, row, record) {
                return record.data.netmask ? name + '/' + record.data.netmask :
                                             name;
            }
        }, {
            id: 'device',
            dataIndex: 'device',
            header: _t('Device'),
            width: 200,
            renderer: function(device, row, record) {
                if (!device) return _t('No Device');
                return Zenoss.render.link(device.uid, null, device.name);
            }
        }, {
            id: 'interface',
            dataIndex: 'interface',
            header: _t('Interface'),
            width: 200,
            renderer: function(iface, row, record){
                if (!iface) return _t('No Interface');
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
        bufferSize: 256,
        proxy: new Ext.data.DirectProxy({
            directFn: Zenoss.remote.NetworkRouter.getIpAddresses
        }),
        reader: new Ext.ux.grid.livegrid.JsonReader({
            root: 'data',
            idProperty: 'uid',
            totalProperty: 'totalCount',
            fields: [
                {name: 'name'},
                {name: 'netmask'},
                {name: 'device'},
                {name: 'interface'},
                {name: 'pingstatus'},
                {name: 'snmpstatus'},
                {name: 'uid'}
            ]
        })
    };


var ipAddressGridConfig = {
        xtype: 'instancecardpanel',
        ref: 'detailCardPanel',
        region: 'center',
        border: false,
        collapsed: false,
        split: true,
        autoExpandColumn: 'name',
        stripeRows: true,
        router: Zenoss.remote.NetworkRouter,
        instancesTitle: _t('IP Addresses'),
        cm: new Ext.grid.ColumnModel(ipAddressColumnConfig),
        store: new Ext.ux.grid.livegrid.Store(ipAddressStoreConfig),
        sm: new Ext.ux.grid.livegrid.RowSelectionModel({
            singleSelect: true,
            listeners: {
                rowselect: function(selModel, rowIndex, record) {
                    var token = Ext.History.getToken();
                    if ( ! token ) {
                        token = getRootId(function(config) {
                            return config.id + ':' + config.root.id;
                        });
                    }
                    var tokenParts = token.split('.ipaddresses.');
                    if ( tokenParts[1] !== record.data.name ) {
                        Ext.History.add( tokenParts[0] + '.ipaddresses.' + record.data.name);
                    }
                }
            }
        })
    };

Ext.getCmp('detail_panel').add(ipAddressGridConfig);

(function(){
    // Remove extraneous toolbar items since we don't hide this panel
    var detailCardPanel = Ext.getCmp('detail_panel').detailCardPanel;
    Ext.each(detailCardPanel.getTopToolbar().items.items.slice(2), function(item) {
        detailCardPanel.getTopToolbar().remove(item);
    });
    // Set the toolbar's height since we removed the large icon
    detailCardPanel.getTopToolbar().setHeight(29);

    detailCardPanel.getTopToolbar().add( {
            xtype: 'tbspacer',
            width: 5
        }, {
            ref: '../descriptionField',
            xtype: 'tbtext'
        },
        '->',
        {
            ref: '../ipcountField',
            xtype: 'tbtext'
    });

    var oldSetContext = detailCardPanel.setContext;

    detailCardPanel.setContext = function(contextUid) {
        Zenoss.remote.NetworkRouter.getInfo( {
            uid: contextUid,
            keys: ['id', 'description', 'ipcount']
            },
            function(infoData) {
                detailCardPanel.descriptionField.setText(
                    infoData.success ? infoData.data.description : '');
                detailCardPanel.ipcountField.setText(
                    infoData.success ? 'IPs Used/Free: ' + infoData.data.ipcount : '');
                detailCardPanel.doLayout();
            }
        );

        return oldSetContext.call(this, contextUid);
    }
})();


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

// Edit description dialog
var showEditDescriptionDialog = function() {
    var dialog = new Zenoss.SmartFormDialog({
        title: _t('Edit Description'),
        formId: 'editDescriptionDialog',
        items: [{
            xtype: 'textfield',
            id: 'description',
            fieldLabel: _t('Description'),
            allowBlank: true
            }],
        formApi: {
            load: Zenoss.remote.NetworkRouter.getInfo
        }
    });

    dialog.setSubmitHandler(function(values) {
        values.uid = Zenoss.env.PARENT_CONTEXT;
        Zenoss.remote.NetworkRouter.setInfo(values);
        Ext.getCmp('detail_panel').detailCardPanel.setContext(values.uid);
    });

    dialog.getForm().load({
        params: { uid: Zenoss.env.PARENT_CONTEXT, keys: ['id', 'description'] },
        success: function(form, action) {
            dialog.show();
        },
        failure: function(form, action) {
            Ext.Msg.alert('Error', action.result.msg);
        }
    });
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
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD') ||
                    treeConfigs.containsKey(Zenoss.env.PARENT_CONTEXT),
                handler: discoverDevicesDialog.show.createDelegate(discoverDevicesDialog)
            },{
                tooltip: _t('Edit network description'),
                text: _t('Edit description'),
                ref: 'buttonEditDescription',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD') ||
                    treeConfigs.containsKey(Zenoss.env.PARENT_CONTEXT),
                handler: showEditDescriptionDialog
            }];
        }
    }
});

});

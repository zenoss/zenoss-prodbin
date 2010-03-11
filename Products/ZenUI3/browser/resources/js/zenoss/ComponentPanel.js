/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

(function(){

var ZC = Ext.ns('Zenoss.component');

Zenoss.nav.register({
    Component: [{
        nodeType: 'subselect',
        id: 'Overview',
        text: _t('Overview'),
        action: function(node, target) {
            var uid = node.parentNode.id;
            if (!(uid in target.items.keys)) {
                Zenoss.form.getGeneratedForm(uid, function(config){
                    target.add(Ext.apply({id:uid}, config));
                    target.layout.setActiveItem(uid);
                });
            } else {
                target.layout.setActiveItem(uid);
            }
        }
    }]
});

ZC.TypeSelection = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            cls: 'x-tree-noicon',
            loader: {
                directFn: config.directFn || Zenoss.remote.DeviceRouter.getComponentTree,
                baseAttrs: {
                    uiProvider: Zenoss.HierarchyTreeNodeUI
                },
                listeners: {
                    load: function(){
                        this.getRootNode().firstChild.select();
                    },
                    scope: this
                }
            },
            rootVisible: false,
            root: {
                nodeType: 'node'
            }
        });
        ZC.TypeSelection.superclass.constructor.call(this, config);
        this.relayEvents(this.getSelectionModel(), ['selectionchange']);
    },
    setContext: function(uid) {
        this.setRootNode({
            nodeType: 'async',
            text: _t('Component Types'),
            expanded: true,
            leaf: false,
            id: uid
        });
    }
});

ZC.Browser = Ext.extend(Zenoss.VerticalBrowsePanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            items: [
                new ZC.TypeSelection({
                    ref: 'typeSelect',
                    directFn: config.directFn,
                    style: 'overflow-y: scroll',
                    border: false,
                    bodyStyle: 'border-right: 1px solid gray'
                    //uid: config.uid
                }),
                new ZC.ComponentGridPanel({
                    ref: 'compSelect',
                    componentType: 'NotAComponentType',
                    fields: ['name', 'uid'],
                    bodyStyle: 'border-right: 1px solid gray',
                    columns: [{
                        id: 'name',
                        dataIndex: 'name',
                        header: _t('Name')
                    }]
                }),{
                    xtype: 'treepanel',
                    ref: 'compNav',
                    border: false,
                    style: 'overflow-y: scroll',
                    selModel: new Ext.tree.DefaultSelectionModel({
                        listeners: {
                            selectionchange: function(sm, node){
                                var target = Ext.getCmp('component_detail_panel');
                                node.attributes.action(node, target);
                            }
                        }
                    }),
                    rootVisible: false,
                    root: {
                        nodeType: 'node'
                    },
                    setContext: function(uid, type) {
                        type = type || Zenoss.types.type(uid);
                        this.setRootNode({
                            id: uid,
                            nodeType: 'async',
                            children: Zenoss.nav[type] || Zenoss.nav.Component
                        });
                        try { // Catch this so it doesn't break ongoing loads
                            this.getRootNode().firstChild.select();
                        } catch(e) { }
                    },
                    clearContext: function() {
                        this.setRootNode({
                            nodeType: 'node'
                        });
                    }
                }
            ]
        });
        ZC.Browser.superclass.constructor.call(this, config);
        this.typeSelect.on('selectionchange', this.onTypeSelect, this);
        this.compSelect.on('selectionchange', this.onComponentSelect, this);

        this.typeSelect.setContext(config.uid);
    },
    onTypeSelect: function(sm, to, from) {
        this.compNav.clearContext();
        var meta_type = to.attributes.text.text;
        this.compSelect.setType(meta_type);
    },
    onComponentSelect: function(sm, to, from) {
        this.compNav.clearContext();
        var row = sm.selections.items[0];
        if (row) {
            this.compNav.setContext(row.data.uid);
        }
    }
});


ZC.ComponentGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            border: false,
            autoExpandColumn: 'name',
            stripeRows: true,
            store: new ZC.BaseComponentStore({
                fields:config.fields, 
                directFn:config.directFn || Zenoss.remote.DeviceRouter.getComponents
            }),
            colModel: new ZC.BaseComponentColModel({
                columns:config.columns
            }),
            selModel: new Ext.ux.grid.livegrid.RowSelectionModel({
                singleSelect: true
            }),
            view: new Ext.ux.grid.livegrid.GridView({
                rowHeight: 10,
                listeners: {
                    beforeload: this.onBeforeLoad,
                    beforebuffer: this.onBeforeBuffer,
                    scope: this
                }
            })
        });
        ZC.ComponentGridPanel.superclass.constructor.call(this, config);
        this.relayEvents(this.getSelectionModel(), ['selectionchange']);
    },
    onBeforeLoad: function(store, options) {
        this.applyOptions(options);
    },
    onBeforeBuffer: function(view, store, rowIndex, visibleRows,
                             totalCount, options) {
        this.applyOptions(options);
    },
    applyOptions: function(options){
        Ext.apply(options.params, {
            uid: this.contextUid,
            keys: Ext.pluck(this.getColumnModel().config, 'dataIndex'),
            meta_type: this.componentType
        });
    },
    setType: function(type) {
        this.componentType = type;
        this.getStore().on('load', function(){
            this.getSelectionModel().selectRow(0);
        }, this, {single:true});
        this.view.updateLiveRows(this.view.rowIndex, true, true, false);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.getStore().on('load', function(){
            this.getSelectionModel().selectRow(0);
        }, this, {single:true});
        this.view.updateLiveRows(this.view.rowIndex, true, true, false);
    }
});

ZC.BaseComponentStore = Ext.extend(Ext.ux.grid.livegrid.Store, {
    constructor: function(config) {
        var fields = config.fields || [
            {name: 'name'},
            {name: 'monitored'},
            {name: 'status'}
        ];
        Ext.applyIf(config, {
            bufferSize: 50,
            proxy: new Ext.data.DirectProxy({
                directFn: config.directFn
            }),
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'data',
                fields: fields
            })
        });
        ZC.BaseComponentStore.superclass.constructor.call(this, config);
    }
});

ZC.BaseComponentColModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config) {
        var cols = config.columns || [{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            }, {
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                width: 70,
                sortable: true
            }, {
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                width: 50
            }];
        config = Ext.applyIf(config||{}, {
            defaults: {
                menuDisabled: true
            },
            columns: cols
        });
        ZC.BaseComponentColModel.superclass.constructor.call(this, config);
    }
});

ZC.IpInterfacePanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpInterface',
            fields: [
                {name: 'name'},
                {name: 'ipAddress'},//, mapping:'ipAddress.uid'},
                {name: 'network'},//, mapping:'network.uid'},
                {name: 'macaddress'},
                {name: 'status'},
                {name: 'monitored'},
                {name: 'locking'}
            ],
            columns: [{
                id: 'name',
                dataIndex: 'name',
                header: _t('IP Interface')
            },{
                id: 'ipAddress',
                dataIndex: 'ipAddress',
                header: _t('IP Address'),
                renderer: function(ip) {
                    // ip is the marshalled Info object
                    if (ip) {
                        return Zenoss.render.link(ip.uid);
                    }
                }
            },{
                id: 'network',
                dataIndex: 'network',
                header: _t('Network'),
                renderer: function(network){
                    // network is the marshalled Info object
                    if (network) {
                        return Zenoss.render.link(network.uid, null, network.name);
                    }
                }
            },{
                id: 'macaddress',
                dataIndex: 'macaddress',
                header: _t('MAC Address'),
                width: 120
            },{
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                width: 50
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpInterfacePanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('IpInterfacePanel', ZC.IpInterfacePanel);


})();

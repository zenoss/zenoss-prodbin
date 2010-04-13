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

var ZEvActions = Zenoss.events.EventPanelToolbarActions;

Zenoss.nav.register({
    Component: [{
        nodeType: 'subselect',
        id: 'Events',
        text: _t('Events'),
        action: function(node, target) {
            var uid = node.ownerTree.ownerCt.contextId,
                cardid = uid + '_events',
                showPanel = function() {
                    target.layout.setActiveItem(cardid);
                    target.layout.activeItem.setContext(uid);
                };
            if (!(cardid in target.items.keys)) {
                var panel = target.add({
                    id: cardid,
                    xtype: 'SimpleEventGridPanel',
                    stateful: false,
                    columns: Zenoss.env.COLUMN_DEFINITIONS,
                    tbar: {
                        cls: 'largetoolbar consolebar',
                        height: 32,
                        items: [{
                            xtype: 'tbfill'
                        }, ZEvActions.acknowledge,
                           ZEvActions.close,
                           ZEvActions.newwindow
                        ]
                    }
                });
            }
            showPanel();
        }
    },{
        nodeType: 'subselect',
        id: 'Edit',
        text: _t('Edit'),
        action: function(node, target) {
            var uid = node.ownerTree.ownerCt.contextId;
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

ZC.ComponentDetailNav = Ext.extend(Zenoss.DetailNavPanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            autoHeight: true,
            autoScroll: true,
            containerScroll: true,
            border: false,
            menuIds: []
        });
        ZC.ComponentDetailNav.superclass.constructor.call(this, config);
        this.relayEvents(this.getSelectionModel(), ['selectionchange']);
        this.on('selectionchange', this.onSelectionChange);
    },
    onGetNavConfig: function(contextId) {
        return Zenoss.nav.Component;
    },
    filterNav: function(navpanel, config){
        //nav items to be excluded
        var excluded = [
            'status',
            'events',
            'resetcommunity',
            'pushconfig',
            'objtemplates',
            'modeldevice',
            'historyevents'
        ];
        return (excluded.indexOf(config.id)==-1);
    },
    onSelectionChange: function(sm, node) {
        var target = this.target || Ext.getCmp('component_detail_panel'),
            action = node.attributes.action || function(node, target) {
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
        action(node, target);
    }
});
Ext.reg('componentnav', ZC.ComponentDetailNav);


ZC.ComponentPanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            border: false,
            defaults: {border: false},
            layout: 'border',
            items: [{
                region: 'north',
                height: 150,
                layout: 'border',
                defaults: {border: false},
                split: true,
                items: [{
                    ref: '../componentnav',
                    xtype: 'componentnav',
                    region: 'east',
                    width: 150,
                    split: true
                },{
                    ref: '../gridcontainer',
                    tbar: config.gridtbar,
                    layout: 'fit',
                    region: 'center',
                    split: true
                }]
            },{
                xtype: 'contextcardpanel',
                region: 'center',
                ref: 'detailcontainer',
                split: true
            }]
        });
        ZC.ComponentPanel.superclass.constructor.call(this, config);
        this.componentnav.target = this.detailcontainer;
    },
    setContext: function(uid, type) {
        this.contextUid = uid;
        if (type!=this.componentType) {
            this.componentType = type;
            var compType = this.componentType + 'Panel',
                xtype = Ext.ComponentMgr.isRegistered(compType) ? compType : 'ComponentGridPanel';
            this.gridcontainer.removeAll();
            this.gridcontainer.add({
                xtype: xtype,
                componentType: this.componentType,
                ref: '../../componentgrid',
                listeners: {
                    render: function(grid) {
                        grid.setContext(uid);
                    },
                    selectionchange: function(sm) {
                        var row = sm.getSelected();
                        if (row) {
                            this.componentnav.setContext(row.data.uid);
                        }
                    },
                    scope: this
                }
            });
            this.gridcontainer.doLayout();
        } else {
            this.componentgrid.setContext(uid);
        }
    }
});
Ext.reg('componentpanel', ZC.ComponentPanel);


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
    setContext: function(uid) {
        this.contextUid = uid;
        this.getStore().on('load', function(){
            this.getSelectionModel().selectRow(0);
        }, this, {single:true});
        this.view.updateLiveRows(this.view.rowIndex, true, true, false);
    }
});

Ext.reg('ComponentGridPanel', ZC.ComponentGridPanel);

ZC.BaseComponentStore = Ext.extend(Ext.ux.grid.livegrid.Store, {
    constructor: function(config) {
        var fields = config.fields || [
            {name: 'uid'},
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
                {name: 'uid'},
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

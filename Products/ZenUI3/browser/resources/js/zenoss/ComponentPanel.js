/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

(function(){

var ZC = Ext.ns('Zenoss.component'),
    ZEvActions = Zenoss.events.EventPanelToolbarActions,
    NM = ZC.nameMap = {};

ZC.registerName = function(meta_type, name, plural) {
    NM[meta_type] = [name, plural];
}

ZC.displayName = function(meta_type) {
    return NM[meta_type] || [meta_type, meta_type];
}

function componentColumnDefinitions() {
    var defs = Zenoss.env.COLUMN_DEFINITIONS,
        bad = ['component', 'device'];
    return  Zenoss.util.filter(defs, function(d){
        return bad.indexOf(d.id)==-1;
    });
}

function render_link(ob) {
    if (ob && ob.uid) {
        return Zenoss.render.link(ob.uid);
    } else {
        return ob;
    }
}

Zenoss.nav.register({
    Component: [{
        nodeType: 'subselect',
        id: 'Graphs',
        text: _t('Graphs'),
        action: function(node, target, combo) {
            var uid = combo.contextUid,
                cardid = uid+'_graphs',
                graphs = {
                    id: cardid,
                    xtype: 'graphpanel',
                    viewName: 'graphs',
                    showToolbar: false,
                    text: _t('Graphs')
                };
            if (!(cardid in target.items.keys)) {
                target.add(graphs);
            }
            target.layout.setActiveItem(cardid);
            target.layout.activeItem.setContext(uid);
            var tbar = target.getTopToolbar();
            if (tbar._btns) {
                Ext.each(tbar._btns, tbar.remove, tbar);
            }
            var btns = tbar.add([
                '->',
                {
                    xtype: 'tbtext',
                    text: _t('Range:')
                }, {
                    xtype: 'drangeselector',
                    listeners: {
                        select: function(combo, record, index){
                            var value = record.data.id,
                                panel = Ext.getCmp(cardid);
                            panel.drange = value;
                            panel.resetSwoopies();

                        }
                    }
                },'-', {
                    xtype: 'button',
                    ref: '../resetBtn',
                    text: _t('Reset'),
                    handler: function(btn) {
                        Ext.getCmp(cardid).resetSwoopies();
                    }
                },'-',{
                    xtype: 'tbtext',
                    text: _t('Link Graphs?:')
                },{
                    xtype: 'checkbox',
                    ref: '../linkGraphs',
                    checked: true,
                    listeners: {
                        check: function(chkBx, checked) {
                            var panel = Ext.getCmp(cardid);
                            panel.setLinked(checked);
                        }
                    }
                }, '-', {
                    xtype: 'graphrefreshbutton',
                    stateId: 'graphRefresh',
                    iconCls: 'refresh',
                    text: _t('Refresh'),
                    handler: function(btn) {
                        if (cardid && Ext.getCmp(cardid)) {
                            Ext.getCmp(cardid).resetSwoopies();
                        }
                    }
                }
            ]);
            tbar.doLayout();
            tbar._btns = btns;
            combo.on('select', function(c, selected){
                if (selected.id!="Graphs") {
                    Ext.each(btns, tbar.remove, tbar);
                }
            }, this, {single:true});
        }
    },{
        nodeType: 'subselect',
        id: 'Events',
        text: _t('Events'),
        action: function(node, target, combo) {
            var uid = combo.contextUid,
                cardid = uid + '_events',
                showPanel = function() {
                    target.layout.setActiveItem(cardid);
                    target.layout.activeItem.setContext(uid);
                };
            if (!(cardid in target.items.keys)) {
                var panel = target.add({
                    id: cardid,
                    xtype: 'SimpleEventGridPanel',
                    displayFilters: false,
                    stateId: 'component-event-console',
                    columns: componentColumnDefinitions()
                });
                var tbar = target.getTopToolbar();
                if (tbar._btns) {
                    Ext.each(tbar._btns, tbar.remove, tbar);
                }
                var btns = tbar.add([
                    '-',
                    ZEvActions.acknowledge,
                    ZEvActions.close,
                    ZEvActions.refresh,
                    '-',
                    ZEvActions.newwindow
                ]);
                Ext.each(btns, function(b){b.grid = panel;});
                tbar.doLayout();
                tbar._btns = btns;
                combo.on('select', function(c, selected){
                    if (selected.id!="Events") {
                        Ext.each(btns, tbar.remove, tbar);
                    }
                }, this, {single:true});
            }
            showPanel();
        }
    },{
        nodeType: 'subselect',
        id: 'Edit',
        text: _t('Details'),
        action: function(node, target, combo) {
            var uid = combo.contextUid;
            if (!(uid in target.items.keys)) {
                Zenoss.form.getGeneratedForm(uid, function(config){
                    target.add(Ext.apply({id:uid}, config));
                    target.layout.setActiveItem(uid);
                });
            } else {
                target.layout.setActiveItem(uid);
            }
        }
    },{
        nodeType: 'subselect',
        id: 'ComponentTemplate',
        text: _t('Templates'),
        action: function(node, target, combo) {
            var uid = combo.contextUid;
            target.add(Ext.create({
                xtype: 'componenttemplatepanel',
                ref: 'componentTemplatePanel',
                id: 'componentTemplatePanel' + uid
            }));
            target.componentTemplatePanel.setContext(uid);
            target.layout.setActiveItem('componentTemplatePanel' + uid);
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
        var grid = this.ownerCt.ownerCt.ownerCt.componentgrid,
            items = [],
            monitor = false;
        Zenoss.env.GRID = grid;
        Ext.each(grid.store.data.items, function(record){
            if (record.data.monitor) { monitor = true; }
        });
        Zenoss.util.each(Zenoss.nav.get('Component'), function(item){
            if (!(item.id=='Graphs' && !monitor)) {
                items.push(item);
            }
        });
        return items;
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
        var tbar = config.gridtbar,
            tbarid = Ext.id();
        if (tbar) {
            if (Ext.isArray(tbar)) {
                tbar = {items:tbar};
            }
            Ext.apply(tbar, {
                id: tbarid
            });
        }
        config = Ext.applyIf(config||{}, {
            tbarid: tbarid,
            border: false,
            defaults: {border: false},
            layout: 'border',
            items: [{
                region: 'north',
                height: 250,
                defaults: {border: false},
                border: false,
                split: true,
                ref: 'gridcontainer',
                tbar: tbar,
                layout: 'fit'
            },{
                xtype: 'contextcardpanel',
                region: 'center',
                ref: 'detailcontainer',
                split: true,
                defaults: {
                    border: false
                },
                tbar: {
                    cls: 'largetoolbar componenttbar',
                    border: false,
                    height: 32,
                    items: [{
                        xtype: 'tbtext',
                        html: _t("Display: ")
                    },{
                        xtype: 'detailnavcombo',
                        menuIds: [],
                        onGetNavConfig: function(uid) {
                            var grid = this.componentgrid,
                                items = [],
                                monitor = false;
                            Ext.each(grid.store.data.items, function(record){
                                if (record.data.uid==uid && record.data.monitor) {
                                    monitor = true;
                                }
                            });
                            Zenoss.util.each(Zenoss.nav.get('Component'), function(item){
                                items.push(item);
                            });
                            return items;
                        }.createDelegate(this),
                        filterNav: function(cfg) {
                            var excluded = [
                                'status',
                                'events',
                                'resetcommunity',
                                'pushconfig',
                                'objtemplates',
                                'template',
                                'modeldevice',
                                'historyevents'
                            ];
                            return (excluded.indexOf(cfg.id)==-1);
                        },
                        ref: '../../componentnav',
                        getTarget: function() {
                            return this.detailcontainer;
                        }.createDelegate(this)
                    }]
                }
            }]
        });
        ZC.ComponentPanel.superclass.constructor.call(this, config);
        this.addEvents('contextchange');
    },
    getGridToolbar: function(){
        return Ext.getCmp(this.tbarid);
    },
    selectByToken: function(token) {
        var grid = this.componentgrid,
            store = grid.getStore(),
            sm = grid.getSelectionModel(),
            view = grid.getView();
        if (token) {
            store.findByUid(token, function(record, index) {
                if (!sm.isSelected(index)) {
                    if (index<=this.store.bufferRange[1]) {
                        sm.selectRow(index);
                    } else {
                        view.on('buffer', function(){
                            sm.selectRow(index);
                        }, this.store, {single:true});
                    }
                    view.ensureVisible(index);
                }
            }, grid);
        }
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
                ref: '../componentgrid',
                listeners: {
                    render: function(grid) {
                        grid.setContext(uid);
                    },
                    rangeselect: function(sm) {
                        this.detailcontainer.removeAll();
                        this.componentnav.reset();
                    },
                    selectionchange: function(sm, node) {
                        var row = sm.getSelected();
                        if (row) {
                            Zenoss.env.compUUID = row.data.uuid;
                            this.componentnav.setContext(row.data.uid);
                            var delimiter = Ext.History.DELIMITER,
                                token = Ext.History.getToken().split(delimiter, 2).join(delimiter);
                            Ext.History.add(token + delimiter + row.data.uid);
                            Ext.getCmp('component_monitor_menu_item').setDisabled(!row.data.usesMonitorAttribute);
                        } else {
                            this.detailcontainer.removeAll();
                            this.componentnav.reset();
                        }
                    },
                    scope: this
                }
            });
            this.gridcontainer.doLayout();
        } else {
            this.componentgrid.setContext(uid);
        }
        this.fireEvent('contextchange', this, uid, type);
    }
});
Ext.reg('componentpanel', ZC.ComponentPanel);


ZC.ComponentGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    lastHash: null,
    constructor: function(config) {
        config = config || {};
        config.fields = config.fields || [];
        config.fields.push({'name': 'uuid'});
        config = Ext.applyIf(config||{}, {
            border: false,
            autoExpandColumn: 'name',
            stripeRows: true,
            store: new ZC.BaseComponentStore({
                sortInfo: config.sortInfo,
                fields:config.fields,
                directFn:config.directFn || Zenoss.remote.DeviceRouter.getComponents
            }),
            colModel: new ZC.BaseComponentColModel({
                columns:config.columns
            }),
            selModel: new Zenoss.ExtraHooksSelectionModel({
                suppressDeselectOnSelect: true
            }),
            view: new Ext.ux.grid.livegrid.GridView({
                rowHeight: 22,
                nearLimit: 100,
                loadMask: {msg: _t('Loading. Please wait...'),
                           msgCls: 'x-mask-loading'},
                listeners: {
                    beforeload: this.onBeforeLoad,
                    beforebuffer: this.onBeforeBuffer,
                    scope: this
                }
            })
        });

        ZC.ComponentGridPanel.superclass.constructor.call(this, config);
        this.relayEvents(this.getSelectionModel(), ['selectionchange']);
        this.relayEvents(this.getSelectionModel(), ['rangeselect']);
        this.store.proxy.on('load',
            function(proxy, o, options) {
                this.lastHash = o.result.hash || this.lastHash;
            },
            this);
        Zenoss.util.addLoadingMaskToGrid(this);
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
            keys: Ext.pluck(this.getStore().fields.getRange(), 'name'),
            meta_type: this.componentType,
            name: this.componentName
        });
    },
    refresh: function() {
        this.setContext(this.contextUid);
    },
    filter: function(name) {
        if (this.componentName!=name) {
            this.componentName = name;
            this.view.updateLiveRows(0, true, true, false);
        }
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.getStore().on('load', function(){
            var token = Ext.History.getToken();
            if (token.split(Ext.History.DELIMITER).length!=3) {
                this.getSelectionModel().selectRow(0);
            }
        }, this, {single:true});
        this.view.updateLiveRows(0, true, true, false);
    }
});

Ext.reg('ComponentGridPanel', ZC.ComponentGridPanel);

ZC.BaseComponentStore = Ext.extend(Ext.ux.grid.livegrid.Store, {
    constructor: function(config) {
        var fields = config.fields || [
            {name: 'uid'},
            {name: 'severity'},
            {name: 'name'},
            {name: 'usesMonitorAttribute'},
            {name: 'monitor'},
            {name: 'monitored'},
            {name: 'status'}
        ];
        Ext.applyIf(config, {
            bufferSize: 300,
            proxy: new Ext.data.DirectProxy({
                directFn: config.directFn
            }),
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'data',
                totalProperty: 'totalCount',
                fields: fields
            })
        });
        ZC.BaseComponentStore.superclass.constructor.call(this, config);
        this.on('load', function(){this.loaded = true;}, this);
    },
    findByUid: function(uid, callback, scope) {
        var doit = function() {
            var i = 0, found = false;
            this.each(function(r){
                if (r.data.uid==uid) {
                    callback.call(scope||this, r, i);
                    found = true;
                    return false;
                }
                i++;
                return true;
            });
            if (!found) {
                var o = {componentUid:uid};
                Ext.apply(o, this.lastOptions.params);
                Zenoss.remote.DeviceRouter.findComponentIndex(o, function(r){
                    callback.call(scope||this, null, r.index);
                });
            }
        }.createDelegate(this);
        if (!this.loaded) {
            this.on('load', doit, this);
        } else {
            doit();
        }
    }
});

ZC.BaseComponentColModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config) {
        var cols = config.columns || [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            }, {
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 70,
                sortable: true
            }, {
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                renderer: Zenoss.render.pingStatus,
                width: 60
            }];
        config = Ext.applyIf(config||{}, {
            defaults: {
                menuDisabled: true,
                sortable: true
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
            autoExpandColumn: 'description',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'status'},
                {name: 'name'},
                {name: 'description'},
                {name: 'ipAddressObjs'},
                {name: 'network'},//, mapping:'network.uid'},
                {name: 'macaddress'},
                {name: 'usesMonitorAttribute'},
                {name: 'ifStatus'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'duplex'},
                {name: 'netmask'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 50
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('IP Interface'),
                width: 150
            },{
                id: 'ipAddresses',
                dataIndex: 'ipAddressObjs',
                header: _t('IP Addresses'),
                renderer: function(ipaddresses) {
                    var returnString = '';
                    Ext.each(ipaddresses, function(ipaddress, index) {
                        if (index > 0) returnString += ', ';
                        if (ipaddress && Ext.isObject(ipaddress) && ipaddress.netmask) {
                            var name = ipaddress.name + '/' + ipaddress.netmask;
                            returnString += Zenoss.render.link(ipaddress.uid, undefined, name);
                        }
                        else if (Ext.isString(ipaddress)) {
                            returnString += ipaddress;
                        }
                    });
                    return returnString;
                }
            },{
                id: 'description',
                dataIndex: 'description',
                header: _t('Description')
            },{
                id: 'macaddress',
                dataIndex: 'macaddress',
                header: _t('MAC Address'),
                width: 120
            },{
                id: 'ifStatus',
                dataIndex: 'ifStatus',
                header: _t('Status'),
                renderer: Zenoss.render.ipInterfaceStatus,
                width: 80
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                width: 72,
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpInterfacePanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('IpInterfacePanel', ZC.IpInterfacePanel);
ZC.registerName('IpInterface', _t('Interface'), _t('Interfaces'));

ZC.WinServicePanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'WinService',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'status'},
                {name: 'name'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'caption'},
                {name: 'startMode'},
                {name: 'startName'},
                {name: 'serviceClassUid'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Service Name'),
                renderer: Zenoss.render.WinServiceClass
            },{
                id: 'caption',
                dataIndex: 'caption',
                header: _t('Caption')
            },{
                id: 'startMode',
                dataIndex: 'startMode',
                header: _t('Start Mode')
            },{
                id: 'startName',
                dataIndex: 'startName',
                header: _t('Start Name')
            },{
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                renderer: Zenoss.render.pingStatus,
                width: 60
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.WinServicePanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('WinServicePanel', ZC.WinServicePanel);
ZC.registerName('WinService', _t('Windows Service'), _t('Windows Services'));


ZC.IpRouteEntryPanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpRouteEntry',
            autoExpandColumn: 'destination',
            fields: [
                {name: 'uid'},
                {name: 'destination'},
                {name: 'nextHop'},
                {name: 'id'}, // needed for nextHop link
                {name: 'device'}, // needed for nextHop link
                {name: 'interface'},
                {name: 'protocol'},
                {name: 'type'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'destination',
                dataIndex: 'destination',
                header: _t('Destination'),
                renderer: render_link
            },{
                id: 'nextHop',
                dataIndex: 'nextHop',
                header: _t('Next Hop'),
                renderer: Zenoss.render.nextHop,
                width: 250
            },{
                id: 'interface',
                dataIndex: 'interface',
                header: _t('Interface'),
                renderer: render_link
            },{
                id: 'protocol',
                dataIndex: 'protocol',
                header: _t('Protocol')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type'),
                width: 50
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpRouteEntryPanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('IpRouteEntryPanel', ZC.IpRouteEntryPanel);
ZC.registerName('IpRouteEntry', _t('Network Route'), _t('Network Routes'));

ZC.IpServicePanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpService',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'status'},
                {name: 'severity'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'protocol'},
                {name: 'description'},
                {name: 'ipaddresses'},
                {name: 'port'},
                {name: 'serviceClassUid'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                renderer: Zenoss.render.IpServiceClass
            },{
                id: 'protocol',
                dataIndex: 'protocol',
                header: _t('Protocol')
            },{
                id: 'port',
                dataIndex: 'port',
                header: _t('Port')
            },{
                id: 'ipaddresses',
                dataIndex: 'ipaddresses',
                header: _t('IPs'),
                renderer: function(ips) {
                    return ips.join(', ');
                }
            },{
                id: 'description',
                dataIndex: 'description',
                header: _t('Description')
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpServicePanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('IpServicePanel', ZC.IpServicePanel);
ZC.registerName('IpService', _t('IP Service'), _t('IP Services'));


ZC.OSProcessPanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'OSProcess',
            autoExpandColumn: 'processName',
            fields: [
                {name: 'uid'},
                {name: 'processName'},
                {name: 'status'},
                {name: 'severity'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'processClass'},
                {name: 'alertOnRestart'},
                {name: 'failSeverity'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'processClass',
                dataIndex: 'processClass',
                header: _t('Process Class'),
                renderer: function(cls) {
                    if (cls && cls.uid) {
                        return Zenoss.render.link(cls.uid);
                    } else {
                        return cls;
                    }
                }
            },{
                id: 'processName',
                dataIndex: 'processName',
                header: _t('Name')
            },{
                id: 'alertOnRestart',
                dataIndex: 'alertOnRestart',
                renderer: Zenoss.render.checkbox,
                width: 85,
                header: _t('Restart Alert?')
            },{
                id: 'failSeverity',
                dataIndex: 'failSeverity',
                renderer: Zenoss.render.severity,
                width: 70,
                header: _t('Fail Severity')
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                width: 55,
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.OSProcessPanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('OSProcessPanel', ZC.OSProcessPanel);
ZC.registerName('OSProcess', _t('OS Process'), _t('OS Processes'));


ZC.FileSystemPanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            autoExpandColumn: 'mount',
            componentType: 'FileSystem',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'status'},
                {name: 'severity'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'mount'},
                {name: 'totalBytes'},
                {name: 'availableBytes'},
                {name: 'usedBytes'},
                {name: 'capacityBytes'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'mount',
                dataIndex: 'mount',
                header: _t('Mount Point')
            },{
                id: 'totalBytes',
                dataIndex: 'totalBytes',
                header: _t('Total Bytes'),
                renderer: Zenoss.render.bytesString
            },{
                id: 'usedBytes',
                dataIndex: 'usedBytes',
                header: _t('Used Bytes'),
                renderer: Zenoss.render.bytesString
            },{
                id: 'availableBytes',
                dataIndex: 'availableBytes',
                header: _t('Free Bytes'),
                renderer: function(n){
                    if (n<0) {
                        return _t('Unknown');
                    } else {
                        return Zenoss.render.bytesString(n);
                    }

                }
            },{
                id: 'capacityBytes',
                dataIndex: 'capacityBytes',
                header: _t('% Util'),
                renderer: function(n) {
                    if (n=='unknown' || n<0) {
                        return _t('Unknown');
                    } else {
                        return n + '%';
                    }
                }

            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.FileSystemPanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('FileSystemPanel', ZC.FileSystemPanel);
ZC.registerName('FileSystem', _t('File System'), _t('File Systems'));


ZC.CPUPanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'CPU',
            autoExpandColumn: 'product',
            fields: [
                {name: 'uid'},
                {name: 'socket'},
                {name: 'manufacturer'},
                {name: 'product'},
                {name: 'clockspeed'},
                {name: 'extspeed'},
                {name: 'cacheSizeL1'},
                {name: 'cacheSizeL2'},
                {name: 'voltage'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'socket',
                dataIndex: 'socket',
                header: _t('Socket'),
                width: 45
            },{
                id: 'manufacturer',
                dataIndex: 'manufacturer',
                header: _t('Manufacturer'),
                renderer: render_link
            },{
                id: 'product',
                dataIndex: 'product',
                header: _t('Model'),
                renderer: render_link
            },{
                id: 'clockspeed',
                dataIndex: 'clockspeed',
                header: _t('Speed'),
                width: 70,
                renderer: function(x){ return x + ' MHz';}
            },{
                id: 'extspeed',
                dataIndex: 'extspeed',
                header: _t('Ext Speed'),
                width: 70,
                renderer: function(x){ return x + ' MHz';}
            },{
                id: 'cacheSizeL1',
                dataIndex: 'cacheSizeL1',
                header: _t('L1'),
                width: 70,
                renderer: function(x){ return x + ' KB';}
            },{
                id: 'cacheSizeL2',
                dataIndex: 'cacheSizeL2',
                header: _t('L2'),
                width: 70,
                renderer: function(x){ return x + ' KB';}
            },{
                id: 'voltage',
                dataIndex: 'voltage',
                header: _t('Voltage'),
                width: 70,
                renderer: function(x){ return x + ' mV';}
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.CPUPanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('CPUPanel', ZC.CPUPanel);
ZC.registerName('CPU', _t('Processor'), _t('Processors'));


ZC.ExpansionCardPanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'ExpansionCard',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'slot'},
                {name: 'name'},
                {name: 'serialNumber'},
                {name: 'manufacturer'},
                {name: 'product'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'slot',
                dataIndex: 'slot',
                header: _t('Slot'),
                width: 80
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'serialNumber',
                dataIndex: 'serialNumber',
                header: _t('Serial Number'),
                width: 110
            },{
                id: 'manufacturer',
                dataIndex: 'manufacturer',
                header: _t('Manufacturer'),
                renderer: render_link,
                width: 110
            },{
                id: 'product',
                dataIndex: 'product',
                header: _t('Model'),
                renderer: render_link,
                width: 130
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.ExpansionCardPanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('ExpansionCardPanel', ZC.ExpansionCardPanel);
ZC.registerName('ExpansionCard', _t('Card'), _t('Cards'));


ZC.PowerSupplyPanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'PowerSupply',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'watts'},
                {name: 'type'},
                {name: 'state'},
                {name: 'millivolts'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'watts',
                dataIndex: 'watts',
                header: _t('Watts')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'millivolts',
                dataIndex: 'millivolts',
                header: _t('Millivolts')
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.PowerSupplyPanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('PowerSupplyPanel', ZC.PowerSupplyPanel);
ZC.registerName('PowerSupply', _t('Power Supply'), _t('Power Supplies'));


ZC.TemperatureSensorPanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'TemperatureSensor',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'state'},
                {name: 'temperature'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'temperature',
                dataIndex: 'temperature',
                header: _t('Temperature'),
                renderer: function(x) {
                    if (x == null) {
                        return "";
                    } else {
                        return x + " F";
                    }
                }
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.TemperatureSensorPanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('TemperatureSensorPanel', ZC.TemperatureSensorPanel);
ZC.registerName('TemperatureSensor', _t('Temperature Sensor'), _t('Temperature Sensors'));


ZC.FanPanel = Ext.extend(ZC.ComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'Fan',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'state'},
                {name: 'type'},
                {name: 'rpm'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type')
            },{
                id: 'rpm',
                dataIndex: 'rpm',
                header: _t('RPM')
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.FanPanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('FanPanel', ZC.FanPanel);
ZC.registerName('Fan', _t('Fan'), _t('Fans'));

})();

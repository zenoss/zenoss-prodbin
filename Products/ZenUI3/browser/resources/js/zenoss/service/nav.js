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
Ext.onReady( function() {

    var zs = Ext.ns('Zenoss.Service.Nav');

    /**********************************************************************
     *
     * Navigation Functionality
     *
     */

    // implements SelectionModel:rowselect event
    zs.navSelectHandler = function(sm, rowIndex, dataRecord) {
        var uid = dataRecord.data.uid;
        Ext.getCmp('serviceForm').setContext(uid);
        Ext.getCmp('serviceInstancePanel').setContext(uid);
    };

    zs.loadHandler = function(me, records, options) {
        var grid = Ext.getCmp('navGrid');
        grid.getSelectionModel().selectFirstRow();
        grid.fireEvent('rowclick', grid, 0);
    };

    zs.nonZeroRenderer = function(v) { return (v > 0 ? v : ''); };

    zs.storeConfig = {
        proxy: new Ext.data.DirectProxy({
            directFn:Zenoss.remote.ServiceRouter.query
            }),
        autoLoad: false,
        bufferSize: 100,
        defaultSort: {field:'name', direction:'ASC'},
        sortInfo: {field:'name', direction:'ASC'},
        reader: new Ext.ux.grid.livegrid.JsonReader({
            root: 'services',
            totalProperty: 'totalCount'
            }, [
                {name:'name', type:'string'},
                {name:'description', type:'string'},
                {name:'port', type:'string'},
                {name:'count', type:'string'},
                {name:'uid', type:'string'}
               ]) // reader
    };

    zs.columnModelConfig = {
        defaults: {
            sortable: false,
            menuDisabled: true
        },
        columns: [
            {
                dataIndex: 'name',
                header: _t('Name'),
                id: 'name'
            },
            {
                dataIndex: 'count',
                header: _t('Count'),
                id: 'count',
                width: 40,
                renderer: zs.nonZeroRenderer,
                filter: false
            }
        ]
    };

    zs.gridConfig = {
        id: 'navGrid',
        stateId: 'servicesNavGridState',
        enableDragDrop: false,
        stateful: true,
        border: false,
        autoExpandColumn: 'name',
        rowSelectorDepth: 5,
        view: new Zenoss.FilterGridView({
            nearLimit: 20,
            loadMask: {msg: 'Loading. Please wait...'},
            listeners: {
                beforeBuffer:
                    function(view, ds, idx, len, total, opts) {
                        opts.params.uid = view._context;
                    }
            }
        })
    };

    zs.initNav = function(initialContext) {
        var columnModel, store, config;

        store = new Ext.ux.grid.livegrid.Store(zs.storeConfig);
        columnModel = new Ext.grid.ColumnModel(zs.columnModelConfig);

        store.on('load', zs.loadHandler, store, { single: true });

        config = Ext.apply(zs.gridConfig, {
            store: store,
            cm: columnModel,
            sm: new Zenoss.ExtraHooksSelectionModel({singleSelect:true})
        });

        var navGrid = new Zenoss.FilterGridPanel(config);

        navGrid.on('afterrender',
            function(me){
                me.setContext(initialContext);
                me.showFilters();
            });

        navGrid.getSelectionModel().on('rowselect', zs.navSelectHandler);
        Ext.getCmp('master_panel').add(navGrid);
    };
});
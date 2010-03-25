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
    * Grid Navigation Functionality
    *
    */

    zs.nonZeroRenderer = function(v) { return (v > 0 ? v : ''); };

    // implements SelectionModel:rowselect event
    zs.gridSelectHandler = function(sm, rowIndex, dataRecord) {
        var uid = dataRecord.data.uid;
        Ext.getCmp('serviceForm').setContext(uid);
        Ext.getCmp('serviceInstancePanel').setContext(uid);
        Ext.getCmp('deleteButton').setDisabled(false);
    };

//    zs.storeLoadHandler = function(me, records, options) {
//        var grid = Ext.getCmp('navGrid');
//        grid.getSelectionModel().selectFirstRow();
//        grid.fireEvent('rowclick', grid, 0);
//    };

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
                dataIndex : 'name',
                header : _t('Name'),
                id : 'name'
            }, {
                dataIndex : 'count',
                header : _t('Count'),
                id : 'count',
                width : 40,
                renderer : zs.nonZeroRenderer,
                filter : false
            }
        ]
    };

    zs.gridConfig = {
        id: 'navGrid',
        flex: 3,
        stateId: 'servicesNavGridState',
        enableDragDrop: false,
        stateful: true,
        border: false,
        autoExpandColumn: 'name',
        rowSelectorDepth: 5,
        view: new Zenoss.FilterGridView({
            nearLimit: 20,
            loadMask: {msg: _t('Loading. Please wait...')},
            listeners: {
                beforeBuffer: function(view, ds, idx, len, total, opts) {
                    opts.params.uid = view._context;
                }
            }
        })
    };
});
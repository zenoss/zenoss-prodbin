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

    var zs = Ext.ns('Zenoss.Service.Nav');

    /**********************************************************************
    *
    * Grid Navigation Functionality
    *
    */

    zs.nonZeroRenderer = function(v) { return (v > 0 ? v : ''); };

    // handles the SelectionModel's rowselect event
    zs.rowselectHandler = function(sm, rowIndex, dataRecord) {
        var selectedOrganizer = Ext.getCmp('navTree').getSelectionModel().getSelectedNode();
        if ( selectedOrganizer ) {
            // unselect the organizer, but leave it highlighted
            selectedOrganizer.unselect();
            selectedOrganizer.getUI().addClass('x-tree-selected');
        }
        Ext.getCmp('serviceForm').setContext(dataRecord.data.uid);
        Ext.getCmp('serviceInstancePanel').setContext(dataRecord.data.uid);
        Ext.getCmp('footer_bar').buttonDelete.setDisabled(false);
    };

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
            sortable: true,
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
                width : 50,
                renderer : zs.nonZeroRenderer,
                filter : false
            }
        ]
    };

    zs.gridConfig = {
        id: 'navGrid',
        flex: 3,
        stateId: 'servicesNavGridState',
        enableDrag: true,
        ddGroup: 'serviceDragDrop',
        stateful: true,
        border: false,
        autoExpandColumn: 'name',
        rowSelectorDepth: 5,
        loadMask: true,
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

})();

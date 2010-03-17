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

    zs.addServiceClassDialogSubmit = function(values)
    {
        var grid = Ext.getCmp('navGrid'),
            view = grid.getView(),
            store = grid.getStore(),
            params = {
                type:'class',
                contextUid: view.contextUid,
                id: values.idTextfield,
                posQuery: view.getFilterParams()
        };

        function callback(p, response){
            var result = response.result;
            if (result.success) {
                var newRowPos = result['newIndex'];
                store.on('load', function(){
                    view.focusRow(newRowPos);
                    grid.getSelectionModel().selectRow(newRowPos);},
                    store, { single: true });
                view.updateLiveRows(newRowPos, true, true, false);
            } else {
                Ext.Msg.alert('Error', result.msg);
            }
        }

        Zenoss.remote.ServiceRouter.addNode(params, callback);
    };

    zs.deleteServiceClassDialogSubmit = function(values)
    {
        var grid = Ext.getCmp('navGrid'),
            view = grid.getView(),
            store = grid.getStore(),
            selected = grid.getSelectionModel().getSelected();

        if (selected) {
            var params = {
                uid: selected.data.uid
            };

            function callback(p, response){
                var result = response.result;
                if (result.success) {
                    var newRowPos = view.rowIndex;
                    store.on('load', function(){
                        view.focusRow(newRowPos);
                        grid.getSelectionModel().selectRow(newRowPos);},
                        store, { single: true });
                    view.updateLiveRows(newRowPos, true, true, false);
                } else {
                    Ext.Msg.alert('Error', result.msg);
                }
            }
            Zenoss.remote.ServiceRouter.deleteNode(params, callback);
        } else {
            Ext.Msg.alert('Error', 'Must select an item in the list.');
        }
    };

    zs.addClassDialog = new Zenoss.SmartFormDialog({
        id: 'addServiceClassDialog',
        title: _t('Add Service Class'),
        items: {
            xtype: 'textfield',
            id: 'idTextfield',
            fieldLabel: _t('ID'),
            allowBlank: false
        },
        saveHandler: zs.addServiceClassDialogSubmit
    });

    zs.deleteClassDialog = new Zenoss.MessageDialog({
        id: 'deleteServiceClassDialog',
        title: _t('Delete Service Class'),
        message: _t('The selected Service Class will be deleted.'),
        okHandler: zs.deleteServiceClassDialogSubmit
    });

    zs.addServiceClassButtonHandler = function() {
        zs.addClassDialog.show();
    };

    zs.deleteServiceClassButtonHandler = function() {
        zs.deleteClassDialog.show();
    };

    zs.gridFooterBar = {
        xtype: 'toolbar',
        id: 'footer_bar',
        border: false,
        items: [
            {
                id: 'addButton',
                iconCls: 'add',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                tooltip: 'Add a child to the selected organizer',
                handler: zs.addServiceClassButtonHandler
            }, {
                id: 'deleteButton',
                iconCls: 'delete',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                tooltip: 'Delete the selected node',
                handler: zs.deleteServiceClassButtonHandler
            }
        ]
    };

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

        Ext.getCmp('footer_panel').add(new Ext.Toolbar(zs.gridFooterBar));

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
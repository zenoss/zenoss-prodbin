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
    * Common Functions
    *
    */

    zs.addDialogSubmit = function(values)
    {
        var type = values.typeCombo;

        if (type=='Class') {
            var grid = Ext.getCmp('navGrid'),
                view = grid.getView(),
                store = grid.getStore(),
                params;

            view.clearFilters();
            params = {
                type: type,
                contextUid: view.contextUid,
                id: values.idTextfield,
                posQuery: view.getFilterParams()
            };

            var callback = function(p, response) {
                var result = response.result;
                if (result.success) {
                    var newRowPos = result['newIndex'];
                    store.on('load', function(){
                        view.focusRow(newRowPos);
                        grid.getSelectionModel().selectRow(newRowPos);
                    },
                        store, { single: true });
                    view.updateLiveRows(newRowPos, true, true, false);
                } else {
                    Ext.Msg.alert(_t('Error'), result.msg);
                }
            }
            Zenoss.remote.ServiceRouter.addNode(params, callback);
        }
        else {
            var tree = Ext.getCmp('navTree');
            tree.addNode(type, values.idTextfield);
        }
    };

    zs.deleteDialogSubmit = function() {
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
            var tree = Ext.getCmp('navTree'),
                node = tree.getSelectionModel().getSelectedNode();

            if (node)
            {
                tree.deleteSelectedNode();
            }
            else {
                Ext.Msg.alert('Error', 'Must select an item in the list.');
            }
        }
    };

    zs.addDialog = new Zenoss.SmartFormDialog({
        id: 'addDialog',
        title: _t('Add Node'),
        items: [{ xtype: 'combo',
            id: 'typeCombo',
            fieldLabel: _t('Type'),
            displayField: 'type',
            mode: 'local',
            triggerAction: 'all',
            emptyText: _t('Select a type...'),
            forceSelection: true,
            editable: false,
            allowBlank: false,
            store: new Ext.data.ArrayStore({
                fields: ['type'],
                data: [['Organizer'], ['Class']]
            })
        }, {
            xtype: 'textfield',
            id: 'idTextfield',
            fieldLabel: _t('ID'),
            allowBlank: false
        }],
        saveHandler: zs.addDialogSubmit
    });

    zs.getSelectedUid = function()
    {
        var selected = Ext.getCmp('navGrid').getSelectionModel().getSelected();
        if (selected) {
            return selected.data.uid;
        }

        selected = Ext.getCmp('navTree').getSelectionModel().getSelectedNode();
        if (selected) {
            return selected.attributes.uid;
        }
    }

    zs.addButtonHandler = function() {
        var uid,
            selected = Ext.getCmp('navTree').getSelectionModel().getSelectedNode();

        if (selected) {
            zs.addDialog.setText('Adding new node to ' + selected.attributes.uid);
            zs.addDialog.show();
        }
        else {
            Ext.MessageBox.alert('Error', 'You must select a node before adding.');
        }
    };

    zs.deleteButtonHandler = function() {
        var uid = zs.getSelectedUid();
        if (uid) {
            Ext.MessageBox.show({
                title: 'Delete Node',
                msg: 'The selected node will be deleted:\n' + uid,
                fn: function(buttonid){
                    if (buttonid=='ok') {
                        zs.deleteDialogSubmit();
                    }
                },
                buttons: Ext.MessageBox.OKCANCEL,
                multiline: true
            });
        }
        else {
            Ext.MessageBox.alert('Error', 'You must select a node to delete.');
        }
    };

    zs.footerBarItems = [
        {
            id: 'addButton',
            iconCls: 'add',
            disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
            tooltip: _t('Add a child to the selected organizer'),
            handler: zs.addButtonHandler
        }, {
            id: 'deleteButton',
            iconCls: 'delete',
            disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
            tooltip: _t('Delete the selected node'),
            handler: zs.deleteButtonHandler
        }
    ];


    /**********************************************************************
    *
    * Navigation Initializer
    *
    */

    zs.initNav = function(initialContext) {
        var columnModel, store, gridConfig, treeConfig;

        store = new Ext.ux.grid.livegrid.Store(zs.storeConfig);
        columnModel = new Ext.grid.ColumnModel(zs.columnModelConfig);

//        store.on('load', zs.storeLoadHandler, store, { single: true });

        gridConfig = Ext.apply(zs.gridConfig, {
            store: store,
            cm: columnModel,
            sm: new Zenoss.ExtraHooksSelectionModel({singleSelect:true})
        });

        var navGrid = new Zenoss.FilterGridPanel(gridConfig);

        navGrid.on('afterrender',
            function(me){
//                me.setContext(initialContext);
                me.showFilters();
            });

        navGrid.getSelectionModel().on('rowselect', zs.gridSelectHandler);

        treeConfig = Ext.applyIf(zs.treeConfig, {
            root: {
                id: initialContext.split('/').pop(),
                uid: initialContext
            }
        });

        var navTree = new Zenoss.HierarchyTreePanel(treeConfig);

        p = new Ext.Panel({layout: {type:'vbox', align: 'stretch'}});
        p.add(navTree);
        p.add(navGrid);

        Ext.getCmp('master_panel').add(p);
        Ext.getCmp('footer_bar').add(zs.footerBarItems);
    };
});
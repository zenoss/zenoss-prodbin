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
    * Common Functions
    *
    */

    zs.addClassHandler = function(newId)
    {
        var grid = Ext.getCmp('navGrid'),
            view = grid.getView(),
            store = grid.getStore(),
            params;

        view.clearFilters();
        params = {
            type: 'class',
            contextUid: view.contextUid,
            id: newId,
            posQuery: view.getFilterParams()
        };

        var callback = function(p, response) {
            var result = response.result;
            if (result.success) {
                var newRowPos = result['newIndex'];
                store.on('load', function(){
                    view.focusRow(newRowPos);
                    grid.getSelectionModel().selectRow(newRowPos);
                }, store, { single: true });
                view.updateLiveRows(newRowPos, true, true, false);
            } else {
                Ext.Msg.alert(_t('Error'), result.msg);
            }
        }
        Zenoss.remote.ServiceRouter.addNode(params, callback);
    };

    zs.addOrganizerHandler = function(newId) {
        var tree = Ext.getCmp('navTree');
        tree.addNode('organizer', newId);
    };

    zs.deleteHandler = function() {
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
                    grid.getSelectionModel().clearSelections();
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

    zs.deleteOrganizerHandler = function() {
        var tree, selected, params;
        tree = Ext.getCmp('navTree');
        selected = tree.getSelectionModel().getSelectedNode();
        params = {uid: selected.attributes.uid};
        function callback(){
            tree.getRootNode().reload(function() {
                tree.getRootNode().select();
                tree.getRootNode().expand(true);
            });
        }
        Zenoss.remote.ServiceRouter.deleteNode(params, callback);
    };

    zs.dispatcher = function(actionName, value) {
        switch (actionName) {
            case 'addClass': zs.addClassHandler(value); break;
            case 'addOrganizer': zs.addOrganizerHandler(value); break;
            case 'delete': zs.deleteHandler(); break;
            case 'deleteOrganizer': zs.deleteOrganizerHandler(); break;
        }
    };

    zs.getSelectedUid = function() {
        var selected = Ext.getCmp('navGrid').getSelectionModel().getSelected();
        if (selected) {
            return selected.data.uid;
        }

        selected = Ext.getCmp('navTree').getSelectionModel().getSelectedNode();
        if (selected) {
            return selected.attributes.uid;
        }
    };

    /**********************************************************************
    *
    * Navigation Initializer
    *
    */

    zs.initNav = function(initialContext) {
        var columnModel, store, gridConfig, fb, navTree, navGrid, p;

        store = new Ext.ux.grid.livegrid.Store(zs.storeConfig);
        columnModel = new Ext.grid.ColumnModel(zs.columnModelConfig);

        gridConfig = Ext.apply(zs.gridConfig, {
            store: store,
            cm: columnModel,
            sm: new Zenoss.ExtraHooksSelectionModel({singleSelect:true})
        });

        navGrid = new Zenoss.FilterGridPanel(gridConfig);

        navGrid.on('afterrender',
            function(me){
                me.showFilters();
            });

        navGrid.getSelectionModel().on('rowselect', zs.gridSelectHandler);


        navTree = Ext.create({
            xtype: 'servicetreepanel',
            root: {
                id: initialContext.split('/').pop(),
                uid: initialContext
            }
        });

        p = new Ext.Panel({layout: {type:'vbox', align: 'stretch'}});
        p.add(navTree);
        p.add(navGrid);

        Ext.getCmp('master_panel').add(p);

        fb = Ext.getCmp('footer_bar');
        fb.on('buttonClick', zs.dispatcher);
        Zenoss.footerHelper('Service', fb, {deleteMenu: true});
    };
})();

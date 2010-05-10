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
            contextUid: view.contextUid,
            id: newId,
            posQuery: view.getFilterParams()
        };

        var callback = function(p, response) {
            var result, loadHandler;
            result = response.result;
            loadHandler = function() {
                view.focusRow(result.newIndex);
                grid.getSelectionModel().selectRow(result.newIndex);
            };
            store.on('load', loadHandler, store, {single: true});
            view.updateLiveRows(result.newIndex, true, true, false);
        };
        Zenoss.remote.ServiceRouter.addClass(params, callback);
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
                    Zenoss.flares.Manager.error(result.msg);
                }
            }
            Zenoss.remote.ServiceRouter.deleteNode(params, callback);
        } else {
            Zenoss.flares.Manager.error(_t('Must select an item in the list.'));
        }
    };

    zs.deleteOrganizerHandler = function() {
        var selected, params;
        selected = zs.getSelectedOrganizer();
        if ( ! selected ) {
            Zenoss.flares.Manager.error(_t('No service organizer is selected.'));
            return;
        }
        params = {uid: selected.attributes.uid};
        function callback(){
            var tree = Ext.getCmp('navTree');
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
            default: break;
        }
    };

    var ContextGetter = Ext.extend(Object, {
        getUid: function() {
            var selected = Ext.getCmp('navGrid').getSelectionModel().getSelected();
            if ( ! selected ) {
                Zenoss.flares.Manager.error(_t('You must select a service.'));
                return null;
            }
            return selected.data.uid;
        },
        hasTwoControls: function() {
            return true;
        },
        getOrganizerUid: function() {
            var selected = zs.getSelectedOrganizer();
            if ( ! selected ) {
                Zenoss.flares.Manager.error(_t('You must select a service organizer.'));
                return null;
            }
            return selected.attributes.uid;
        }
    });

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

        navGrid.getSelectionModel().on('rowselect', zs.rowselectHandler);


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
        var footerHelperOptions = {
            contextGetter: new ContextGetter()
        };
        Zenoss.footerHelper('Service', fb, footerHelperOptions);
    };
})();

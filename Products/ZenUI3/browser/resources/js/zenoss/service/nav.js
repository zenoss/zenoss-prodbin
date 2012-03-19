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

        grid.filterRow.clearFilters();
        params = {
            contextUid: grid.getContext(),
            id: newId,
            posQuery: grid.getFilters()
        };

        var callback = function(p, response) {
            var result, loadHandler;
            result = response.result;
            loadHandler = function() {
                view.focusRow(result.newIndex);
                grid.getSelectionModel().selectRange(result.newIndex, result.newIndex);
            };
            store.on('load', loadHandler, store, {single: true});
            grid.refresh();
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
                        grid.getSelectionModel().selectRange(newRowPos, newRowPos);},
                        store, { single: true });
                    grid.refresh();
                } else {
                    Zenoss.message.error(result.msg);
                }
            }
            Zenoss.remote.ServiceRouter.deleteNode(params, callback);
        } else {
            Zenoss.message.error(_t('Must select an item in the list.'));
        }
    };

    zs.deleteOrganizerHandler = function() {
        var selected, params;
        selected = zs.getSelectedOrganizer();
        if ( ! selected ) {
            Zenoss.message.error(_t('No service organizer is selected.'));
            return;
        }
        params = {uid: selected.data.uid};
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
                Zenoss.message.error(_t('You must select a service.'));
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
                Zenoss.message.error(_t('You must select a service organizer.'));
                return null;
            }
            return selected.data.uid;
        }
    });

    /**********************************************************************
    *
    * Navigation Initializer
    *
    */

    zs.initNav = function(initialContext) {
        var store, gridConfig, fb, navTree, navGrid, p;

        store = Ext.create('Zenoss.Service.Nav.Store',{});

        navGrid = Ext.create('Zenoss.Service.Nav.GridPanel', {
            store: store,
            selModel: new Zenoss.ExtraHooksSelectionModel({
                singleSelect: true,
                listeners: {
                    select: zs.rowselectHandler
                }
            })
        });

        navTree = Ext.create('Zenoss.Service.Nav.ServiceTreePanel', {
            root: {
                id: initialContext.split('/').pop(),
                uid: initialContext
            }
        });

        p = new Ext.Panel({layout: {type:'vbox', align: 'stretch'}});
        p.add(navTree);
        p.add(navGrid);

        Ext.getCmp('center_panel').add(
            new Ext.Panel({
                layout: 'border',
                defaults: {'border':false},
                items: [{
                    id: 'master_panel',
                    region: 'west',
                    layout: 'fit',
                    width: 250,
                    maxWidth: 250,
                    split: true,
                    items: [p]
                },{
                    id: 'detail_panel',
                    region: 'center',
                    layout: 'border',
                    defaults: {'border':false},
                    items: [
                        Zenoss.Service.DetailForm.formConfig, {
                            xtype: 'instancecardpanel',
                            ref: 'detailCardPanel',
                            id: 'detailCardPanel',
                            region: 'south',
                            split: true,
                            height: 300,
                            collapsed: true,
                            listeners: {
                                afterrender: function(panel){
                                    panel.collapse();
                                }
                            },
                            router: Zenoss.remote.ServiceRouter,
                            instancesTitle: 'Service Instances',
                            bufferSize: 100,
                            nearLimit: 20,
                            zPropertyEditListeners: {
                                frameload: function() {
                                    var formPanel = Ext.getCmp('serviceForm');
                                    if (formPanel.contextUid) {
                                        formPanel.setContext(formPanel.contextUid);
                                    }
                                }
                            }
                    }]
                }]
            }
        ));
        Ext.getCmp('center_panel').doLayout();
        // expand the card panel so it can render the toolbar
        Ext.getCmp('detailCardPanel').expand();
        fb = Ext.getCmp('footer_bar');
        fb.on('buttonClick', zs.dispatcher);
        var footerHelperOptions = {
            contextGetter: new ContextGetter(),
            customAddDialog: {
                formListeners: {
                    clientvalidation: function(form, valid) {
                        form.refOwner.buttonSubmit.setDisabled(!valid);
                    }
                }
            },
            onGetAddDialogItems: function () {
                return [{
                    xtype: 'idfield',
                    name: 'id',
                    anchor: '80%',
                    fieldLabel: _t('Name'),
                    allowBlank: false
                }];
            }
        };
        Zenoss.footerHelper('Service', fb, footerHelperOptions);
    };
})();

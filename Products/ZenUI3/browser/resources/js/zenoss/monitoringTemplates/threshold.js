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

/* package level */
(function() {
    Ext.namespace('Zenoss.templates');

    /****  Variable Declaration ****/
    var thresholdSelectionModel, thresholdDeleteButton,
        router, treeId, thresholdEditButton, MinMaxThresholdDialog;
     
    Zenoss.templates.thresholdsId = 'thresholdGrid';
    thresholdDeleteButton = 'thresholdDeleteButton';
    thresholdEditButton = 'thesholdEditButton';
    router = Zenoss.remote.TemplateRouter;
     
    // The id of the tree on the left hand side of the screen
    treeId = 'templateTree';


    /**** Delete Thresholds ****/
     
    /**
     * Calls the router to delete the selected
     * threshold
     **/
    function deleteThreshold() {
        var grid, selectedRow, callback,
            opts;
        grid = Ext.getCmp(Zenoss.templates.thresholdsId);
        selectedRow = grid.getSelectionModel().getSelected();

        // delete threshold callback
        callback = function (response) {
            // only if we were successful. If there
            // was an exception we should see a dialog
            if (!response.success) {
                return;
            }

            // reload the thresholds grid
            grid.getStore().reload();

            // disable the delete button (they have to select another one to enable it)
            Ext.getCmp(thresholdDeleteButton).disable();
            Ext.getCmp(thresholdEditButton).disable();
        };
        
        // parameters for the router request
        opts = {
            'uid': selectedRow.id
        };
        
        router.removeThreshold(opts, callback);
    }

    /**
     * Configuration Options for the Delete Threshold Dialog
     **/
    function thresholdDeleteConfig(){
        // assuming there is always a selected node in the tree and the
        // threshold datagrid at this point
        var grid = Ext.getCmp(Zenoss.templates.thresholdsId),
            name = grid.getSelectionModel().getSelected().data.name,
            tree = Ext.getCmp(treeId),
            msg = String.format(_t("Are you sure you want to remove {0} from the template {1}? There is no undo."),
                name,
                tree.getSelectionModel().getSelectedNode().id.replace('./',''));
        
        return {
            title: _t('Remove Threshold'),
            modal: true,
            width: 310,
            height: 130,
            items: [{
                xtype: 'panel',
                bodyStyle: 'font-weight: bold; text-align:center',
                html: msg
            }],
            buttons: [{
                xtype: 'DialogButton',
                text: _t('Remove'),
                handler: deleteThreshold
            }, 
                Zenoss.dialog.CANCEL
            ]      
        };
    }
     
     
    /**** View/Edit Threshold ****/
     
    /**
     * Call back from the router call to save
     * the threshold (from the edit dialog),
     * just reloads the threshold dialg
     **/
    function closeThresholdDialog(response) {
        // update the datasource of the threshold
        var grid = Ext.getCmp(Zenoss.templates.thresholdsId),
            dialog = Ext.getCmp('editThresholdDialog');
        grid.getStore().reload();
        // hide the form
        if (dialog) {
            dialog.hide();
        }
    }
     
    /**
     *@returns Zenoss.FormDialog Ext Dialog type associated with the
     *          selected threshold type
     **/
    function thresholdEdit() {
        var grid = Ext.getCmp(Zenoss.templates.thresholdsId),
            record = grid.getSelectionModel().getSelected(),
            config = {};
                            
        function displayEditDialog(response) {
            var win;
            config.record = response;
            config.xtype = "EditThresholdDialog";
            config.id = "editThresholdDialog";
            config.saveHandler = closeThresholdDialog;
            win = Ext.create(config);
            win.show();
        }

        // send the request for all of the threshold's info to the server
        router.getThresholdDetails({uid: record.id}, displayEditDialog);
    }
     
     
    /**** Threshold Data Grid ****/
    
    /**
     * Threshold DataGrid Selection Model
     * Handles when a user clicks on a specific threshold.
     **/
    thresholdSelectionModel = new Ext.grid.RowSelectionModel ({
        singleSelect: true,
        listeners : {
            /**
             * If they have permission and they select a row, show the
             * edit and delete buttons
             **/
            rowselect: function (selectionModel, rowIndex, record ) {
                // enable the "Delete Threshold" button
                if (Zenoss.Security.hasPermission('Manage DMD')) {
                    Ext.getCmp(thresholdDeleteButton).enable();
                    Ext.getCmp(thresholdEditButton).enable();
                }
            },
            
            /**
             * When they deselect don't allow them to press the buttons
             **/
            rowdeselect: function(selectionModel, rowIndex, record) {
                Ext.getCmp(thresholdDeleteButton).disable();
                Ext.getCmp(thresholdEditButton).disable();
            }
        }
    });

    /**
     * Definition for the Thresholds datagrid. This is used in 
     * templates.js in the updateThresholds function.
     **/
    Zenoss.templates.thresholdDataGrid = Ext.extend(Ext.grid.GridPanel, {
        constructor: function(config) {
            config = config || {};
            Ext.apply(config, {
                id: Zenoss.templates.thresholdsId,
                selModel: thresholdSelectionModel,
                title: _t('Thresholds'),
                store: {
                    xtype: 'directstore',
                    directFn: router.getThresholds,
                    fields: ['name', 'type', 'dataPoints', 'severity', 'enabled']
                },
                tbar: [{
                    id: thresholdDeleteButton,
                    xtype: 'button',
                    iconCls: 'delete',
                    disabled: true,
                    tooltip: _t('Delete Threshold'),
                    handler: function() {
                        // when they press delete show the Confirmation
                        var win = new Zenoss.FormDialog(thresholdDeleteConfig());
                        win.show();
                    }
                                       
                }, {
                    id: thresholdEditButton,
                    xtype: 'button',
                    iconCls: 'configure',
                    disabled: true,
                    tooltip: _t('Edit Threshold'),
                    handler: thresholdEdit
                }],
                colModel: new Ext.grid.ColumnModel({
                    columns: [
                        {dataIndex: 'name', header: _t('Name'), width:400}
                    ]
                })
            });
            
            Zenoss.templates.thresholdDataGrid.superclass.constructor.apply(
                this, arguments);
        }
    });
    Ext.reg('thresholddatagrid', Zenoss.templates.thresholdDataGrid);
}());
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
    /**********************************************************************
     *
     * Variable Declarations
     *
     */
    var thresholdSelectionModel, thresholdDeleteButton, addThreshold,
        router, treeId, thresholdEditButton, MinMaxThresholdDialog, dataSourcesId, addThresholdDialog;
     
    Zenoss.templates.thresholdsId = 'thresholdGrid';
    thresholdDeleteButton = 'thresholdDeleteButton';
    thresholdEditButton = 'thresholdEditButton';
    dataSourcesId = 'dataSourceTreeGrid';
    router = Zenoss.remote.TemplateRouter;
     
    // The id of the tree on the left hand side of the screen
    treeId = 'templateTree';
     
    /**********************************************************************
     *
     * Add Threshold
     *
     */
     
    addThreshold = function(data){
        var uid, node, dataPoints, params, callback;
        uid = Ext.getCmp(treeId).getSelectionModel().getSelectedNode().attributes.uid;
        node = Ext.getCmp(dataSourcesId).getSelectionModel().getSelectedNode();
        if ( node && node.isLeaf() ) {
            dataPoints = [node.attributes.uid];
        } else {
            dataPoints = [];
        }
        params = {
            uid: uid, 
            thresholdType: data.thresholdTypeField,
            thresholdId: data.thresholdIdField,
            dataPoints: dataPoints
        };
        callback = function(provider, response) {
            Ext.getCmp(Zenoss.templates.thresholdsId).getStore().reload();
        };
        Zenoss.remote.TemplateRouter.addThreshold(params, callback);
    };
    
    addThresholdDialog = new Ext.create({
        xtype: 'window',
        id: 'addThresholdDialog',
        title: _t('Add Threshold'),
        message: _t('Allow the user to add a threshold.'),
        closeAction: 'hide',
        buttonAlign: 'left',
        autoScroll: true,
        plain: true,
        width: 375,
        autoHeight: true,
        modal: true,
        padding: 10,
        listeners:{
            show: function() {
                this.formPanel.getForm().reset();
            }
        },
        
        buttons: [{ 
            ref: '../submitButton',
            text: _t('Add'), 
            handler: function(submitButton) {
                var dialogWindow, basicForm; 
                dialogWindow = submitButton.refOwner; 
                basicForm = dialogWindow.formPanel.getForm();
                basicForm.api.submit(basicForm.getValues()); 
                dialogWindow.hide(); 
            } },
                  { 
                      ref: '../cancelButton', 
                      text: _t('Cancel'), 
                      handler: function(cancelButton) { 
                          var dialogWindow = cancelButton.refOwner; 
                          dialogWindow.hide();
                      } 
                  }],
        items: {
            xtype: 'form',
            ref: 'formPanel',
            leftAlign: 'top',
            monitorValid: true,
            border: false,
            paramsAsHash: true,
            api: { submit: addThreshold },
            listeners: {
                clientValidation: function(formPanel, valid) {
                    var dialogWindow;
                    dialogWindow = formPanel.refOwner;
                    dialogWindow.submitButton.setDisabled( !valid );
                }
            },
            items: [{
                name: 'thresholdTypeField',
                xtype: 'combo',
                fieldLabel: _t('Type'),
                displayField: 'type',
                forceSelection: true,
                triggerAction: 'all',
                emptyText: _t('Select a type...'),
                selectOnFocus: true,
                allowBlank: false,
                store: new Ext.data.DirectStore({
                    fields: ['type'],
                    root: 'data',
                    directFn: Zenoss.remote.TemplateRouter.getThresholdTypes
                })
            }, {
                name: 'thresholdIdField',
                xtype: 'idfield',
                fieldLabel: _t('Name'),
                allowBlank: false
            }
                   ]
        }});
    /**********************************************************************
     *
     * Delete Thresholds
     *
     */
     
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
     
     
     /**********************************************************************
     *
     * Edit Thresholds
     *
     */

     
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
            var win = Ext.create( {
                record: response.record,
                items: response.form,
                singleColumn: true,
                width: 650,
                xtype: 'datasourceeditdialog',
                title: _t('Edit Threshold'),
                directFn: router.setInfo,
                id: 'editThresholdDialog',
                saveHandler: closeThresholdDialog                 
            });
                        
            win.show();
        }

        // send the request for all of the threshold's info to the server
        router.getThresholdDetails({uid: record.id}, displayEditDialog);
    }
     
     
     /**********************************************************************
     *
     * Threshold Data Grid
     *
     */
    
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
            var listeners = {};
            
            listeners = Ext.apply(listeners, { rowdblclick: thresholdEdit});
            
            config = config || {};
            Ext.apply(config, {
                id: Zenoss.templates.thresholdsId,
                selModel: thresholdSelectionModel,
                title: _t('Thresholds'),
                border: false,
                store: {
                    xtype: 'directstore',
                    directFn: router.getThresholds,
                    fields: ['name', 'type', 'dataPoints', 'severity', 'enabled']
                },
                listeners: listeners,
                tbar: [{
                    xtype: 'button',
                    iconCls: 'add',
                    id: 'thresholdAddButton',
                    ref: '../addButton',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function() {
                        Ext.getCmp('addThresholdDialog').show();
                    },
                    listeners: {
                        render: function() {
                            Zenoss.registerTooltipFor('thresholdAddButton');
                        }
                    }
                },
                    {
                    id: thresholdDeleteButton,
                    xtype: 'button',
                    iconCls: 'delete',
                    disabled: true,
                    handler: function() {
                        // when they press delete show the Confirmation
                        var win = new Zenoss.FormDialog(thresholdDeleteConfig());
                        win.show();
                    },
                    listeners: {
                        render: function() {
                            Zenoss.registerTooltipFor(thresholdDeleteButton);
                        }
                    }
                                       
                }, {
                    id: thresholdEditButton,
                    xtype: 'button',
                    iconCls: 'customize',
                    disabled: true,
                    handler: thresholdEdit,
                    listeners: {
                        render: function() {
                            Zenoss.registerTooltipFor(thresholdEditButton);
                        }
                    }
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
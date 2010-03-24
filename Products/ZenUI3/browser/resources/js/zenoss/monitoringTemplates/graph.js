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

var router, addGraphDefinition, deleteGraphDefinition;

Ext.ns('Zenoss', 'Zenoss.templates');

router = Zenoss.remote.TemplateRouter;

addGraphDefinition = function(){
    var templateSelectionModel, params, callback;
    templateSelectionModel = Ext.getCmp('templateTree').getSelectionModel();
    params = {
        templateUid: templateSelectionModel.getSelectedNode().attributes.uid,
        graphDefinitionId: Ext.getCmp('graphDefinitionIdTextfield').getValue()
    };
    callback = function(provider, response) {
        Ext.getCmp('graphGrid').getStore().reload();
    };
    router.addGraphDefinition(params, callback);
};

new Zenoss.HideFormDialog({
    id: 'addGraphDefinitionDialog',
    title: _t('Add Graph Definition'),
    items: [
        {
            xtype: 'textfield',
            id: 'graphDefinitionIdTextfield',
            fieldLabel: _t('ID'),
            allowBlank: false,
            listeners: {
                invalid: function(){
                    Ext.getCmp('submit').disable();
                },
                valid: function(){
                    Ext.getCmp('submit').enable();
                }
            }
        }
    ],
    listeners: {
        hide: function() {
            Ext.getCmp('graphDefinitionIdTextfield').reset();
        }
    },
    buttons: [
    {
        xtype: 'HideDialogButton',
        id: 'submit',
        text: _t('Submit'),
        disabled: true,
        handler: function(button, event) {
            addGraphDefinition();
        }
    }, {
        xtype: 'HideDialogButton',
        text: _t('Cancel')
    }]
});

deleteGraphDefinition = function() {
    var params, callback;
    params = {
        uid: Ext.getCmp('graphGrid').getSelectionModel().getSelected().id
    };
    callback = function(provider, response) {
        Ext.getCmp('deleteGraphDefinitionButton').disable();
        Ext.getCmp('graphGrid').getStore().reload();
    };
    router.deleteGraphDefinition(params, callback);
};

new Zenoss.MessageDialog({
    id: 'deleteGraphDefinitionDialog',
    title: _t('Delete Graph Definition'),
    okHandler: function(){
        deleteGraphDefinition();
    }
});

Zenoss.templates.GraphGrid = Ext.extend(Ext.grid.GridPanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            title: _t('Graph Definitions'),
            store: {xtype: 'graphstore'},
            selModel: new Ext.grid.RowSelectionModel({
                singleSelect: true,
                listeners: {
                    rowdeselect: function() {
                        Ext.getCmp('deleteGraphDefinitionButton').disable();
                    },
                    rowselect: function() {
                        Ext.getCmp('deleteGraphDefinitionButton').enable();
                    }
                }
            }),
            colModel: new Ext.grid.ColumnModel({
                columns: [
                    {dataIndex: 'name', header: _t('Name'), width: 400}                    
                ]
            }),
            tbar: [{
                id: 'addGraphDefinitionButton',
                xtype: 'button',
                iconCls: 'add',
                tooltip: _t('Add Graph Definition'),
                handler: function() {
                    Ext.getCmp('addGraphDefinitionDialog').show();
                }
            }, {
                id: 'deleteGraphDefinitionButton',
                xtype: 'button',
                iconCls: 'delete',
                tooltip: _t('Delete Graph Definition'),
                disabled: true,
                handler: function() {
                    var msg, name, html, dialog;
                    msg = _t("Are you sure you want to remove {0}? There is no undo.");
                    name = Ext.getCmp('graphGrid').getSelectionModel().getSelected().data.name;
                    html = String.format(msg, name);
                    dialog = Ext.getCmp('deleteGraphDefinitionDialog');
                    dialog.show();
                    dialog.update(html);
                }
            }]
        });
        Zenoss.templates.GraphGrid.superclass.constructor.call(this, config);
    }
});
Ext.reg('graphgrid', Zenoss.templates.GraphGrid);

})();

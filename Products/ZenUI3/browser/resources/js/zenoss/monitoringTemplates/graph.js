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

var router, addGraphDefinition;

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

Zenoss.templates.GraphGrid = Ext.extend(Ext.grid.GridPanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            title: _t('Graph Definitions'),
            store: {xtype: 'graphstore'},
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
                                   
            }]
        });
        Zenoss.templates.GraphGrid.superclass.constructor.call(this, config);
    }
});
Ext.reg('graphgrid', Zenoss.templates.GraphGrid);

})();

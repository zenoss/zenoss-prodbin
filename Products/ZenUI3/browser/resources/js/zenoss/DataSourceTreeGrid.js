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

var addThreshold;

Ext.ns('Zenoss');

addThreshold = function(thresholdType, thresholdId){
    var uid, dataPoints, params, callback;
    uid = Ext.getCmp('templateTree').getSelectionModel().getSelectedNode().attributes.uid;
    dataPoints = [Ext.getCmp('dataSourceTreeGrid').getSelectionModel().getSelectedNode().attributes.uid];
    params = {
        uid: uid, 
        thresholdType:thresholdType, 
        thresholdId: thresholdId,
        dataPoints: dataPoints
    };
    callback = function(provider, response) {
        Ext.getCmp('thresholdGrid').getStore().reload();
    };
    Zenoss.remote.TemplateRouter.addThreshold(params, callback);
};

new Zenoss.HideFormDialog({
    id: 'addThresholdDialog',
    title: _t('Add Threshold'),
    items: [
        {
            xtype: 'combo',
            id: 'thresholdTypeCombo',
            fieldLabel: _t('Type'),
            displayField: 'type',
            forceSelection: true,
            triggerAction: 'all',
            emptyText: 'Select a type...',
            selectOnFocus: true,
            store: new Ext.data.DirectStore({
                fields: ['type'],
                root: 'data',
                directFn: Zenoss.remote.TemplateRouter.getThresholdTypes
            })
        }, {
            xtype: 'textfield',
            id: 'thresholdIdTextfield',
            fieldLabel: _t('ID'),
            allowBlank: false
        }
    ],
    listeners: {
        'hide': function(treeDialog) {
            Ext.getCmp('thresholdTypeCombo').setValue('');
            Ext.getCmp('thresholdIdTextfield').setValue('');
        }
    },
    buttons: [
        {
            xtype: 'HideDialogButton',
            text: _t('Submit'),
            handler: function(button, event) {
                var thresholdType, thresholdId;
                thresholdType = Ext.getCmp('thresholdTypeCombo').getValue();
                thresholdId = Ext.getCmp('thresholdIdTextfield').getValue();
                addThreshold(thresholdType, thresholdId);
            }
        }, {
            xtype: 'HideDialogButton',
            text: _t('Cancel')
        }
    ]
});

/**
 * @class Zenoss.DataSourceTreeGrid
 * @extends Ext.ux.tree.TreeGrid
 * @constructor
 */
Zenoss.DataSourceTreeGrid = Ext.extend(Ext.ux.tree.TreeGrid, {

    constructor: function(config) {
        Ext.applyIf(config, {
            tbar: [
                {
                    xtype: 'button',
                    iconCls: 'configure',
                    tooltip: 'Add Threshold',
                    handler: function() {
                        Ext.getCmp('addThresholdDialog').show();
                    }
                }, {
                    xtype: 'button',
                    iconCls: 'set',
                    tooltip: 'Add Metric to Graph'
                }, {
                    xtype: 'tbseparator'
                }, {
                    xtype: 'button',
                    iconCls: 'devprobs',
                    tooltip: 'Add Data Source'
                }, {
                    xtype: 'button',
                    iconCls: 'adddevice',
                    tooltip: 'Override Template'
                }
            ],
            columns: [
                {
                    id: 'name',
                    dataIndex: 'name',
                    header: 'Metrics by Datasource',
                    width: 250
                }, {
                    dataIndex: 'source',
                    header: 'Source',
                    width: 250
                }, {
                    dataIndex: 'enabled',
                    header: 'Enabled',
                    width: 40
                }, {
                    dataIndex: 'type',
                    header: 'Type',
                    width: 90
                }
            ]
        });
        Zenoss.DataSourceTreeGrid.superclass.constructor.call(this, config);
    }

});

Ext.reg('DataSourceTreeGrid', Zenoss.DataSourceTreeGrid);

})();

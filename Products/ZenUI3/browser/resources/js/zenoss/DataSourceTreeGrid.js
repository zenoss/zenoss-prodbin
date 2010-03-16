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

var router, dataSourcesId, graphsId, resetCombo, addThreshold, 
    addMetricToGraph, showAddToGraphDialog, override, overrideHtml1,
    overrideHtml2, showOverrideDialog;

Ext.ns('Zenoss');

router = Zenoss.remote.TemplateRouter;
dataSourcesId = 'dataSourceTreeGrid';
graphsId = 'graphGrid';

resetCombo = function(combo, uid) {
    combo.clearValue();
    combo.getStore().setBaseParam('uid', uid);
    delete combo.lastQuery;
    combo.doQuery(combo.allQuery, true);
};

addThreshold = function(thresholdType, thresholdId){
    var uid, node, dataPoints, params, callback;
    uid = Ext.getCmp('templateTree').getSelectionModel().getSelectedNode().attributes.uid;
    node = Ext.getCmp(dataSourcesId).getSelectionModel().getSelectedNode();
    if ( node && node.isLeaf() ) {
        dataPoints = [node.attributes.uid];
    } else {
        dataPoints = [];
    }
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
        hide: function() {
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
    }]
});

addMetricToGraph = function(dataPointUid, graphUid) {
    var params, callback;
    params = {dataPointUid: dataPointUid, graphUid: graphUid};
    callback = function(provider, response) {
        Ext.getCmp(graphsId).getStore().reload();
    };
    router.addDataPointToGraph(params, callback);
};

Zenoss.GraphStore = Ext.extend(Ext.data.DirectStore, {
    constructor: function(config) {
        Ext.applyIf(config, {
            xtype: 'directstore',
            directFn: router.getGraphs,
            idProperty: 'uid',
            fields: ['uid', 'name', 'graphPoints', 'units', 'height', 'width']
        });
        Zenoss.GraphStore.superclass.constructor.call(this, config);
    }
});
Ext.reg('graphstore', Zenoss.GraphStore);

new Zenoss.HideFormDialog({
    id: 'addToGraphDialog',
    title: _t('Add Metric to Graph'),
    items: [
    {
        xtype: 'panel',
        id: 'addToGraphMetricPanel',
        border: false
    }, {
        xtype: 'combo',
        id: 'graphCombo',
        fieldLabel: _t('Graph'),
        displayField: 'name',
        valueField: 'uid',
        forceSelection: true,
        minChars: 999, // only do an all query
        triggerAction: 'all',
        emptyText: 'Select a graph...',
        selectOnFocus: true,
        store: {xtype: 'graphstore'},
        listeners: {select: function(){
            Ext.getCmp('submit').enable();
        }}
    }],
    buttons: [
    {
        xtype: 'HideDialogButton',
        id: 'submit',
        text: _t('Submit'),
        disabled: true,
        handler: function(button, event) {
            var node, datapointUid, graphUid;
            node = Ext.getCmp(dataSourcesId).getSelectionModel().getSelectedNode();
            datapointUid = node.attributes.uid;
            graphUid = Ext.getCmp('graphCombo').getValue();
            addMetricToGraph(datapointUid, graphUid);
        }
    }, {
        xtype: 'HideDialogButton',
        text: _t('Cancel')
    }]
});

showAddToGraphDialog = function() {
    var smTemplate, templateUid, smDataSource, 
        nodeDataSource, metricName, html, combo;
    smTemplate = Ext.getCmp('templateTree').getSelectionModel();
    templateUid = smTemplate.getSelectedNode().attributes.uid;
    smDataSource = Ext.getCmp(dataSourcesId).getSelectionModel();
    nodeDataSource = smDataSource.getSelectedNode();
    if ( nodeDataSource && nodeDataSource.isLeaf() ) {
        metricName = nodeDataSource.attributes.name;
        html = '<div>Metric</div>';
        html += '<div>' + metricName + '</div><br/>';
        Ext.getCmp('addToGraphDialog').show();
        Ext.getCmp('addToGraphMetricPanel').body.update(html);
        combo = Ext.getCmp('graphCombo');
        resetCombo(combo, templateUid);
        Ext.getCmp('submit').disable();
    } else {
        Ext.Msg.alert('Error', 'You must select a datapoint.');
    }
};
     
/**********************************************************************
 *
 * Override Functionality
 *
 */
override = function() {
    var node, params, callback;
    node = Ext.getCmp('templateTree').getSelectionModel().getSelectedNode();
    params = {
        uid: node.attributes.uid,
        targetUid: Ext.getCmp('targetCombo').getValue()
    };
    callback = function() {
        Ext.getCmp('templateTree').getRootNode().reload();
    };
    router.copyTemplate(params, callback);
};

overrideHtml1 = function() {
    var html;
    html = 'Do you wish to override the selected monitoring template? This';
    html += ' will affect all devices using the monitoring template.<br/><br/>';
    return html;
};

overrideHtml2 = function() {
    var html;
    html = 'If new thresholds, graphs, are added or removed, or datasources';
    html += ' added or disabled, these will be saved to this local copy of';
    html += ' template.<br/><br/>Override lets you save this template';
    html += ' overriding the original template at the root level.';
    return html;
};

new Zenoss.HideFormDialog({
    id: 'overrideDialog',
    title: _t('Override'),
    width: 500,
    items: [
    {
        xtype: 'panel',
        border: false,
        html: overrideHtml1()
    }, {
        xtype: 'button',
        id: 'learnMore',
        border: false,
        text: _t('Learn more'),
        handler: function() {
            Ext.getCmp('learnMore').hide();
            Ext.getCmp('detailedExplanation').show();
        }
    }, {
        xtype: 'panel',
        id: 'detailedExplanation',
        border: false,
        html: overrideHtml2(),
        hidden: true
    }, {
        xtype: 'panel',
        border: false,
        html: '<br/>'
    }, {
        xtype: 'combo',
        id: 'targetCombo',
        fieldLabel: 'Target',
        quickTip: 'The selected monitoring template will be copied to the specified device class or device.',
        forceSelection: true,
        emptyText: 'Select a target...',
        minChars: 0,
        selectOnFocus: true,
        valueField: 'uid',
        displayField: 'label',
        typeAhead: true,
        width: 450,
        store: {
            xtype: 'directstore',
            directFn: router.getCopyTargets,
            fields: ['uid', 'label'],
            root: 'data'
        },
        listeners: {
            select: function(){
                Ext.getCmp('submit').enable();
            }
        }
    }],
    buttons: [
    {
        xtype: 'HideDialogButton',
        id: 'submit',
        text: _t('Submit'),
        handler: function(button, event) {
            override();
        }
    }, {
        xtype: 'HideDialogButton',
        text: _t('Cancel')
    }]
});

showOverrideDialog = function() {
    var sm, uid, combo;
    sm = Ext.getCmp('templateTree').getSelectionModel();
    uid = sm.getSelectedNode().attributes.uid;
    Ext.getCmp('overrideDialog').show();
    combo = Ext.getCmp('targetCombo');
    resetCombo(combo, uid);
    Ext.getCmp('submit').disable();
};


/**********************************************************************
 *
 * Edit DataSource/DataPoint functionality
 *
 */

/**
 * Closes the edit dialog and updates the store of the datasources. 
 * This is called after the router request to save the edit dialog
 **/
function closeEditDialog(response) {
    var dialog = Ext.getCmp('editDataSources'),
        grid = Ext.getCmp(dataSourcesId);
    
    // reload the DataSources Grid
    grid.getRootNode().reload();
    
    // hide the dialog
    if (dialog) {
        dialog.hide();
    }
}
     
/**
 * Event handler for editing a specific datasource or
 * datapoint. 
 **/
function editDataSourceOrPoint() {
    var cmp = Ext.getCmp(dataSourcesId),
        selectedNode = cmp.getSelectionModel().getSelectedNode(),
        attributes = selectedNode.attributes,
        isDataPoint = false,
        params = {
            uid: attributes.uid  
        };
    
    // find out if we are editing a datasource or a datapoint
    if (attributes.leaf) {
        isDataPoint = true;
    }

    // callback for the router request
    function displayEditDialog(response) {
        var win,
        config = {};
        config.record = response.record;
        config.items = response.form;
        config.xtype = "editdialog";
        config.id = "editDataSources";
        config.isDataPoint = isDataPoint;
        if (isDataPoint) {
            config.title = _t('Edit DataPoint');
            config.directFn = router.setInfo;
        }else{
            config.title = _t('Edit DataSource');
            config.directFn = router.setInfo;;
        }
        
        config.saveHandler = closeEditDialog;
        win = Ext.create(config);
        win.show();
    }
    
    // get the details
    if (isDataPoint) {
        router.getDataPointDetails(params, displayEditDialog);
    }else{
        router.getDataSourceDetails(params, displayEditDialog);
    }
}
/**
 * @class Zenoss.DataSourceTreeGrid
 * @extends Ext.ux.tree.TreeGrid
 * @constructor
 */
Zenoss.DataSourceTreeGrid = Ext.extend(Ext.ux.tree.TreeGrid, {

    constructor: function(config) {
        Ext.applyIf(config, {
            border: false,
            useArrows: true,
            cls: 'x-tree-noicon',
            id: dataSourcesId,
            title: _t('Data Sources'),
            loader: new Ext.ux.tree.TreeGridLoader({
                directFn: router.getDataSources
            }),
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
                    tooltip: 'Add Metric to Graph',
                    handler: showAddToGraphDialog
                }, {
                    xtype: 'tbseparator'
                }, {
                    xtype: 'button',
                    iconCls: 'devprobs',
                    tooltip: 'Add Data Source'
                },{
                    xtype: 'button',
                    iconCls: 'edit',
                    tooltip: 'Edit Data Source',
                    disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: editDataSourceOrPoint
                },{
                    xtype: 'button',
                    iconCls: 'adddevice',
                    tooltip: 'Override Template',
                    handler: showOverrideDialog
                }
            ],
            columns: [
                {
                    id: 'name',
                    dataIndex: 'name',
                    header: 'Metrics by Data Source',
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

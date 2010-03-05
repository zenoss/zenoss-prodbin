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

var router, dataSourcesId, graphsId, addThreshold, addMetricToGraph;

Ext.ns('Zenoss');

router = Zenoss.remote.TemplateRouter;
dataSourcesId = 'dataSourceTreeGrid';
graphsId = 'graphGrid';

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
                    handler: function() {
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
                            combo.clearValue();
                            combo.getStore().setBaseParam('uid', templateUid);
                            delete combo.lastQuery;
                            combo.doQuery(combo.allQuery, true);
                            Ext.getCmp('submit').disable();
                        } else {
                            Ext.Msg.alert('Error', 'You must select a datapoint.');
                        }
                    }
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
    },
    
    initComponent: function() {
        Ext.ux.tree.TreeGrid.prototype.initComponent.call(this);
        this.loader.createNode = function(attr) {
            attr.expanded = true;
            return Ext.ux.tree.TreeGridLoader.prototype.createNode.call(this, attr);
        };
    }

});

Ext.reg('DataSourceTreeGrid', Zenoss.DataSourceTreeGrid);

})();

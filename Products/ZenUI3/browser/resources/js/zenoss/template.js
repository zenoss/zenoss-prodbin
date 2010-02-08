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

Ext.onReady(function(){

var router, treeId, dataSourcesId, thresholdsId, graphsId,
    beforeselectHandler, updateDataSources, updateThresholds, updateGraphs,
    selectionchangeHandler, selModel, footerPanel;

router = Zenoss.remote.TemplateRouter;
treeId = 'templateTree';
dataSourcesId = 'dataSourceTreeGrid';
thresholdsId = 'thresholdGrid';
graphsId = 'graphGrid';

beforeselectHandler = function(sm, node, oldNode) {
    return node.isLeaf();
};

updateDataSources = function(uid) {
    var panel, root;
    panel = Ext.getCmp('center_detail_panel');
    if ( ! Ext.getCmp(dataSourcesId) ) {
        panel.add({
            xtype: 'DataSourceTreeGrid',
            id: dataSourcesId,
            title: _t('Data Sources'),
            loader: new Ext.ux.tree.TreeGridLoader({
                directFn: router.getDataSources
            })
        });
        root = Ext.getCmp(dataSourcesId).getRootNode();
        root.setId(uid);
        panel.doLayout();
    } else {
        root = Ext.getCmp(dataSourcesId).getRootNode();
        root.setId(uid);
        root.reload();
    }
};

updateThresholds = function(uid) {
    var panel, root;
    panel = Ext.getCmp('top_detail_panel');
    if ( ! Ext.getCmp(thresholdsId) ) {
        panel.add({
            xtype: 'grid',
            id: thresholdsId,
            title: _t('Thresholds'),
            store: {
                xtype: 'directstore',
                directFn: router.getThresholds,
                fields: ['name', 'type', 'dataPoints', 'severity', 'enabled']
            },
            colModel: new Ext.grid.ColumnModel({
                columns: [
                    {dataIndex: 'name', header: _t('Name')},
                    {dataIndex: 'type', header: _t('Type')},
                    {dataIndex: 'dataPoints', header: _t('Data Points')},
                    {dataIndex: 'severity', header: _t('Severity')},
                    {dataIndex: 'enabled', header: _t('Enabled')}
                ]
            })
        });
        panel.doLayout();
    }
    Ext.getCmp(thresholdsId).getStore().load({
        params: {uid: uid}
    });
};

updateGraphs = function(uid) {
    var panel, root;
    panel = Ext.getCmp('bottom_detail_panel');
    if ( ! Ext.getCmp(graphsId) ) {
        panel.add({
            xtype: 'grid',
            id: graphsId,
            title: _t('Graph Definitions'),
            store: {
                xtype: 'directstore',
                directFn: router.getGraphs,
                fields: ['name', 'graphPoints', 'units', 'height', 'width']
            },
            colModel: new Ext.grid.ColumnModel({
                columns: [
                    {dataIndex: 'name', header: _t('Name')},
                    {dataIndex: 'graphPoints', header: _t('Graph Points')},
                    {dataIndex: 'units', header: _t('Units')},
                    {dataIndex: 'height', header: _t('Height')},
                    {dataIndex: 'width', header: _t('Width')}
                ]
            })
        });
        panel.doLayout();
    }
    Ext.getCmp(graphsId).getStore().load({
        params: {uid: uid}
    });
};

selectionchangeHandler = function(sm, node) {
    updateDataSources(node.attributes.uid);
    updateThresholds(node.attributes.uid);
    updateGraphs(node.attributes.uid);
};

selModel = new Ext.tree.DefaultSelectionModel({
    listeners: {
        beforeselect: beforeselectHandler,
        selectionchange: selectionchangeHandler
    }
});

Ext.getCmp('master_panel').add({
    xtype: 'TemplateTreePanel',
    id: treeId,
    title: _t('Monitoring Templates'),
    rootVisible: false,
    loader: {
        directFn: router.getTemplates,
        baseAttrs: {
            singleClickExpand: true
        }
    },
    selModel: selModel,
    root: {
        nodeType: 'async',
        id: 'root'
    }
});

footerPanel = Ext.getCmp('footer_panel');
footerPanel.removeAll();
footerPanel.add({
    xtype: 'TreeFooterBar',
    id: 'footer_bar',
    bubbleTargetId: treeId
});

}); // Ext.onReady

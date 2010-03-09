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
thresholdsId = Zenoss.templates.thresholdsId;
graphsId = 'graphGrid';

beforeselectHandler = function(sm, node, oldNode) {
    return node.isLeaf();
};
                
updateDataSources = function(uid) {
    var panel, treeGrid, root;
    if ( ! Ext.getCmp(dataSourcesId) ) {
        panel = Ext.getCmp('center_detail_panel');
        panel.add({
            xtype: 'DataSourceTreeGrid'
        });
        treeGrid = Ext.getCmp(dataSourcesId);
        root = treeGrid.getRootNode();
        root.setId(uid);
        panel.doLayout();
    } else {
        root = Ext.getCmp(dataSourcesId).getRootNode();
        root.setId(uid);
        root.reload();
    }
};

updateThresholds = function(uid) {
    var panel, root, grid;
    panel = Ext.getCmp('top_detail_panel');
    
    if ( ! Ext.getCmp(thresholdsId) ) {
        panel.add({id: thresholdsId, xtype:'thresholddatagrid'});
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
            xtype: 'graphgrid',
            id: graphsId
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
    selModel: selModel
});

footerPanel = Ext.getCmp('footer_panel');
footerPanel.removeAll();
footerPanel.add({
    xtype: 'TreeFooterBar',
    id: 'footer_bar',
    bubbleTargetId: treeId
});

}); // Ext.onReady

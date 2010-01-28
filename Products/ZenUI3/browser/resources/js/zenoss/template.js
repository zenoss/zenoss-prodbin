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

var treeId = 'templateTree';
var router = Zenoss.remote.TemplateRouter;

function beforeselectHandler(sm, node, oldNode) {
}

function selectionchangeHandler(sm, node) {
}

var selModel = new Ext.tree.DefaultSelectionModel({
    listeners: {
        beforeselect: beforeselectHandler,
        selectionchange: selectionchangeHandler
    }
});

Ext.getCmp('master_panel').add({
    xtype: 'HierarchyTreePanel',
    id: treeId,
    directFn: router.getTemplates,
    router: router,
    selModel: selModel,
    root: {
        id: 'Monitoring Templates',
        uid: '/zport/dmd/Devices'
    }
});

Ext.getCmp('center_detail_panel').add({
    xtype: 'DataSourceTreeGrid',
    id: 'dataSourceTreeGrid',
    loader: new Ext.ux.tree.TreeGridLoader({
        directFn: router.getDataSources
    })
});

}); // Ext.onReady

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

Ext.ns('Zenoss', 'Zenoss.templates');

var REMOTE = Zenoss.remote.DeviceRouter;

Zenoss.templates.Container = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'border',
            border: false,
            defaults: {
                border: false,
                split: true
            },
            items: [{
                xtype: 'DataSourceTreeGrid',
                id: 'dataSourceTreeGrid',
                region: 'center',
                ref: 'dataSourceTreeGrid'
            }, {
                xtype: 'panel',
                layout: 'border',
                region: 'east',
                width: '35%',
                defaults: {
                    border: false,
                    split: true
                },
                items: [{
                    xtype: 'thresholddatagrid',
                    id: 'thresholdGrid',
                    ref: '../thresholdGrid',
                    region: 'north',
                    height: 300
                }, {
                    xtype: 'graphgrid',
                    id: 'graphGrid',
                    ref: '../graphGrid',
                    region: 'center'
                }]
            }]
        });
        Zenoss.templates.Container.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        this.updateTreeGrid(this.dataSourceTreeGrid, uid);
        this.updateGrid(this.thresholdGrid, uid);
        this.updateGrid(this.graphGrid, uid);
    },
    updateTreeGrid: function(treeGrid, uid){
        treeGrid.getRootNode().setId(uid);
        treeGrid.getRootNode().reload();
    },
    updateGrid: function(grid, uid) {
        grid.getStore().load({
            params: {uid: uid}
        });
    }
});
Ext.reg('templatecontainer', Zenoss.templates.Container);

Zenoss.BubblingSelectionModel = Ext.extend(Ext.tree.DefaultSelectionModel, {
    constructor: function(config) {
        Zenoss.BubblingSelectionModel.superclass.constructor.call(this, config);
        this.enableBubble('selectionchange');
        this.bubbleTarget = config.bubbleTarget;
    },
    getBubbleTarget: function() {
        return this.bubbleTarget;
    }
});

Zenoss.MonTemplateSelectionModel = Ext.extend(Zenoss.BubblingSelectionModel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            listeners: {
                beforeselect: function(sm, node) {
                    return node.isLeaf();
                }
            }
        });
        Zenoss.MonTemplateSelectionModel.superclass.constructor.call(this, config);
    }
});

Zenoss.templates.MonTemplateTreePanel = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config){
        Ext.applyIf(config, {
            useArrows: true,
            border: false,
            cls: 'x-tree-noicon',
            selModel: new Zenoss.MonTemplateSelectionModel({
                bubbleTarget: config.bubbleTarget
            }),
            loader: {
                directFn: REMOTE.getTemplates,
                baseAttrs: {singleClickExpand: true}
            },
            root: {
                text: _t('Monitoring Templates')
            }
        });
        Zenoss.templates.MonTemplateTreePanel.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        if ( uid.match('^/zport/dmd/Devices') ) {
            this.show();
            this.setRootNode({
                nodeType: 'async',
                id: uid,
                text: _t('Monitoring Templates'),
                expanded: true
            });
        } else {
            this.hide();
        }
    },
    onSelectionChange: function(node) {
        var detail;
        if (node) {
            detail = Ext.getCmp(this.initialConfig.detailPanelId);
            if ( ! detail.items.containsKey('montemplate') ) {
                detail.add({
                    xtype: 'templatecontainer',
                    id: 'montemplate',
                    ref: 'montemplate'
                });
            }
            detail.montemplate.setContext(node.attributes.uid);
            detail.getLayout().setActiveItem('montemplate');
        }
    }
});
Ext.reg('montemplatetreepanel', Zenoss.templates.MonTemplateTreePanel);

})();

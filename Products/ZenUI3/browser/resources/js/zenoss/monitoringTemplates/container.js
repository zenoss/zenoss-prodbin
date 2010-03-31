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

})();
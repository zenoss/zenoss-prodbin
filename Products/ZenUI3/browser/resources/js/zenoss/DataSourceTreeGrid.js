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

Ext.ns('Zenoss');

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
                    xtype: 'tbtext',
                    text: 'All Applied'
                }, {
                    xtype: 'button',
                    iconCls: 'configure'
                }, {
                    xtype: 'tbseparator'
                }, {
                    xtype: 'button',
                    iconCls: 'devprobs'
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

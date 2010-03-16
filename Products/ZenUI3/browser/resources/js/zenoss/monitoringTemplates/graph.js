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

Zenoss.templates.GraphGrid = Ext.extend(Ext.grid.GridPanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            title: _t('Graph Definitions'),
            store: {xtype: 'graphstore'},
            colModel: new Ext.grid.ColumnModel({
                columns: [
                    {dataIndex: 'name', header: _t('Name'), width: 400}                    
                ]
            })
        });
        Zenoss.templates.GraphGrid.superclass.constructor.call(this, config);
    }
});
Ext.reg('graphgrid', Zenoss.templates.GraphGrid);


})();

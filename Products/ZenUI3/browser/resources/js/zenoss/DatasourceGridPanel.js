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

Ext.grid.CheckColumn = function(config){
    Ext.apply(this, config);
    if(!this.id){
        this.id = Ext.id();
    }
    this.renderer = this.renderer.createDelegate(this);
};

Ext.grid.CheckColumn.prototype = {
    init : function(grid){
        this.grid = grid;
        this.grid.on('render', function(){
            var view = this.grid.getView();
            view.mainBody.on('mousedown', this.onMouseDown, this);
        }, this);
    },

    onMouseDown : function(e, t){
        if(t.className && t.className.indexOf('x-grid3-cc-'+this.id) != -1){
            e.stopEvent();
            var index = this.grid.getView().findRowIndex(t);
            var record = this.grid.store.getAt(index);
            record.set(this.dataIndex, !record.data[this.dataIndex]);
        }
    },

    renderer : function(v, p, record){
        p.css += ' x-grid3-check-col-td'; 
        return '<div class="x-grid3-check-col'+(v?'-on':'')+' x-grid3-cc-'+this.id+'"> </div>';
    }
}; 

Ext.ns('Zenoss');

var enabledColumn = new Ext.grid.CheckColumn({
    dataIndex: 'enabled',
    header: 'Enabled',
    width: 90
});

var myData = [
    ['iaLoadInt5', '1.3.6.1.4.1.2021.10.1.5.2', true, 'SNMP'],
    ['memAvailReal', '1.3.6.1.4.1.2021.4.6.0', true, 'Guage'],
    ['memAvailSwap', '1.3.6.1.4.1.2021.4.4.0', true, 'SNMP'],
    ['memBuffer', '1.3.6.1.4.1.2021.4.14.0', true, 'Guage'],
    ['memCached', '1.3.6.1.4.1.2021.4.15.0', true, 'SNMP'],
    ['SSCpuRawIdle', '1.3.6.1.5.1.2021.11.53.0', true, 'SNMP'],
    ['SSCpuRawSystem', '1.3.6.1.5.1.2021.10.11.52.0', true, 'Guage'],
    ['SSCpuRawUser', '1.3.6.1.5.1.2021.10.11.50.0', false, 'SNMP'],
    ['SSCpuRawWait', '1.3.6.1.5.1.2021.10.11.55.0', true, 'Guage'],
    ['sysUpTime', '1.3.6.1.5.1.2021.1.0.0', true, 'SNMP']
];

// create the data store
var store = new Ext.data.ArrayStore({
    fields: [
        {name: 'name'},
        {name: 'source'},
        {name: 'enabled'},
        {name: 'type'}
    ]
});

// manually load local data
store.loadData(myData);

/**
 * @class Zenoss.DatasourceGridPanel
 * @extends Ext.grid.GridPanel
 * @constructor
 */
Zenoss.DatasourceGridPanel = Ext.extend(Ext.grid.EditorGridPanel, {

    constructor: function(config) {
        Ext.applyIf(config, {
            autoExpandColumn: 'name',
            stripeRows: true,
            store: store,
            plugins: enabledColumn,
            sm: new Ext.grid.RowSelectionModel({singleSelect:true}),
            cm: new Ext.grid.ColumnModel({
                columns: [
                    {
                        id: 'name',
                        dataIndex: 'name',
                        header: 'Metrics by Datasource',
                        width: 300
                    }, {
                        dataIndex: 'source',
                        header: 'Source',
                        width: 300
                    },
                    enabledColumn, 
                    {
                        dataIndex: 'type',
                        header: 'Type',
                        width: 90
                    }
                ]
            })
        });
        Zenoss.DatasourceGridPanel.superclass.constructor.call(this, config);
    }
  
});

Ext.reg('DatasourceGridPanel', Zenoss.DatasourceGridPanel);

})();

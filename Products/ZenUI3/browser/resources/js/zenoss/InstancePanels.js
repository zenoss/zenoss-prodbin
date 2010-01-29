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

// templates for the events renderer
var iconTemplate = new Ext.Template('<'+'div style="float: left;" ' +
                     'class="severity-icon-small {severity}"><'+'/div>');
iconTemplate.compile();

var countTemplate = new Ext.Template('<'+'div style="' +
        'float: left; ' +
        'vertical-align: 27%;' +
        'margin-left: .5em;' +
        'margin-right: 1.5em;">' +
        '{count}<'+'/div>');
countTemplate.compile();

// renders events using icons for critical, error and warning
function statusRenderer(value) {
    return value;
    var result = '';
    Ext.each(['critical', 'error', 'warning'], function(severity) {
        result += iconTemplate.apply({severity: severity});
        result += countTemplate.apply({count: value[severity]});
    });
    return result;
}

// renders availability as a percentage with 3 digits after decimal point
function availabilityRenderer(value) {
    return Ext.util.Format.number(value*100, '0.000%');
}

Zenoss.InstanceColumnModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config) {
        var config = config || {};
        Ext.applyIf(config, {
            defaults: {
                sortable: false,
                menuDisabled: true,
                width: 200
            },
            columns: [{
                id: 'device',
                dataIndex: 'device',
                header: _t('Device')
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'monitor',
                dataIndex: 'monitor',
                header: _t('Monitor'),
            },{
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                renderer: statusRenderer
            }] // columns
        }); // Ext.applyIf
        Zenoss.InstanceColumnModel.superclass.constructor.call(this, config);
    } // constructor
});
Ext.reg('InstanceColumnModel', Zenoss.InstanceColumnModel);


/**
 * Device data store definition
 * @constructor
 */
Zenoss.InstanceStore = Ext.extend(Ext.ux.grid.livegrid.Store, {

    constructor: function(config) {
        var config = config || {};
        Ext.applyIf(config, {
            bufferSize: 50,
            defaultSort: {field: 'name', direction:'ASC'},
            sortInfo: {field: 'name', direction:'ASC'},
            proxy: new Ext.data.DirectProxy({
                directFn: config.directFn
            }),
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'data',
                totalProperty: 'totalCount'
            },[
                  {name: 'device', type: 'string'},
                  {name: 'name', type: 'string'},
                  {name: 'monitor', type: 'string'},
                  {name: 'status', type: 'auto'},
              ]
            )
        });
        Zenoss.InstanceStore.superclass.constructor.call(this, config);
    }
});

Ext.reg('InstanceStore', Zenoss.InstanceStore);


Zenoss.SimpleInstanceGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    constructor: function(config) {
        var store = {xtype:'InstanceStore'};
        if (!Ext.isEmpty(config.directFn)) {
            Ext.apply(store, {
                proxy: new Ext.data.DirectProxy({
                    directFn: config.directFn
                })
            });
        }
        var config = Ext.applyIf(config || {}, {
            cm: new Zenoss.InstanceColumnModel({
                menuDisabled: true
            }),
            sm: new Zenoss.ExtraHooksSelectionModel,
            store: store,
            enableDragDrop: false,
            border:false,
            rowSelectorDepth: 5,
            autoExpandColumn: 'device',
            stripeRows: true
        });
        Zenoss.SimpleInstanceGridPanel.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.getStore().load({params:{uid:uid}});
    }

});
Ext.reg('SimpleInstanceGridPanel', Zenoss.SimpleInstanceGridPanel);


Zenoss.InstanceGridPanel = Ext.extend(Zenoss.FilterGridPanel,{
    constructor: function(config) {
        var store = {xtype:'InstanceStore'};
        if (!Ext.isEmpty(config.directFn)) {
            Ext.apply(store, {
                proxy: new Ext.data.DirectProxy({
                    directFn: config.directFn
                })
            });
        }
        Ext.applyIf(config, {
            store: store,
            enableDragDrop: false,
            border: false,
            rowSelectorDepth: 5,
            view: new Zenoss.FilterGridView({
                nearLimit: 20,
                loadMask: {msg: 'Loading. Please wait...'}
            }),
            autoExpandColumn: 'name',
            cm: new Zenoss.InstanceColumnModel(),
            sm: new Zenoss.ExtraHooksSelectionModel(),
            stripeRows: true
        });
        Zenoss.InstanceGridPanel.superclass.constructor.call(this, config);
    }
});
Ext.reg('InstanceGridPanel', Zenoss.InstanceGridPanel);


})(); // end of function namespace scoping

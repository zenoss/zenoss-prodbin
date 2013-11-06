/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){


    var cards = Ext.create('Ext.data.Store', {
        fields: ['id', 'name'],
        data : [
            {id: 'details', name: _t('Details')}
        ]
    });
    Ext.define('Daemons.view.daemons.Details' ,{
        extend: 'Ext.Panel',
        alias: 'widget.daemonsdetails',
        dockedItems:[{
            xtype: 'toolbar',
            dock: 'top',
            items: [{
                xtype: 'combo',
                ref: 'menucombo',
                fieldLabel: _t('Display'),
                labelWidth: 50,
                valueField: 'id',
                displayField: 'name',
                store: cards,
                value: 'details'
            }]
        }],
        layout: 'card',
        initComponent: function() {
            this.callParent(arguments);
        }
    });
})();
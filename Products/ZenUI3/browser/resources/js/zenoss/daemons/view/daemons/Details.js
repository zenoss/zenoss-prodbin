/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){


    /**
     * The store for the combobox that acts as the details
     * menu. The id of the record MUST match the id of the  card we
     * want to display when selecting that option from the combo.
     **/
    var cards = Ext.create('Ext.data.Store', {
        fields: ['id', 'name'],
        data : [
            {id: 'details', name: _t('Details')},
            {id: 'devices', name: _t('Devices')}
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
                labelWidth: 50
            }]
        }],
        layout: 'card',
        initComponent: function() {
            this.items = [{
                xtype: 'panel',
                ref: 'details',
                id: 'details'
            },{
                xtype: 'DeviceGridPanel',
                ref: 'devices',
                id: 'devices',
                // we always want to show all devices, just filter on collectors
                uid: '/zport/dmd/Devices',
                multiSelect: true,
                viewConfig: {
                    plugins: {
                        ptype: 'gridviewdragdrop',
                        dragText: _t('Drag device to assign to a collector'),
                        dragGroup: 'assignCollector'
                    }
                }
            }];
            this.callParent(arguments);
        }
    });



    Ext.define('Daemons.dialog.AssignCollectors',{
        extend: 'Zenoss.dialog.SimpleMessageDialog',
        alias: ['widget.daemonassigncollectordialog'],
        messageFmt: _t("Are you sure you want to assign these {0} devices to the collector,  {1}?"),
        constructor: function(config) {
            config.message = Ext.String.format(this.messageFmt, config.numRecords, config.collectorId);
            this.callParent(arguments);
            this.okBtn.handler = config.okHandler;
        },
        title: _t('Assign Collector'),
        buttons: [{
            xtype: 'DialogButton',
            ref: '../okBtn',
            text: _t('OK')
        }, {
            xtype: 'DialogButton',
            text: _t('Cancel')
        }]
    });


})();

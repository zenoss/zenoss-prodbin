/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){



    Ext.define('Daemons.view.daemons.Details' ,{
        extend: 'Ext.Panel',
        alias: 'widget.daemonsdetails',
        dockedItems:[{
            xtype: 'toolbar',
            dock: 'top',
            items: [{
                xtype: 'combo',
                ref: 'menucombo',
                editable: false,
                fieldLabel: _t('Display'),
                labelWidth: 50,
                valueField: 'id',
                displayField: 'name',
                value: 'graphs'
            }]
        }],
        layout: 'card',
        initComponent: function() {
            this.items = [{
                id: 'graphs',
                ref: 'graphs',
                xtype:'graphpanel',
                newWindowButton: true,
                columns: 2
            },{
                xtype: 'panel',
                ref: 'details',
                id: 'details',
                bodyStyle: {
                    overflow: 'auto'
                }
            },{
                xtype: 'DeviceGridPanel',
                ref: 'devices',
                id: 'collectordevices',
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
            },{
                xtype: 'form',
                id: 'configs',
                ref: 'configPanel',
                layout: 'fit',
                buttonAlign: 'left',
                buttons: [{
                    xtype: 'button',
                    text: _t('Save'),
                    ref: 'configSaveBtn'
                }, {
                    xtype: 'button',
                    text: _t('Cancel'),
                    ref: 'configCancelBtn'
                }]
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
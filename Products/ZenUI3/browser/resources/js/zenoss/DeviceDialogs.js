/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2011, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){
    var router = Zenoss.remote.DeviceRouter;

    /**
     * @class Zenoss.form.RenameDevice
     * @extends Zenoss.SmartFormDialog
     * Dialog for renaming a Device
     **/
    Ext.define('Zenoss.form.RenameDevice',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 340,
                width: 500,
                title: _t('Reidentify Device'),
                submitHandler: Ext.bind(this.renameDevice, this),
                items: [{
                    xtype: 'hidden',
                    name: 'uid',
                    value: config.uid
                },{
                    xtype: 'displayfield',
                    value: _t(config.uid.split("/devices/")[1]),
                    labelAlign: 'left',
                    fieldLabel: _t('Current ID:')
                }, {
                    xtype: 'idfield',
                    name: 'newId',
                    labelAlign: 'left',
                    fieldLabel: _t('New ID'),
                    allowBlank: false
                }, {
                    xtype: 'displayfield',
                    value: _t('Caution: Past performance data stored for this device will be lost if it is not reassociated with the new ID. Moving the performance data may take a while.'),
                    margin: '0 0 40 0'

                }, {
                    xtype: 'fieldcontainer',
                    defaultType: 'radiofield',
                    layout: 'vbox',
                    align: 'left',
                    width: '500px',
                    items: [
                        {
                            boxLabel: 'Move the performance data to keep it associated with the device',
                            name: 'retainGraphData',
                            inputValue: true,
                            checked: true,
                            id: 'radRadio',
                            width: '500px'
                        }, {
                            xtype: 'displayfield',
                            value: _t('Note: This device will be subject to an outage -- no metrics will be collected or graphed during this renaming'),
                            width: '480px'
                        }, {
                            boxLabel: 'Delete the old performance data and start fresh with the new ID',
                            name: 'retainGraphData',
                            inputValue: false,
                            id: 'radderRadio',
                            width: '500px'
                        }, {
                            xtype: 'displayfield',
                            value: _t('Note: Collection of performance data will begin immediately, however please note that the old ID will remain unusable until the metrics for the previous ID have expired'),
                            width: '480px'
                        }
                    ]
                }]
            });
            this.callParent([config]);
        },
        renameDevice: function(values) {
            router.renameDevice(values, function(response){
                if (response.success) {
                    var uid = response.uid;
                    window.location = uid;
                }
            });
        }
    });

    /**
     * @class Zenoss.form.DeleteDevice
     * @extends Zenoss.SmartFormDialog
     * Dialog for deleting a Device
     **/
    Ext.define('Zenoss.form.DeleteDevice',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 175,
                title: _t('Delete Device'),
                submitHandler: Ext.bind(this.removeDevice, this),
                items: [{
                    xtype: 'hidden',
                    name: 'uid',
                    value: config.uid
                },{
                    xtype: 'panel',
                    bodyStyle: 'font-weight: bold; text-align:center',
                    html: _t('Are you sure you want to remove this device? '+
                             'There is no undo.')
                },{
                    name: "deleteEvents",
                    fieldLabel: _t('Close Events?'),
                    xtype: 'checkbox',
                    checked: true
                }]
            });
            this.callParent([config]);
        },
        removeDevice: function(values) {
            var deviceClass= values.uid.split("/devices")[0],
                options = {
                action: 'delete',
                uids: [values.uid],
                hashcheck: 1,
                deleteEvents: values.deleteEvents
            };

            router.removeDevices(options, function(response){
                if (response.success) {
                    window.location = deviceClass;
                }
            });
        },
        initComponent: function() {
            this.callParent(arguments);
            var btn = this.query("button[ref='buttonSubmit']")[0];
            btn.setDisabled(false);
        }
    });


}());

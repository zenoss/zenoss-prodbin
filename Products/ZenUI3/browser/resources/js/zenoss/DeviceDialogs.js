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
                height: 310,
                width: 500,
                padding: '20 40 20 18',
                title: _t('Reidentify Device'),
                submitHandler: Ext.bind(this.renameDevice, this),
                items: [{
                    xtype: 'hidden',
                    name: 'uid',
                    value: config.uid
                },{
                    xtype: 'displayfield',
                    padding: '0 0 14 0',
                    value: _t(config.uid.split("/devices/")[1]),
                    labelAlign: 'left',
                    fieldLabel: _t('Current ID:')
                }, {
                    xtype: 'idfield',
                    padding: '0 0 14 0',
                    name: 'newId',
                    labelAlign: 'left',
                    fieldLabel: _t('New ID'),
                    allowBlank: false
                }, {
                    padding: '20 48 20 0',
                    xtype: 'displayfield',
                    fieldCls: 'x-form-display-field-jumbo',
                    value: _t('Caution: Existing performance data stored for this device will be lost.')
                }]
            });
            this.callParent([config]);
        },
        renameDevice: function(values) {
            router.renameDevice(values, function(response){
                if (response.success) {
                    window.location = Zenoss.render.link(false, response.uid);
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

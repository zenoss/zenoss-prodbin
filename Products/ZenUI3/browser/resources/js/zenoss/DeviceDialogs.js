/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

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
                height: 150,
                title: _t('Rename Device'),
                submitHandler: Ext.bind(this.renameDevice, this),
                items: [{
                    xtype: 'hidden',
                    name: 'uid',
                    value: config.uid
                },{
                    xtype: 'label',
                    text: _t('Change the name of this device.')
                },{
                    xtype: 'idfield',
                    name: 'newId',
                    fieldLabel: _t('New ID')
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
                height: 250,
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
                    fieldLabel: _t('Delete Events?'),
                    xtype: 'checkbox',
                    checked: true
                },{
                    name: "deletePerf",
                    fieldLabel: _t('Delete performance data?'),
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
                deleteEvents: values.deleteEvents,
                deletePerf: values.deletePerf
            };

            router.removeDevices(options, function(response){
                if (response.success) {
                    window.location = deviceClass;
                }
            });
        }
    });


}());



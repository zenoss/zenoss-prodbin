/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/
Ext.ns('Zenoss.WinService');

Ext.onReady( function() {

    var zsf = Zenoss.Service.DetailForm;

    Ext.define("Zenoss.Service.DetailForm.MonitoredStartModes", {
        alias: ['widget.monitoredstartmodes'],
        extend:"Ext.form.field.ComboBox",
        constructor: function(config) {
            Ext.applyIf(config, {
                imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
                fieldLabel: _t('Monitored Start Modes'),
                width: 450,
                editable:false,
                multiSelect: true,
                displayField: 'name',
                valueField: 'name',
                store: Ext.create("Ext.data.ArrayStore", {
                    model: 'Zenoss.model.Name',
                    data: [['Auto'], ['Manual'], ['Disabled'], ['Not Installed']]
                })
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            Zenoss.remote.ServiceRouter.getMonitoredStartModes({uid: uid}, function(provider, response){
                this.setValue(response.result.data);
            }, this);
        },
        refresh: function() {
            if (this.uid) {
                this.setContext(this.uid);
            }
        }

    });

    zsf.formItems.items = [{
        items: [
            zsf.nameTextField,
            zsf.descriptionTextField,
            zsf.serviceKeysTextField,
            {
                xtype: 'monitoredstartmodes',
                id: 'monitoredStartModes',
                ref: '../../monitoredStartModes',
                name: 'monitoredStartModes'
            }
        ]
    }, {
        items: [
            zsf.zMonitor,
            zsf.zFailSeverity
        ]
    }];

    Zenoss.Service.Nav.initNav('/zport/dmd/Services/WinService');
    Zenoss.Service.DetailForm.initForm();
    Ext.getCmp('serviceForm').on('render', function(){
        Ext.getCmp('monitoredStartModes').setDisabled(true);
    });
    Ext.getCmp('navGrid').getSelectionModel().on('select', function(sm, record, rowIndex) {
        var monitoredStartModes = Ext.getCmp('serviceForm').monitoredStartModes;
        monitoredStartModes.setDisabled(false);
        monitoredStartModes.setContext(record.data.uid);
    });

});

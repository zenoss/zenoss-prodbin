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

    Ext.define("Zenoss.Service.DetailForm.MonitoredStartModesItemSelector", {
        alias: ['widget.monitoredstartmodesitemselector'],
        extend:"Ext.ux.form.ItemSelector",
        constructor: function(config) {
            Ext.applyIf(config, {
                imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
                drawUpIcon: false,
                drawDownIcon: false,
                drawTopIcon: false,
                drawBotIcon: false,
                displayField: 'startMode',
                valueField: 'startMode',
                fieldLabel: _t('Monitored Start Modes'),
                width: 300,
                store:  Ext.create('Ext.data.ArrayStore', {
                    data: [],
                    fields: ['startMode'],
                    sortInfo: {
                        field: 'startMode',
                        direction: 'ASC'
                    }
                })

            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            this.uid = uid;
            Zenoss.remote.ServiceRouter.getUnmonitoredStartModes({uid: uid}, function(provider, response){
                var data = response.result.data;
                Zenoss.remote.ServiceRouter.getMonitoredStartModes({uid: uid}, function(provider, response){
                    var results = [];
                    Ext.each(response.result.data, function(row){
                        results.push(row[0]);
                        data.push(row);
                    });
                    this.store.loadData(data);
                    this.bindStore(this.store);
                    this.setValue(results);
                }, this);
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
                xtype: 'monitoredstartmodesitemselector',
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
    Ext.getCmp('navGrid').getSelectionModel().on('rowselect', function(sm, rowIndex, record) {
        var monitoredStartModes = Ext.getCmp('serviceForm').monitoredStartModes;
        monitoredStartModes.setDisabled(false);
        monitoredStartModes.setContext(record.data.uid);
    });

});

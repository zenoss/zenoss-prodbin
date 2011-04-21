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

    zsf.MonitoredStartModesItemSelector = Ext.extend(Ext.ux.form.ItemSelector, {

        constructor: function(config) {
            Ext.applyIf(config, {
                imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
                drawUpIcon: false,
                drawDownIcon: false,
                drawTopIcon: false,
                drawBotIcon: false,
                displayField: 'startMode',
                valueField: 'startMode',
                hideLabel: true,
                hidden: true,
                listeners: {
                    scope: this,
                    change: function() {
                        this.fireEvent('valid', this);
                    }
                },
                multiselects: [{
                    legend: 'Available',
                    cls: 'multiselect',
                    height: 100,
                    appendOnly: true,
                    displayField: 'startMode',
                    valueField: 'startMode',
                    store: {
                        xtype: 'arraystore',
                        fields: ['startMode']
                    }
                },{
                    legend: 'Monitored',
                    cls: 'multiselect',
                    height: 100,
                    appendOnly: true,
                    displayField: 'startMode',
                    valueField: 'startMode',
                    store: {
                        xtype: 'arraystore',
                        fields: ['startMode']
                    }
                }]
            });
            zsf.MonitoredStartModesItemSelector.superclass.constructor.apply(this, arguments);
        },

        setContext: function(uid) {

            Zenoss.remote.ServiceRouter.getUnmonitoredStartModes({uid: uid}, function(provider, response){
                this.fromMultiselect.store.loadData(response.result.data);
            }, this);

            Zenoss.remote.ServiceRouter.getMonitoredStartModes({uid: uid}, function(provider, response){
                this.toMultiselect.store.loadData(response.result.data);
            }, this);

        },
        
        reset: function() {
            // do nothing (override behavior of superclass)
        }

    });
    
    Ext.reg('monitoredstartmodesitemselector', zsf.MonitoredStartModesItemSelector);

    zsf.formItems.items = [{
        items: [
            zsf.nameTextField, 
            zsf.descriptionTextField,
            zsf.serviceKeysTextField,
        {
            xtype: 'label',
            ref: '../../startModeLabel',
            text: 'Monitored Start Modes:',
            cls: 'x-form-item',
            forId: 'monitoredStartModes',
            hidden: true
        }, {
            xtype: 'monitoredstartmodesitemselector',
            id: 'monitoredStartModes',
            ref: '../../monitoredStartModes',
            name: 'monitoredStartModes',
            hidden: true
        }]
    }, {
        items: [
            zsf.zMonitor,
            zsf.zFailSeverity
        ]
    }];

    Zenoss.Service.Nav.initNav('/zport/dmd/Services/WinService');
    Zenoss.Service.DetailForm.initForm();
    Zenoss.Service.DetailGrid.initDetailPanel();

    Ext.getCmp('navGrid').getSelectionModel().on('rowselect', function(sm, rowIndex, record) {
        Ext.getCmp('serviceForm').startModeLabel.show();
        var monitoredStartModes = Ext.getCmp('serviceForm').monitoredStartModes;
        monitoredStartModes.show();
        monitoredStartModes.setContext(record.data.uid);
    });

});

/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/
Ext.ns('Zenoss.IpService');

Ext.onReady( function() {

    var zsn = Zenoss.Service.Nav;
    var zsf = Zenoss.Service.DetailForm;
    var zsg = Zenoss.Service.DetailGrid;

    var portTextField = {
        xtype: 'numberfield',
        fieldLabel: _t('Port'),
        name: 'port',
        width: "100%",
        id: 'portTextField',
        allowBlank: false,
        allowDecimals: false,
        allowNegative: false,
        maxValue: 65535,
        minValue: 1
    };

    zsf.formItems.items = [{
        items: [
            zsf.nameTextField,
            zsf.descriptionTextField,
            portTextField,
            zsf.serviceKeysTextField
        ]
    }, {
        items: [
            zsf.zMonitor,
            zsf.zFailSeverity
        ]
    }];

    zsn.columnModelConfig.columns = [
        {
            dataIndex: 'name',
            header: _t('Name'),
            id: 'name'
        },
        {
            dataIndex: 'port',
            header: _t('Port'),
            id: 'port',
            width: 50,
            filter: false
        },
        {
            dataIndex: 'count',
            header: _t('Count'),
            id: 'count',
            width: 50,
            renderer: zsn.nonZeroRenderer,
            filter: false
        }
    ];


    zsf.hiddenFieldIdsForOrganizer.push('portTextField');

    zsn.initNav('/zport/dmd/Services/IpService');
    zsf.initForm();
    zsg.initDetailPanel();
});

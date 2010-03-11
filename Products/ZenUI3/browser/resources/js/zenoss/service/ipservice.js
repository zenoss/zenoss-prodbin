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
        xtype: 'textfield',
        fieldLabel: _t('Port'),
        name: 'port',
        width: "100%"
    };

    var formItems = [
        {items: [zsf.nameTextField, zsf.descriptionTextField,
                 portTextField, zsf.serviceKeysTextField]},

        {items: [zsf.monitoringFieldSet]}
    ];

    var navColumns = [
        {
            dataIndex: 'name',
            header: _t('Name'),
            id: 'name'
        },
        {
            dataIndex: 'port',
            header: _t('Port'),
            id: 'port',
            width: 40,
            filter: false
        },
        {
            dataIndex: 'count',
            header: _t('Count'),
            id: 'count',
            width: 40,
            renderer: zsn.nonZeroRenderer,
            filter: false
        }
    ];


    zsn.columnModelConfig.columns = navColumns;
    zsf.formItems.items = formItems;

    zsn.initNav('/zport/dmd/Services/IpService');
    zsf.initForm();
    zsg.initDetailPanel();
});

/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/
Ext.onReady( function() {

    /**********************************************************************
     *
     * Service Panel Functionality
     *
     */

    var zs = Ext.ns('Zenoss.Service.DetailForm');

    zs.actioncompleteHandler = function(form, action) {
        form = Ext.getCmp('serviceForm');

        var isClass = (form.contextUid.indexOf('serviceclasses') > 0),
            isRoot = form.contextUid == Ext.getCmp('navTree').root.attributes.uid;

        if (action.type == 'directload') {
            form.isLoadInProgress = false;
            Ext.each(zs.hiddenFieldIdsForOrganizer, function(i){
                    var o = Ext.getCmp(i);
                    o.setVisible(isClass);
                    o.label.setVisible(isClass);
                });
            Ext.getCmp('nameTextField').setDisabled(isRoot);
        }
        else if (action.type == 'directsubmit') {
            if (isClass) {
                // Update the record in the navigation grid.
                var navGrid = Ext.getCmp('navGrid'),
                    navGridModel = navGrid.getSelectionModel(),
                    navGridRecord = navGridModel.getSelected();

                if (navGridRecord) {
                    Zenoss.util.applyNotIf(navGridRecord.data, form.form.getValues());
                    navGrid.view.refreshRow(navGridRecord);
                }
            }
            else {
                // Update the record in the navigation tree.
                var treeSM = Ext.getCmp('navTree').getSelectionModel(),
                    treeSNode = treeSM.getSelectedNode();

                treeSNode.attributes.text.text = form.form.getValues().name;
                treeSNode.setText(treeSNode.attributes.text);
            }
        }
    };

    zs.nameTextField = {
        xtype: 'textfield',
        id: 'nameTextField',
        fieldLabel: _t('Name'),
        name: 'name',
        allowBlank: false,
        width: "100%"
    };

    zs.descriptionTextField = {
        xtype: 'textfield',
        id: 'descriptionTextField',
        fieldLabel: _t('Description'),
        name: 'description',
        width: "100%"
    };

    zs.serviceKeysTextField = {
        xtype: 'textarea',
        id: 'serviceKeysTextField',
        fieldLabel: _t('Service Keys'),
        name: 'serviceKeys',
        width: "100%"
    };

    zs.zMonitor = {
        xtype: 'zprop',
        ref: '../../zMonitor',
        title: _t('Enable Monitoring? (zMonitor)'),
        name: 'zMonitor',
        localField: {
            xtype: 'select',
            mode: 'local',
            store: [[true, 'Yes'], [false, 'No']]
        }
    };

    zs.zFailSeverity = {
        xtype: 'zprop',
        ref: '../../zFailSeverity',
        title: _t('Failure Event Severity (zFailSeverity)'),
        name: 'zFailSeverity',
        localField: {
            xtype: 'select',
            mode: 'local',
            store: Zenoss.env.SEVERITIES.slice(0, 5)
        }
    };

    zs.formItems = {
        layout: 'column',
        border: false,
        defaults: {
            layout: 'form',
            border: false,
            bodyStyle: 'padding: 15px',
            columnWidth: 0.5
        },
        items: [{
            items: [
                zs.nameTextField, 
                zs.descriptionTextField,
                zs.serviceKeysTextField
            ]
        }, {
            items: [
                zs.zMonitor,
                zs.zFailSeverity
            ]
        }]
    };

    zs.hiddenFieldIdsForOrganizer = [zs.serviceKeysTextField.id];

    zs.formConfig = {
        xtype: 'basedetailform',
        id: 'serviceForm',
        region: 'center',
        items: zs.formItems,
        permission: 'Manage DMD',
        trackResetOnLoad: true,
        router: Zenoss.remote.ServiceRouter
    };

    zs.initForm = function() {
        var serviceForm = Ext.getCmp('detail_panel').add(zs.formConfig);
        serviceForm.on('actioncomplete', zs.actioncompleteHandler);
    };
});

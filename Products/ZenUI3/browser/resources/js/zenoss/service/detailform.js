/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
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

    var zsf = Ext.ns('Zenoss.Service.DetailForm');

    zsf.actioncompleteHandler = function(form, action) {
        form = Ext.getCmp('serviceForm');

        var isClass = (form.contextUid.indexOf('serviceclasses') > 0),
            isRoot = form.contextUid == Ext.getCmp('navTree').root.attributes.uid;

        if (action.type == 'directload') {
            form.isLoadInProgress = false;
            Ext.each(zsf.hiddenFieldIdsForOrganizer, function(i){
                    var o = Ext.getCmp(i);
                    // make sure comp exists
                    if (!o){
                        return;
                    }
                    o.setVisible(isClass);
                    o.label.setVisible(isClass);
                    o.setDisabled(!isClass);
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
                    Ext.getCmp('detail_panel').detailCardPanel.setContext(navGridRecord.data.uid);
                }
            }
            else {
                // Update the record in the navigation tree.
                var treeSM = Ext.getCmp('navTree').getSelectionModel(),
                    treeSNode = treeSM.getSelectedNode();

                treeSNode.attributes.text.text = form.form.getValues().name;
                treeSNode.setText(treeSNode.attributes.text);
                Ext.getCmp('detail_panel').detailCardPanel.setContext(treeSNode.attributes.uid);
            }
        }
    };

    zsf.nameTextField = {
        xtype: 'textfield',
        id: 'nameTextField',
        fieldLabel: _t('Name'),
        name: 'name',
        allowBlank: false,
        width: "100%"
    };

    zsf.descriptionTextField = {
        xtype: 'textfield',
        id: 'descriptionTextField',
        fieldLabel: _t('Description'),
        name: 'description',
        width: "100%"
    };

    zsf.sendStringTextField = {
        xtype: 'textfield',
        id: 'sendStringTextField',
        fieldLabel: _t('Send String'),
        name: 'sendString',
        width: "100%"
    };

    zsf.expectRegexTextField = {
        xtype: 'textfield',
        id: 'expectRegexTextField',
        fieldLabel: _t('Expect Regex'),
        name: 'expectRegex',
        width: "100%"
    };

    zsf.serviceKeysTextField = {
        xtype: 'textarea',
        id: 'serviceKeysTextField',
        fieldLabel: _t('Service Keys'),
        name: 'serviceKeys',
        width: "100%"
    };

    zsf.zMonitor = {
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

    zsf.zFailSeverity = {
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

    zsf.formItems = {
        layout: 'column',
        border: false,
        defaults: {
            layout: 'form',
            border: false,
            bodyStyle: 'padding: 15px',
            columnWidth: 0.5
        }
        // items is set in winservice.js and ipservice.js
    };

    zsf.hiddenFieldIdsForOrganizer = [
        zsf.serviceKeysTextField.id
    ];

    zsf.formConfig = {
        xtype: 'basedetailform',
        id: 'serviceForm',
        region: 'center',
        items: zsf.formItems,
        permission: 'Manage DMD',
        trackResetOnLoad: true,
        router: Zenoss.remote.ServiceRouter
    };

    zsf.initForm = function() {
        var serviceForm = Ext.getCmp('detail_panel').add(zsf.formConfig);
        serviceForm.on('actioncomplete', zsf.actioncompleteHandler);
    };
});

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

    /**
     * Enables or disables monitoring options based on inheritance
     * @param {boolean} disabled Whether to disable or not
     */
    zs.setMonitoringDisabled = function(disabled) {
        Ext.getCmp('monitorCheckbox').setDisabled(disabled);
        Ext.getCmp('eventSeverityCombo').setDisabled(disabled);
    };

    /**
     * Handles the acquiredCheckbox check events.  If unchecked, it will
     * load its own values, but if checked, it will load its parent's
     * values instead.
     * @implements Ext.form.Checkbox:check
     * @param {Ext.form.Checkbox} checkbox The checkbox itself
     * @param {boolean} checked The value of the checkbox as a boolean
     */
    zs.acquiredCheckboxHandler = function(checkbox, checked) {
        if ( Ext.getCmp('serviceForm').isLoadInProgress ) {
            return;
        }
        zs.setMonitoringDisabled(checked);

        var router = Zenoss.remote.ServiceRouter,
            uid = Ext.getCmp('serviceForm').contextUid;

        var callback = function(provider, response) {
            var info = response.result.data;
            Ext.getCmp('monitorCheckbox').setValue(info.monitor);
            Ext.getCmp('eventSeverityCombo').setValue(info.failSeverity);
        };

        router.getInfo({uid: uid, keys: ['monitor', 'failSeverity']}, callback);
    };
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
        else if (action.type == 'zsubmit') {
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

    zs.acquiredCheckbox = {
        xtype: 'checkbox',
        id: 'acquiredCheckbox',
        fieldLabel: _t('Inherited?'),
        name: 'isInherited',
        handler: zs.acquiredCheckboxHandler,
        submitValue: true
    };

    zs.monitorCheckbox = {
        xtype: 'checkbox',
        id: 'monitorCheckbox',
        fieldLabel: _t('Enabled'),
        name: 'monitor',
        submitValue: true
    };

    //TODO: replace with 'severity' xtype
    zs.eventSeverityCombo = {
        xtype: 'combo',
        id: 'eventSeverityCombo',
        fieldLabel: _t('Event Severity'),
        name: 'failSeverity',
        mode: 'local',
        store: new Ext.data.ArrayStore({
            data: Zenoss.env.SEVERITIES,
            fields: ['value', 'name']
        }),
        valueField: 'value',
        displayField: 'name',
        hiddenName: 'failSeverity',
        hiddenId: 'eventSeverityComboHidden',
        triggerAction: 'all',
        forceSelection: true,
        editable: false,
        autoSelect: true
    };

    zs.monitoringFieldSet = {
        xtype: 'ColumnFieldSet',
        title: _t('Monitoring'),
        __inner_items__: [
            {
                items: zs.acquiredCheckbox
            }, {
                items: zs.monitorCheckbox
            }, {
                items: zs.eventSeverityCombo
            }
        ]
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
        items: [
            {items: [zs.nameTextField, zs.descriptionTextField,
                     zs.serviceKeysTextField]},

            {items: [zs.monitoringFieldSet]}
        ]
    };

    zs.hiddenFieldIdsForOrganizer = [zs.serviceKeysTextField.id];

    zs.formConfig = {
        xtype: 'basedetailform',
        id: 'serviceForm',
        region: 'center',
        items: zs.formItems,
        trackResetOnLoad: true,
        api: {
            load: Zenoss.remote.ServiceRouter.getInfo,
            submit: Zenoss.remote.ServiceRouter.setInfo
        }
    };

    var clearForm = function(form) {
        var q = {};
        Ext.each(form.items.items, function(i){ q[i.id] = null; } );
        form.setValues(q);
    };

    zs.initForm = function() {

        var serviceForm = Ext.create(zs.formConfig);
        serviceForm.setContext = function(uid) {
                this.contextUid = uid;
                clearForm(this.getForm());
                this.load({ params: {uid: uid} });
            }.createDelegate(serviceForm);
        Ext.getCmp('detail_panel').add(serviceForm);
        serviceForm.on('actioncomplete', zs.actioncompleteHandler);
    };
});

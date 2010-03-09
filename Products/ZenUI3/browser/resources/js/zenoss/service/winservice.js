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
Ext.ns('Zenoss.ui.Service');

Ext.onReady( function() {

    /**********************************************************************
     *
     * Tree Functionality
     *
     */

    /**
     * Callback handler for click events coming from the tree
     * @param {Ext.tree.TreeNode} node Node clicked upon
     */
    function treeSelectHandler(tree, node) {
        // Change context
        setPanelsDisabled(false);
        Ext.getCmp('serviceForm').setContext(node.attributes.uid);
        Ext.getCmp('serviceInstancePanel').setContext(node.attributes.uid);
    }

    /**
     * Initialize the tree.
     */
    function treeInitialize() {
        var treePanel = Ext.create({
            xtype: 'HierarchyTreePanel',
            id: 'serviceTree',
            searchField: true,
            autoScroll: true,
            directFn: Zenoss.remote.ServiceRouter.getTree,
            root: {
                id: 'WinService',
                uid: '/zport/dmd/Services/WinService',
                text: 'Windows Services'
            },
            listeners: {
                render: function(tree){
                    tree.getRootNode().on('load', function(node){
                        node.select();
                    });
                }
            }
        });
        Ext.getCmp('master_panel').add(treePanel);
        treePanel.getSelectionModel().on('selectionchange', treeSelectHandler);
    }

    /**********************************************************************
     *
     * Instances Functionality
     *
     */

    function instancePanelInitialize() {
        var instancePanel = {
            xtype: 'SimpleInstanceGridPanel',
            id: 'serviceInstancePanel',
            disabled: true,
            buttonTitle: _t('Services'),
            iconCls: 'services',
            directFn: Zenoss.remote.ServiceRouter.getInstances,
            tbar: [ { xtype: 'tbtext', text: _t('Instances') } ]
        }
        Ext.getCmp('bottom_detail_panel').add(instancePanel);
    }

    /**********************************************************************
     *
     * Service Panel Functionality
     *
     */

    /**
     * Enables or disables all data entry panels on the screen.
     * @param {boolean} disabled Whether to disable or not
     */
    function setPanelsDisabled(disabled) {
        Ext.getCmp('serviceForm').setDisabled(disabled);
        Ext.getCmp('serviceInstancePanel').setDisabled(disabled);
    }

    /**
     * Enables or disables monitoring options based on inheritance
     * @param {boolean} disabled Whether to disable or not
     */
    function setMonitoringDisabled(disabled) {
        Ext.getCmp('monitorCheckbox').setDisabled(disabled);
        Ext.getCmp('eventSeverityCombo').setDisabled(disabled);
    }

    /**
     * Handles the acquiredCheckbox check events.  If unchecked, it will
     * load its own values, but if checked, it will load its parent's
     * values instead.
     * @param {Ext.form.Checkbox} checkbox The checkbox itself
     * @param {boolean} checked The value of the checkbox as a boolean
     */
    function acquiredCheckboxHandler(checkbox, checked) {
        setMonitoringDisabled(checked);
        var router = Zenoss.remote.ServiceRouter;
        var serviceTree = Ext.getCmp('serviceTree');
        var selectionModel = serviceTree.getSelectionModel();
        var selectedNode = selectionModel.getSelectedNode();

        var uid;
        if (checked && selectedNode.parentNode !== null) {
            uid = selectedNode.parentNode.attributes.uid;
        } else {
            uid = selectedNode.attributes.uid;
        }

        var callback = function(provider, response) {
            var info = response.result.data;
            Ext.getCmp('monitorCheckbox').setValue(info.monitor);
            Ext.getCmp('eventSeverityCombo').setValue(info.eventSeverity);
        };

        router.getInfo({uid: uid, keys: ['monitor', 'eventSeverity']}, callback);
    }

    function saveForm(button, event) {
        var serviceTree = Ext.getCmp('serviceTree');
        var selectionModel = serviceTree.getSelectionModel();
        var selectedNode = selectionModel.getSelectedNode();
        var nameTextField = Ext.getCmp('nameTextField');
        selectedNode.attributes.text.text = nameTextField.getValue();
        selectedNode.setText(selectedNode.attributes.text);
        var form = Ext.getCmp('serviceForm').getForm();
        var params = Ext.apply({uid: selectedNode.attributes.uid}, form.getValues());
        form.api.submit(params);
        var values = Ext.applyIf(form.getValues(), {
            isMonitoringAcquired: 'off',
            monitor: 'off',
            ignoreParameters: 'off'
        });
        // setValues makes isDirty return false
        form.setValues(values);

    }

    function resetForm(button, event) {
        var form = Ext.getCmp('serviceForm').getForm();
        form.reset();
    }
    /**
     * Form definition variables
     */
    var nameTextField = {
        xtype: 'textfield',
        id: 'nameTextField',
        fieldLabel: _t('Name'),
        name: 'name',
        allowBlank: false,
        width: "100%"
    };

    var descriptionTextField = {
        xtype: 'textfield',
        id: 'descriptionTextField',
        fieldLabel: _t('Description'),
        name: 'description',
        width: "100%"
    };

    var serviceKeysTextField = {
        xtype: 'textarea',
        fieldLabel: _t('Service Keys'),
        name: 'serviceKeys',

        width: "100%"
    };

    var acquiredCheckbox = {
        xtype: 'checkbox',
        id: 'acquiredCheckbox',
        fieldLabel: _t('Inherited'),
        name: 'isMonitoringAcquired',
        handler: acquiredCheckboxHandler
    };

    var monitorCheckbox = {
        xtype: 'checkbox',
        id: 'monitorCheckbox',
        fieldLabel: _t('Enabled'),
        name: 'monitor'
    };

    var eventSeverityCombo = {
        xtype: 'combo',
        id: 'eventSeverityCombo',
        fieldLabel: _t('Event Severity'),
        name: 'eventSeverity',
        triggerAction: 'all',
        mode: 'local',
        valueField: 'severityId',
        displayField: 'severityText',
        store: new Ext.data.ArrayStore({
            fields: ['severityId', 'severityText'],
            data: Zenoss.env.SEVERITIES.slice(0, 5)
        })
    };

    var monitoringFieldSet = {
        xtype: 'ColumnFieldSet',
        title: _t('Monitoring'),
        __inner_items__: [
            {
                items: acquiredCheckbox
            }, {
                items: monitorCheckbox
            }, {
                items: eventSeverityCombo
            }
        ]
    };

    var saveButton = {
        xtype: 'button',
        id: 'saveButton',
        text: _t('Save'),
        handler: saveForm
    };

    var cancelButton = {
        xtype: 'button',
        id: 'cancelButton',
        text: _t('Cancel'),
        handler: resetForm
    };

    var formItems = {
        layout: 'column',
        border: false,
        defaults: {
            layout: 'form',
            border: false,
            bodyStyle: 'padding: 15px',
            labelSeparator: ' ',
            columnWidth: 0.5
        },
        items: [
            {items: [nameTextField, descriptionTextField,
                     monitoringFieldSet, saveButton]},

            {items: [serviceKeysTextField]}
        ]
    };

    var formConfig = {
        xtype: 'form',
        id: 'serviceForm',
        paramsAsHash: true,
        items: formItems,
        border: false,
        labelAlign: 'top',
        autoScroll: true,
        disabled: true,
        trackResetOnLoad: true,
        api: {
            load: Zenoss.remote.ServiceRouter.getInfo,
            submit: Zenoss.remote.ServiceRouter.setInfo
        }
    };

    function formInitialize() {
        var serviceForm = new Ext.form.FormPanel(formConfig);
        serviceForm.setContext = function(uid) {
                this.load({ params: {uid: uid} });
            }.createDelegate(serviceForm);
        Ext.getCmp('top_detail_panel').add(serviceForm);
    }

    treeInitialize();
    formInitialize();
    instancePanelInitialize();

}); // Ext.onReady

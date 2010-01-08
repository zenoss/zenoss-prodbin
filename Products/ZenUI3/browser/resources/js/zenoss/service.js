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
    function treeClickHandler(node) {
        // Change context
        setPanelsDisabled(false);
    }

    /**
     * Initialize the tree.
     */
    function treeInitialize() {
        Ext.getCmp('master_panel').add({
            xtype: 'HierarchyTreePanel',
            id: 'serviceTree',
            searchField: true,
            autoScroll: true,
            directFn: Zenoss.remote.ServiceRouter.getTree,
            root: 'Services',
            rootuid: '/zport/dmd/Services',
            listeners: {click: treeClickHandler}
        });
    }

    /**********************************************************************
     *
     * CardPanel Functionality
     *
     */

    /**
     * Initialize the Card Panel
     */
    function cardPanelInitialize() {
        Ext.getCmp('bottom_detail_panel').add({
            xtype: 'ContextCardButtonPanel',
            id: 'itCardButtonPanel',
            disabled: true,
            items: [ { xtype: 'SimpleDeviceGridPanel',
                       buttonTitle: _t('Devices'),
                       iconCls: 'devprobs'
                     },
                     { xtype: 'SimpleEventGridPanel',
                       buttonTitle: _t('Events'),
                       iconCls: 'events'
                     }
            ]
        });
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
        Ext.getCmp('itCardButtonPanel').setDisabled(disabled);
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

    /**
     * Form definition variables
     */
    var nameTextField = {
        xtype: 'textfield',
        fieldLabel: _t('Name'),
        name: 'name',
        allowBlank: false,
        width: "100%"
    }

    var descriptionTextField = {
        xtype: 'textfield',
        fieldLabel: _t('Description'),
        name: 'description',
        width: "100%"
    }

    var serviceKeysTextField = {
        xtype: 'textfield',
        fieldLabel: _t('Service Keys'),
        name: 'serviceKeys',
        width: "100%"
    }

    var portTextField = {
        xtype: 'textfield',
        fieldLabel: _t('Port'),
        name: 'port',
        width: "100%"
    }

    var acquiredCheckbox = {
        xtype: 'checkbox',
        id: 'acquiredCheckbox',
        fieldLabel: _t('Inherited'),
        name: 'isMonitoringAcquired',
        handler: acquiredCheckboxHandler
    }

    var monitorCheckbox = {
        xtype: 'checkbox',
        id: 'monitorCheckbox',
        fieldLabel: _t('Enabled'),
        name: 'monitor'
    }

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
    }

    var monitoringFieldSet = {
        xtype: 'ColumnFieldSet',
        title: _t('Monitoring'),
        __inner_items__: [
            {
                items: acquiredCheckbox
            }, {
                items: monitorCheckbox,
                bodyStyle: 'padding-left: 15px'
            }, {
                items: eventSeverityCombo,
                bodyStyle: 'padding-left: 15px'
            }
        ]
    }

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
            {items: [nameTextField,
                     descriptionTextField ]},
            {items: [serviceKeysTextField,
                     portTextField ]},
            {items: [monitoringFieldSet]}
        ]
    }

    var formConfig = {
        xtype: 'form',
        id: 'serviceForm',
        paramsAsHash: true,
        items: formItems,
        border: false,
        labelAlign: 'top',
        autoScroll: true,
        disabled: true,
        api: {
            load: Zenoss.remote.ServiceRouter.getInfo,
            submit: Zenoss.remote.ServiceRouter.submitInfo
        },
        tbar: [
               {
                   xtype: 'button',
                   id: 'Save-button',
                   text: _t('Save'),
                   iconCls: 'save',
                   handler: function(button, event) {
                           var serviceTree = Ext.getCmp('serviceTree');
                           var selectionModel = serviceTree.getSelectionModel();
                           var selectedNode = selectionModel.getSelectedNode();
                           var nameTextField = Ext.getCmp('nameTextField');
                           selectedNode.attributes.text.text = nameTextField.getValue();
                           selectedNode.setText(selectedNode.attributes.text);
                           var form = Ext.getCmp('serviceForm').getForm();
                           var params = Ext.apply({id: selectedNode.id}, form.getValues());
                           form.api.submit(params);
                       }
               }
        ]
    }

    /**
     * @class Zenoss.ui.Service.ServiceFormPanel
     * @extends Ext.form.FormPanel
     * The form panel that displays information about a service organizer or class
     * @constructor
     */
    Zenoss.ui.Service.ServiceFormPanel = Ext.extend(Ext.form.FormPanel, {

        constructor: function(config) {
            Ext.apply(config, formConfig);
            Zenoss.ui.Service.ServiceFormPanel.superclass.constructor.call(this, config);
            //this.on('actioncomplete', actioncompleteHandler);
        }

    });

    Ext.reg('ServiceFormPanel', Zenoss.ui.Service.ServiceFormPanel);

    cardPanelInitialize();
    treeInitialize();

    var serviceForm = new Zenoss.ui.Service.ServiceFormPanel({});


    // place the form in the top right
    Ext.getCmp('top_detail_panel').add(serviceForm);

    serviceForm.getForm().load({params:{uid: 'Services'}});



}); // Ext.onReady

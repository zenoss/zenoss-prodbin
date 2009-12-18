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

// Script for the processes page.

Ext.onReady(function(){


/* ***************************************************************************
 *
 *   master_panel - the processes tree on the left
 *
 */

// function that gets run when the user clicks on a node in the tree
function clickHandler(node) {
    
    // load up appropriate data in the form
    Ext.getCmp('processForm').getForm().load({
        params: {id: node.attributes.id}
    });
    
    // load up appropriate data in the devices grid
    Ext.getCmp('deviceGrid').getStore().load({
        params: {id: node.attributes.id}
    });
    
    // load up appropriate data in the event grid
    Ext.getCmp('eventGrid').getStore().load({
        params: {id: node.attributes.id}
    });
    
} // clickHandler

Ext.getCmp('master_panel').add({
    xtype: 'HierarchyTreePanel',
    id: 'processTree',
    searchField: true,
    directFn: Zenoss.remote.ProcessRouter.getTree,
    root: 'Processes',
    listeners: {click: clickHandler}
}); // master_panel.add


/* **************************************************************************
 *
 *   top_detail_panel - the process form on the top right
 *
 */


// disable the monitoring fields if monitoring settings are inherited
function  setMonitoringDisabled(disabled) {
    var monitorCheckbox = Ext.getCmp('Enabled-option');
    var eventSeverityCombo = Ext.getCmp('Event_Severity-selection');
    monitorCheckbox.setDisabled(disabled);
    eventSeverityCombo.setDisabled(disabled);
}

function inheritedCheckboxHandler(checkbox, checked) {
    setMonitoringDisabled(checked);
    var router = Zenoss.remote.ProcessRouter;
    var processTree = Ext.getCmp('processTree');
    var selectionModel = processTree.getSelectionModel();
    var selectedNode = selectionModel.getSelectedNode();

    var id;
    if (checked && selectedNode.parentNode !== null) {
        id = selectedNode.parentNode.id;
    } else {
        id = selectedNode.id;
    }

    var callback = function(provider, response) {
        var info = response.result.data;
        var monitorCheckbox = Ext.getCmp('Enabled-option');
        monitorCheckbox.setValue(info.monitor);
        var eventSeverityCombo = Ext.getCmp('Event_Severity-selection');
        eventSeverityCombo.setValue(info.eventSeverity);
    };
    
    router.getInfo({id: id, keys: ['monitor', 'eventSeverity']}, callback);
}

// when the form loads, show/hide the regex fieldset
function actioncompleteHandler(form, action) {
    if (action.type == 'directload') {
        var processInfo = action.result.data;
        var regexFieldSet = Ext.getCmp('regexFieldSet');
        var nameTextField = Ext.getCmp('nameTextField');
        var inheritedCheckbox = Ext.getCmp('inheritedCheckbox');
        regexFieldSet.setVisible(processInfo.hasRegex);
        regexFieldSet.doLayout();
        nameTextField.setDisabled(processInfo.name == 'Processes');
        inheritedCheckbox.setDisabled(processInfo.name == 'Processes');
        setMonitoringDisabled(processInfo.isMonitoringAcquired);
        Ext.getCmp('processForm').setDisabled(action.result.disabled);
    }
}

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
    fieldLabel: _t('Description'),
    name: 'description',
    width: "100%"
};

var inheritedCheckbox = {
    xtype: 'checkbox',
    id: 'Inherited-option',
    fieldLabel: _t('Inherited'),
    name: 'isMonitoringAcquired',
    handler: inheritedCheckboxHandler
};

var monitorCheckbox = {
    xtype: 'checkbox',
    id: 'Enabled-option',
    fieldLabel: _t('Enabled'),
    name: 'monitor'
};

var eventSeverityCombo = {
    xtype: 'combo',
    id: 'Event_Severity-selection',
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

var regexTextField = {
    xtype: 'textfield',
    id: 'Pattern-entry',
    fieldLabel: _t('Pattern'),
    name: 'regex',
    width: "100%"
};

var ignoreParametersCheckbox = {
    xtype: 'checkbox',
    id: 'Ignore_Parameters-option',
    fieldLabel: _t('Ignore Parameters'),
    name: 'ignoreParameters'
};

var monitoringFieldSet = {
    xtype: 'ColumnFieldSet',
    title: _t('Monitoring'),
    __innner_items__: [
        {
            items: inheritedCheckbox
        }, {
            items: monitorCheckbox,
            bodyStyle: 'padding-left: 15px'
        }, {
            items: eventSeverityCombo,
            bodyStyle: 'padding-left: 15px'
        }
    ]
}; // monitoringFieldSet

var regexFieldSet = {
    xtype: 'ColumnFieldSet',
    id: 'regexFieldSet',
    title: _t('Regular Expression'),
    hidden: true,
    __innner_items__: [
        {
            items: regexTextField,
            columnWidth: 0.6
        }, {
            items: ignoreParametersCheckbox,
            bodyStyle: 'padding-left: 15px'
        }
    ]
}; // regexFieldSet

// the items that make up the form
var processFormItems = {
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
        {items: [nameTextField, monitoringFieldSet]},
        {items: [descriptionTextField, regexFieldSet]}
    ]
}; // processFormItems

var processFormConfig = {
    xtype: 'form',
    id: 'processForm',
    paramsAsHash: true,
    items: processFormItems,
    border: false,
    labelAlign: 'top',
    autoScroll: true,
    api: {
        load: Zenoss.remote.ProcessRouter.getInfo,
        submit: Zenoss.remote.ProcessRouter.setInfo
    },
    tbar: [
        {
            xtype: 'button',
            id: 'Save-button',
            text: _t('Save'),
            iconCls: 'save',
            handler: function(button, event) {
                var processTree = Ext.getCmp('processTree');
                var selectionModel = processTree.getSelectionModel();
                var selectedNode = selectionModel.getSelectedNode();
                var nameTextField = Ext.getCmp('nameTextField');
                selectedNode.attributes.text.text = nameTextField.getValue();
                selectedNode.setText(selectedNode.attributes.text);
                var form = Ext.getCmp('processForm').getForm();
                var params = Ext.apply({id: selectedNode.id}, form.getValues());
                form.api.submit(params);
            }
        }
    ] //tbar
};

Ext.ns('Zenoss');

/**
 * @class Zenoss.ProcessFormPanel
 * @extends Ext.form.FormPanel
 * The form panel that displays information about a process organizer or class
 * @constructor
 */
Zenoss.ProcessFormPanel = Ext.extend(Ext.form.FormPanel, {

    constructor: function(userConfig) {
        var config = Ext.apply(processFormConfig, userConfig);
        Zenoss.ProcessFormPanel.superclass.constructor.call(this, config);
        this.on('actioncomplete', actioncompleteHandler);
    }

});

Ext.reg('ProcessFormPanel', Zenoss.ProcessFormPanel);

var processForm = new Zenoss.ProcessFormPanel({});

// place the form in the top right
Ext.getCmp('top_detail_panel').add(processForm);

processForm.getForm().load({params:{id: 'Processes'}});


/* ***********************************************************************
 *
 *   bottom_detail_panel - the device and event grid on the bottom right
 *
 */

 // the store that holds the records for the device grid
 var deviceStore = {
     xtype: 'DeviceStore',
     autoLoad: {params:{id: 'Processes'}},
     // Ext.data.DirectProxy config
     api: {read: Zenoss.remote.ProcessRouter.getDevices}
 };

 // the store that holds the records for the event grid
 var eventStore = {
     xtype: 'EventStore',
     autoLoad: {params:{id: 'Processes'}},
     // Ext.data.DirectProxy config
     api: {read: Zenoss.remote.ProcessRouter.getEvents}
 };

Ext.getCmp('bottom_detail_panel').add({
    xtype: 'DeviceEventPanel',
    __device_store__: deviceStore,
    __event_store__: eventStore,
    getSelectedNode: function() {
        var processTree = Ext.getCmp('processTree');
        var selectionModel = processTree.getSelectionModel();
        return selectionModel.getSelectedNode();
    }
});


}); // Ext.onReady

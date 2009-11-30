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
    
} // clickHandler

Ext.getCmp('master_panel').add({
    xtype: 'HierarchyTreePanel',
    id: 'processTree',
    searchField: true,
    directFn: Zenoss.remote.ProcessRouter.getProcessTree,
    root: 'Processes',
    listeners: {click: clickHandler}
}); // master_panel.add


/* **************************************************************************
 *
 *   top_detail_panel - the process form on the top right
 *
 */


// disable the monitoring fields if monitoring settings are acquired
function  setMonitoringDisabled(disabled) {
    var monitorCheckbox = Ext.getCmp('monitorCheckbox');
    var eventSeverityCombo = Ext.getCmp('eventSeverityCombo');
    monitorCheckbox.setDisabled(disabled);
    eventSeverityCombo.setDisabled(disabled);
}

function acquiredCheckboxHandler(checkbox, checked) {
    setMonitoringDisabled(checked);
    var router = Zenoss.remote.ProcessRouter;
    var processTree = Ext.getCmp('processTree');
    var selectionModel = processTree.getSelectionModel();
    var selectedNode = selectionModel.getSelectedNode();

    if (checked) {
        var id = selectedNode.parentNode.id;
    } else {
        var id = selectedNode.id;
    }

    var callback = function(provider, response) {
        var info = response.result.data;
        var monitorCheckbox = Ext.getCmp('monitorCheckbox');
        monitorCheckbox.setValue(info.enabled);
        var eventSeverityCombo = Ext.getCmp('eventSeverityCombo')
        eventSeverityCombo.setValue(info.eventSeverity);
    }
    
    router.getMonitoringInfo({id: id}, callback);
}

// when the form loads, show/hide the regex fieldset
function actioncompleteHandler(form, action) {
    if (action.type == 'directload') {
        var processInfo = action.result.data;
        var regexFieldSet = Ext.getCmp('regexFieldSet');
        var acquiredCheckbox = Ext.getCmp('acquiredCheckbox');
        regexFieldSet.setVisible(processInfo.hasRegex);
        regexFieldSet.doLayout();
        acquiredCheckbox.setDisabled(processInfo.name == 'Processes');
        setMonitoringDisabled(processInfo.isMonitoringAcquired);
    }
}

var nameTextField = {
    xtype: 'textfield',
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

var regexTextField = {
    xtype: 'textfield',
    fieldLabel: _t('Pattern'),
    name: 'regex',
    width: "100%"
};

var ignoreParametersCheckbox = {
    xtype: 'checkbox',
    fieldLabel: _t('Ignore Parameters'),
    name: 'ignoreParameters'
};

var monitoringFieldSet = {
    xtype: 'ColumnFieldSet',
    title: _t('Monitoring'),
    __innner_items__: [
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
}; // monitoringFieldSet

var regexFieldSet = {
    xtype: 'ColumnFieldSet',
    id: 'regexFieldSet',
    title: _t('Regular Expression'),
    hidden: true,
    __innner_items__: [
        {
            items: regexTextField,
            columnWidth: .6
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
        columnWidth: .5
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
    api: {
        load: Zenoss.remote.ProcessRouter.getProcessInfo,
        submit: Zenoss.remote.ProcessRouter.submitProcessInfo
    }
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


Ext.getCmp('bottom_detail_panel').add(new Zenoss.PlaceholderPanel({
    text: 'Ext.getCmp("bottom_detail_panel"), metal:fill-slot="bottom_detail_panel"'
}));


}); // Ext.onReady

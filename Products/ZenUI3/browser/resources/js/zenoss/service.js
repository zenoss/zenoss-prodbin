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

// Script for the services page.

Ext.onReady(function(){


/* ***************************************************************************
 *
 *   master_panel - the services tree on the left
 *
 */

// function that gets run when the user clicks on a node in the tree
function clickHandler(node) {
    
    // load up appropriate data in the form
    Ext.getCmp('serviceForm').getForm().load({
        params: {id: node.attributes.uid}
    });
    
    // load up appropriate data in the devices grid
//    Ext.getCmp('deviceGrid').getStore().load({
//        params: {id: node.attributes.id}
//    });
    
} // clickHandler

function acquiredCheckboxHandler(checkbox, checked) {
    setMonitoringDisabled(checked);
    var router = Zenoss.remote.ProcessRouter;
    var processTree = Ext.getCmp('processTree');
    var selectionModel = processTree.getSelectionModel();
    var selectedNode = selectionModel.getSelectedNode();

    var uid;
    if (checked && selectedNode.parentNode !== null) {
        uid = selectedNode.parentNode.attributes.uid;
    } else {
        uid = selectedNode.attributes.uid;
    }

    var callback = function(provider, response) {
        var info = response.result.data;
        var monitorCheckbox = Ext.getCmp('monitorCheckbox');
        monitorCheckbox.setValue(info.monitor);
        var eventSeverityCombo = Ext.getCmp('eventSeverityCombo');
        eventSeverityCombo.setValue(info.eventSeverity);
    };
    
    router.getInfo({uid: uid, keys: ['monitor', 'eventSeverity']}, callback);
}



Ext.getCmp('master_panel').add({
    xtype: 'HierarchyTreePanel',
    id: 'serviceTree',
    searchField: true,
    autoScroll: true,
    directFn: Zenoss.remote.ServiceRouter.getTree,
    root: 'Services',
    listeners: {click: clickHandler}
}); // master_panel.add


/* **************************************************************************
 *
 *   top_detail_panel - the service form on the top right
 *
 */

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

var serviceKeysTextField = {
    xtype: 'textfield',
    fieldLabel: _t('Service Keys'),
    name: 'serviceKeys',
    width: "100%"
};
     
var portTextField = {
    xtype: 'textfield',
    fieldLabel: _t('Port'),
    name: 'port',
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


// the items that make up the form
var serviceFormItems = {
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
        {items: [nameTextField, descriptionTextField ]},
        {items: [serviceKeysTextField, portTextField ]},
        {items: [monitoringFieldSet]}
    ]
}; // serviceFormItems

var serviceFormConfig = {
    xtype: 'form',
    id: 'serviceForm',
    paramsAsHash: true,
    items: serviceFormItems,
    border: false,
    labelAlign: 'top',
    autoScroll: true,
    api: {
        load: Zenoss.remote.ServiceRouter.getInfo,
        submit: Zenoss.remote.ServiceRouter.submitInfo
    },
    tbar: [
       {
           xtype: 'tbfill'
       }, {
           xtype: 'button',
           text: _t('Save'),
           width: 80,
           handler: function(button, event) {} 
               /*function(button, event) {
               var processTree = Ext.getCmp('processTree');
               var selectionModel = processTree.getSelectionModel();
               var selectedNode = selectionModel.getSelectedNode();
               var nameTextField = Ext.getCmp('nameTextField');
               selectedNode.attributes.text.text = nameTextField.getValue();
               selectedNode.setText(selectedNode.attributes.text);
               var form = Ext.getCmp('processForm').getForm();
               var params = Ext.apply({id: selectedNode.id}, form.getValues());
               form.api.submit(params);
           }*/
       }
       ] //tbar

};

Ext.ns('Zenoss');

/**
 * @class Zenoss.ServiceFormPanel
 * @extends Ext.form.FormPanel
 * The form panel that displays information about a service organizer or class
 * @constructor
 */
Zenoss.ServiceFormPanel = Ext.extend(Ext.form.FormPanel, {

    constructor: function(userConfig) {
        var config = Ext.apply(serviceFormConfig, userConfig);
        Zenoss.ServiceFormPanel.superclass.constructor.call(this, config);
        //this.on('actioncomplete', actioncompleteHandler);
    }

});

Ext.reg('ServiceFormPanel', Zenoss.ServiceFormPanel);

var serviceForm = new Zenoss.ServiceFormPanel({});

// place the form in the top right
Ext.getCmp('top_detail_panel').add(serviceForm);

serviceForm.getForm().load({params:{id: 'Services'}});


/* ***********************************************************************
 *
 *   bottom_detail_panel - the device and event grid on the bottom right
 *
 */

//the store that holds the records for the device grid
var deviceStore = {
    xtype: 'DeviceStore',
    autoLoad: {params:{id: 'Services'}},
    // Ext.data.DirectProxy config
    api: {read: Zenoss.remote.ServiceRouter.getDevices}
};

// the store that holds the records for the event grid
var eventStore = {
    xtype: 'EventStore',
    autoLoad: {params:{id: 'Services'}},
    // Ext.data.DirectProxy config
    api: {read: Zenoss.remote.ServiceRouter.getEvents}
};



Ext.getCmp('bottom_detail_panel').add({
    xtype: 'DeviceEventPanel',
    __device_store__: deviceStore,
    __event_store__: eventStore,
    getSelectedNode: function() {
        var serviceTree = Ext.getCmp('serviceTree');
        var selectionModel = serviceTree.getSelectionModel();
        return selectionModel.getSelectedNode();
    }
});


}); // Ext.onReady

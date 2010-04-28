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

Ext.ns('Zenoss', 'Zenoss.env');
var treeId = 'processTree';
var router = Zenoss.remote.ProcessRouter;

new Zenoss.MessageDialog({
    id: 'dirtyDialog',
    title: _t('Unsaved Data'),
    message: _t('The changes made in the form will be lost.'),
    okHandler: function() {
        Ext.getCmp('processForm').getForm().reset();
        Zenoss.env.node.select();
    }
});

/* ***************************************************************************
 *
 *   master_panel - the processes tree on the left
 *
 */

function beforeselectHandler(sm, node, oldNode) {
    if (node == oldNode) {
        return false;
    }
    if ( Ext.getCmp('processForm').getForm().isDirty() ) {
        // the user made changes to the form make sure that they don't care
        // about losing those changes
        Zenoss.env.node = node;
        Ext.getCmp('dirtyDialog').show();
        return false;
    }
    return true;
}

// function that gets run when the user clicks on a node in the tree
function selectionchangeHandler(sm, node) {
    if (node) {
        // load up appropriate data in the form
        var uid = node.attributes.uid;
        Ext.getCmp('processForm').setContext(uid);
        Ext.getCmp('instancesGrid').setContext(uid);
        Ext.getCmp('footer_bar').setContext(uid);
        // don't allow the user to delete the root node
        Ext.getCmp('footer_bar').buttonDelete.setDisabled(
                node == Ext.getCmp(treeId).root);
    }
}

var selModel = new Ext.tree.DefaultSelectionModel({
    listeners: {
        beforeselect: beforeselectHandler,
        selectionchange: selectionchangeHandler
    }
});

var MoveProcessCallback = Ext.extend(Object, {
    constructor: function(tree, node) {
        this.tree = tree;
        this.node = node;
        MoveProcessCallback.superclass.constructor.call(this);
    },
    call: function(provider, response) {
        this.node.setId(response.result.id);
        this.node.attributes.uid = response.result.uid;
        this.tree.selectPath(this.node.getPath());
        Ext.History.add(this.tree.id + Ext.History.DELIMITER + this.node.id);
    }
});

var ProcessTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            id: treeId,
            searchField: true,
            directFn: router.getTree,
            router: router,
            selModel: selModel,
            enableDD: true,
            dropConfig: {
                appendOnly: true
            },
            listeners: {
                nodedrop: {
                    fn: this.onNodeDrop,
                    scope: this
                }
            },
            root: {
                id: 'Processes',
                uid: '/zport/dmd/Processes'
            }
        });
        ProcessTreePanel.superclass.constructor.call(this, config);
    },
    onNodeDrop: function(dropEvent) {
        var node, uid, target, targetUid, params, callback;
        node = dropEvent.dropNode;
        uid = node.attributes.uid;
        target = dropEvent.target;
        target.expand();
        targetUid = target.attributes.uid;
        params = {uid: uid, targetUid: targetUid};
        callback = new MoveProcessCallback(this, node);
        router.moveProcess(params, callback.call, callback);
    }
});

Ext.getCmp('master_panel').add( new ProcessTreePanel({}) );


/* **************************************************************************
 *
 *   top_detail_panel - the process form on the top right
 *
 */


// disable the monitoring fields if monitoring settings are inherited
function setMonitoringDisabled(disabled) {
    Ext.getCmp('monitorCheckbox').setDisabled(disabled);
    Ext.getCmp('alertOnRestartCheckBox').setDisabled(disabled);
    Ext.getCmp('eventSeverityCombo').setDisabled(disabled);
}

function inheritedCheckboxHandler(checkbox, checked) {
    if ( Ext.getCmp('processForm').isLoadInProgress ) {
        return;
    }
    setMonitoringDisabled(checked);
    var processTree = Ext.getCmp(treeId);
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
        Ext.getCmp('monitorCheckbox').setValue(info.monitor);
        Ext.getCmp('alertOnRestartCheckBox').setValue(info.alertOnRestart);
        Ext.getCmp('eventSeverityCombo').setValue(info.eventSeverity);
    };

    router.getInfo({uid: uid, keys: ['monitor', 'eventSeverity']}, callback);
}

// when the form loads, show/hide the regex fieldset
function actioncompleteHandler(form, action) {
    if (action.type == 'directload') {
        Ext.getCmp('processForm').isLoadInProgress = false;
        var processInfo = action.result.data;
        // disabling the forms will disable all of the elements in it
        Ext.getCmp('processForm').setDisabled(Zenoss.Security.doesNotHavePermission('Manage DMD'));
        var isRoot = processInfo.name == 'Processes';
        Ext.getCmp('nameTextField').setDisabled(isRoot);
        Ext.getCmp('inheritedCheckbox').setDisabled(isRoot);
        setMonitoringDisabled(processInfo.isMonitoringAcquired);
        var regexFieldSet = Ext.getCmp('regexFieldSet');
        regexFieldSet.setVisible(processInfo.hasRegex);
        regexFieldSet.doLayout();
    } else if (action.type == 'zsubmit') {
        var processTree = Ext.getCmp(treeId);
        var selectionModel = processTree.getSelectionModel();
        var selectedNode = selectionModel.getSelectedNode();
        var nameTextField = Ext.getCmp('nameTextField');

        selectedNode.attributes.text.text = nameTextField.getValue();
        selectedNode.setText(selectedNode.attributes.text);
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
    xtype: 'textarea',
    fieldLabel: _t('Description'),
    name: 'description',
    width: "100%",
    grow: true
};

var inheritedCheckbox = {
    xtype: 'checkbox',
    id: 'inheritedCheckbox',
    fieldLabel: _t('Inherited'),
    name: 'isMonitoringAcquired',
    handler: inheritedCheckboxHandler,
    submitValue: true
};

var monitorCheckbox = {
    xtype: 'checkbox',
    id: 'monitorCheckbox',
    fieldLabel: _t('Enabled'),
    name: 'monitor',
    submitValue: true
};

var alertOnRestartCheckBox = {
    xtype: 'checkbox',
    id: 'alertOnRestartCheckBox',
    fieldLabel: _t('Alert on Restart'),
    name: 'alertOnRestart',
    submitValue: true
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
    id: 'regexTextField',
    fieldLabel: _t('Pattern'),
    name: 'regex',
    width: "100%"
};

var ignoreParametersCheckbox = {
    xtype: 'checkbox',
    id: 'ignoreParametersCheckbox',
    fieldLabel: _t('Ignore Parameters'),
    name: 'ignoreParameters',
    submitValue: true
};

var monitoringFieldSet = {
    xtype: 'ColumnFieldSet',
    title: _t('Monitoring'),
    __inner_items__: [
    {
        items: inheritedCheckbox
    }, {
        items: monitorCheckbox
    }, {
        items: alertOnRestartCheckBox
    }, {
        items: eventSeverityCombo
    }]
}; // monitoringFieldSet

var regexFieldSet = {
    xtype: 'ColumnFieldSet',
    id: 'regexFieldSet',
    title: _t('Regular Expression'),
    hidden: true,
    __inner_items__: [
        {
            items: regexTextField
        }, {
            items: ignoreParametersCheckbox
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
        {items: [nameTextField, descriptionTextField]},
        {items: [monitoringFieldSet, regexFieldSet]}
    ]
}; // processFormItems

var processFormConfig = {
    xtype: 'basedetailform',
    trackResetOnLoad: true,
    id: 'processForm',
    region: 'center',
    items: processFormItems,
    api: {
        load: router.getInfo,
        submit: router.setInfo
    }
};

// place the form in the top right
var processForm = Ext.create(processFormConfig);

Ext.getCmp('detail_panel').add(processForm);
processForm.on('actioncomplete', actioncompleteHandler);

/* ***********************************************************************
 *
 *   bottom_detail_panel - the device and event grid on the bottom right
 *
 */
Ext.getCmp('detail_panel').add({
    xtype: 'SimpleInstanceGridPanel',
    region: 'south',
    id: 'instancesGrid',
    directFn: router.getInstances,
    tbar: {
        xtype: 'consolebar',
        title: 'Process Instances'
    }
});

var ContextGetter = Ext.extend(Object, {
    getUid: function() {
        var selected = Ext.getCmp('processTree').getSelectionModel().getSelectedNode();
        if ( ! selected ) {
            Ext.Msg.alert(_t('Error'), _t('You must select a process.'));
            return null;
        }
        return selected.attributes.uid;
    },
    hasTwoControls: function() {
        return false;
    }
});

/* ***********************************************************************
 *
 *   footer_panel - the add/remove tree node buttons at the bottom
 *
 */
function dispatcher(actionName, value) {
    var tree = Ext.getCmp(treeId);
    switch (actionName) {
        case 'addClass': tree.addNode('class', value); break;
        case 'addOrganizer': tree.addNode('organizer', value); break;
        case 'delete': tree.deleteSelectedNode(); break;
        default: break;
    }
};

var footer = Ext.getCmp('footer_bar');
Zenoss.footerHelper('Process', footer, {contextGetter: new ContextGetter()});
footer.on('buttonClick', dispatcher);
footer.buttonDelete.setDisabled(true);

Zenoss.SequenceGrid = Ext.extend(Zenoss.BaseSequenceGrid, {
    constructor: function(config) {
        Ext.applyIf(config, {
            stripeRows: true,
            autoScroll: true,
            border: false,
            layout: 'fit',
            viewConfig: {forceFit: true},
            store: {
                xtype: 'directstore',
                root: 'data',
                autoSave: false,
                idProperty: 'uid',
                directFn: router.getSequence,
                fields: ['uid', 'folder', 'name', 'regex', 'monitor', 'count']
            },
            columns: [
                {dataIndex: 'folder', header: 'Folder'},
                {dataIndex: 'name', header: 'Name'},
                {dataIndex: 'regex', header: 'Regex'},
                {dataIndex: 'monitor', header: 'Monitor'},
                {dataIndex: 'count', header: 'Count'}
            ]
        });
        Zenoss.SequenceGrid.superclass.constructor.call(this, config);
    }
});
Ext.reg('sequencegrid', Zenoss.SequenceGrid);

Ext.getCmp('footer_bar').buttonContextMenu.menu.addItem({
    id: 'sequenceButton',
    iconCls: 'set',
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    tooltip: 'Sequence the process classes',
    text: _t('Change Sequence'),
    handler: function(button, event) {
        if ( ! Ext.getCmp('sequenceDialog') ) {
            new Zenoss.HideFitDialog({
                id: 'sequenceDialog',
                title: _t('Sequence'),
                items: [
                {
                    xtype: 'sequencegrid',
                    id: 'sequenceGrid'
                }],
                buttons: [{
                    xtype: 'HideDialogButton',
                    text: _t('Submit'),
                    handler: function(button, event) {
                        var records, uids;
                        records = Ext.getCmp('sequenceGrid').getStore().getRange();
                        uids = Ext.pluck(records, 'id');
                        router.setSequence({'uids': uids});
                    }
                 }, {
                    xtype: 'HideDialogButton',
                    text: _t('Cancel')
                }]
            });
        }
        Ext.getCmp('sequenceGrid').getStore().load();
        Ext.getCmp('sequenceDialog').show();
    }
});

}); // Ext.onReady

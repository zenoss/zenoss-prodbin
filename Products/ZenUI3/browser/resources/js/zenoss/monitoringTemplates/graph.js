/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


(function(){

var router, getSelectedTemplate, getSelectedGraphDefinition,
    addGraphDefinition, deleteGraphDefinition, addThresholdToGraph;


Ext.ns('Zenoss', 'Zenoss.templates');

router = Zenoss.remote.TemplateRouter;

getSelectedTemplate = function() {
    return Ext.getCmp('templateTree').getSelectionModel().getSelectedNode();
};

getSelectedGraphDefinition = function() {
    return Ext.getCmp('graphGrid').getSelectionModel().getSelected();
};

function getSelectedGraphPoint() {
    var cmp = Ext.getCmp('graphPointGrid');
    if (cmp) {
        return cmp.getSelectionModel().getSelected();
    }
    return null;
}



deleteGraphDefinition = function() {
    var params, callback;
    params = {
        uid: getSelectedGraphDefinition().get("uid")
    };
    callback = function(provider, response) {
        Ext.getCmp('deleteGraphDefinitionButton').disable();
        Ext.getCmp('graphDefinitionMenuButton').disable();
        Ext.getCmp('graphGrid').refresh();
    };
    router.deleteGraphDefinition(params, callback);
};


new Zenoss.MessageDialog({
    id: 'deleteGraphDefinitionDialog',
    title: _t('Delete Graph Definition'),
    // the message is generated dynamically
    okHandler: function(){
        deleteGraphDefinition();
    }
});

/**
 * Deletes the selected graph point
 **/
function deleteGraphPoint() {
    var params, callback;
    params = {
        uid: getSelectedGraphPoint().get("uid")
    };
    callback = function(provider, response) {
        Ext.getCmp('deleteGraphPointButton').disable();
        Ext.getCmp('editGraphPointButton').disable();
        Ext.getCmp('graphPointGrid').refresh();
    };
    router.deleteGraphPoint(params, callback);
}

new Zenoss.MessageDialog({
    id: 'deleteGraphPointDialog',
    title: _t('Delete Graph Point'),
    // the message is generated dynamically
    okHandler: deleteGraphPoint
});

/**
 * Adds the selected datapoint as a graph point to our
 * graph definition we are managing
 **/
function addDataPointToGraph() {
    var dataPointUid = Ext.getCmp('addDataPointToGraphDialog').comboBox.getValue(),
        graphUid = getSelectedGraphDefinition().get("uid"),
        includeThresholds = Ext.getCmp('addDataPointToGraphDialog').includeRelatedThresholds.getValue(),
        params = {
            dataPointUid: dataPointUid,
            graphUid: graphUid,
            includeThresholds: includeThresholds
        },
        callback = function() {
            Ext.getCmp('graphPointGrid').refresh();
        };
    router.addDataPointToGraph(params, callback);
}

new Zenoss.HideFormDialog({
    id: 'addDataPointToGraphDialog',
    title: _t('Add Data Point'),
    closeAction: 'hide',
    items:[{
        xtype: 'combo',
        ref: 'comboBox',
        getInnerTpl: function() {
            return '<tpl for="."><div ext:qtip="{name}" class="x-combo-list-item">{name}</div></tpl>';
        },
        fieldLabel: _t('Data Point'),
        valueField: 'uid',
        displayField: 'name',
        triggerAction: 'all',
        forceSelection: true,
        editable: false,
        allowBlank: false,
        listeners: {
            validitychange: function(form, isValid){
                var window = Ext.getCmp('addDataPointToGraphDialog');
                if (window.isVisible()){
                    window.submit.setDisabled(!isValid);
                }
            }
        },
        store: Ext.create('Zenoss.NonPaginatedStore', {
            root: 'data',
            model: 'Zenoss.model.Basic',
            directFn: router.getDataPoints
        })
    },{
        xtype: 'checkbox',
        name: 'include_related_thresholds',
        ref: 'includeRelatedThresholds',
        fieldLabel: _t('Include Related Thresholds'),
        checked: true
    }],
    listeners: {
        show: function() {
            var combo, uid;
            combo = Ext.getCmp('addDataPointToGraphDialog').comboBox;
            combo.reset();
            Ext.getCmp('addDataPointToGraphDialog').submit.disable();
            uid = getSelectedTemplate().data.uid;
            combo.store.setContext(uid);
        }
    },
    buttons: [
    {
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        ref: '../submit',
        text: _t('Submit'),
        disabled: true,
        handler: function(button, event) {
            addDataPointToGraph();
        }
    }, {
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        text: _t('Cancel')
    }]

});

addThresholdToGraph = function() {
    var params, callback;
    params = {
        graphUid: getSelectedGraphDefinition().get("uid"),
        thresholdUid: Ext.getCmp('addThresholdToGraphCombo').getValue()
    };
    callback = function() {
        Ext.getCmp('graphPointGrid').refresh();
    };
    router.addThresholdToGraph(params, callback);
};

new Zenoss.HideFormDialog({
    id: 'addThresholdToGraphDialog',
    title: _t('Add Threshold'),
    items: {
        xtype: 'combo',
        id: 'addThresholdToGraphCombo',
        getInnerTpl: function() {
            return '<tpl for="."><div ext:qtip="{name}" class="x-combo-list-item">{name}</div></tpl>';
        },
        fieldLabel: _t('Threshold'),
        valueField: 'uid',
        displayField: 'name',
        triggerAction: 'all',
        forceSelection: true,
        editable: false,
        allowBlank: false,
        listeners: {
            validitychange: function(form, isValid){
                var button = Ext.getCmp('addThresholdToGraphSubmit');
                if (button.isVisible()){
                    button.setDisabled(!isValid);
                }
            }
        },
        store: Ext.create('Zenoss.NonPaginatedStore', {
            root: 'data',
            model: 'Zenoss.model.Basic',
            directFn: router.getThresholds
        })
    },
    listeners: {
        show: function() {
            var combo, uid;
            combo = Ext.getCmp('addThresholdToGraphCombo');
            combo.reset();
            Ext.getCmp('addThresholdToGraphSubmit').disable();
            uid = getSelectedTemplate().data.uid;
            combo.store.setContext(uid);
        }
    },
    buttons: [
    {
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        id: 'addThresholdToGraphSubmit',
        text: _t('Submit'),
        disabled: true,
        handler: function(button, event) {
            addThresholdToGraph();
        }
    }, {
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        text: _t('Cancel')
    }]

});

Ext.define('Zenoss.InstructionTypeModel', {
    extend: 'Ext.data.Model',
    idProperty: 'pythonClassName',
    fields: ['pythonClassName', 'label']
});



new Zenoss.HideFormDialog({
    id: 'addCustomToGraphDialog',
    title: _t('Add Custom Graph Point'),
    listeners: {
        show: function(dialog) {
            dialog.addForm.idField.reset();
            dialog.addForm.typeCombo.reset();
            dialog.addForm.typeCombo.store.load();
        }
    },
    items: [{
        xtype: 'form',
        ref: 'addForm',
        listeners: {
            validitychange: function(formPanel, valid) {
                Ext.getCmp('addCustomToGraphDialog').submitButton.setDisabled( !valid );
            }
        },
        items: [{
            xtype: 'idfield',
            ref: 'idField',
            fieldLabel: _t('Name'),
            allowBlank: false
        }, {
            xtype: 'combo',
            ref: 'typeCombo',
            fieldLabel: _t('Instruction Type'),
            valueField: 'pythonClassName',
            displayField: 'label',
            triggerAction: 'all',
            forceSelection: true,
            editable: false,
            allowBlank: false,
            store: Ext.create('Zenoss.NonPaginatedStore', {
                root: 'data',
                autoLoad: false,
                model: 'Zenoss.InstructionTypeModel',
                directFn: router.getGraphInstructionTypes
            })
        }]
    }],
    buttons: [{
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        disabled: true,
        ref: '../submitButton',
        text: _t('Add'),
        handler: function(addButton) {
            var params, callback, form = Ext.getCmp('addCustomToGraphDialog').addForm;
            params = {
                graphUid: getSelectedGraphDefinition().get("uid"),
                customId: form.idField.getValue(),
                customType: form.typeCombo.getValue()
            };
            callback = function() {
                Ext.getCmp('graphPointGrid').refresh();
            };
            router.addCustomToGraph(params, callback);
        }
    }, {
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        ref: '../cancelButton',
        text: _t('Cancel')
    }]
});

/**********************************************************************
 *
 * Graph Custom Definition
 *
 */
Ext.create('Zenoss.dialog.BaseWindow', {
    title: _t('Graph Custom Definition'),
    id: 'graphCustomDefinitionDialog',
    closeAction: 'hide',
    buttonAlign: 'left',
    autoScroll: true,
    height: 500,
    width: 400,
    modal: true,
    plain: true,
    padding: 10,
    items: [{
        xtype:'form',
        ref: 'formPanel',
        paramsAsHash: true,
        api: {
            load: router.getGraphDefinition,
            submit: router.setInfo
        },
        items:[{
            xtype: 'label',
            fieldLabel: _t('Name'),
            name:'id',
            ref: 'nameLabel'
        },{
            xtype: 'textarea',
            fieldLabel: _t('Custom'),
            width: 300,
            height: 300,
            name: 'custom',
            ref: 'custom'
        },{
            xtype: 'label',
            fieldLabel: _t('Available RRD Variables'),
            ref: 'rrdVariables'
        }]
    }],
    buttons: [{
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        text: _t('Submit'),
        handler: function(button, event) {
            var cmp = Ext.getCmp('graphCustomDefinitionDialog'),
                routerCallback,
                data = cmp.record,
                params = {};

            // we just need to update custom
            params.uid = data.uid;
            params.custom = cmp.formPanel.custom.getValue();

            router.setInfo(params);
        }
    }, {
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        text: _t('Cancel')
    }],
    loadAndShow: function(uid) {
        this.uid = uid;
        this.formPanel.getForm().load({
            params: {uid:uid},
            success: function(btn, response) {
                var data = response.result.data;
                this.record = data;
                // populate the form
                this.formPanel.nameLabel.setText(data.id);
                this.formPanel.custom.setValue(data.custom);
                this.formPanel.rrdVariables.setText(data.rrdVariables.join('<br />'), false);

                this.show();
            },
            scope: this
        });
    }

});

/**
 * @class Zenoss.graph.GraphPointModel
 * @extends Ext.data.Model
 * Field definitions for the Graph Point
 **/
Ext.define('Zenoss.graph.GraphPointModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: ['uid', 'name', 'type', 'description']
});

Ext.define("Zenoss.GraphPointStore", {
    alias:['widget.graphpointstore'],
    extend:"Zenoss.NonPaginatedStore",
    constructor: function(config){
        Ext.applyIf(config, {
            model: 'Zenoss.graph.GraphPointModel',
            directFn: router.getGraphPoints,
            root: 'data'
        });
        this.callParent(arguments);
    }
});


new Ext.menu.Menu({
    id: 'graphPointMenu',
    items: [{
        xtype: 'menuitem',
        text: _t('Data Point'),
        handler: function(){
            Ext.getCmp('addDataPointToGraphDialog').show();
        }
    }, {
        xtype: 'menuitem',
        text: _t('Threshold'),
        handler: function(){
            Ext.getCmp('addThresholdToGraphDialog').show();
        }
    }, {
        xtype: 'menuitem',
        text: _t('Custom Graph Point'),
        handler: function(){
            Ext.getCmp('addCustomToGraphDialog').show();
        }
    }]
});

Ext.define("Zenoss.BaseSequenceGrid", {
    extend:"Ext.grid.GridPanel",
    constructor: function(config){
        Ext.applyIf(config, {
            enableDragDrop   : true,
            viewConfig: {
                forcefit: true,
                plugins: {
                    ptype: 'gridviewdragdrop'
                }
            }
        });
        this.addEvents({'resequence': true});
        Zenoss.BaseSequenceGrid.superclass.constructor.call(this, config);
    }
});

Ext.define("Zenoss.GraphPointGrid", {
    alias:['widget.graphpointgrid'],
    extend:"Zenoss.ContextGridPanel",
    constructor: function(config){
        Ext.applyIf(config, {
            height: 215,
            viewConfig: {
                plugins: {
                    ptype: 'gridviewdragdrop'
                }
            },
            listeners: {
                /**
                 * The selection model was being ignored at this point so I used the
                 * row click.
                 **/
                itemclick: function() {
                    var record = getSelectedGraphPoint();
                    if (record) {
                        Ext.getCmp('deleteGraphPointButton').enable();
                        Ext.getCmp('editGraphPointButton').enable();
                    }else{
                        Ext.getCmp('deleteGraphPointButton').disable();
                        Ext.getCmp('editGraphPointButton').disable();
                    }
                },
                itemdblclick: displayGraphPointForm
            },
            store: Ext.create('Zenoss.GraphPointStore', {}),
            columns: [
                {dataIndex: 'name', header: _t('Name'), width: 150},
                {dataIndex: 'type', header: _t('Type'), width: 150},
                {
                    dataIndex: 'description',
                    header: _t('Description'),
                    id: 'definition_description',
                    flex: 1
                }
            ],
            tbar: [{
                xtype: 'button',
                id: 'addGraphPointButton',
                iconCls: 'add',
                menu: 'graphPointMenu',
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('addGraphPointButton');
                    }
                }
            }, {
                xtype: 'button',
                id: 'deleteGraphPointButton',
                iconCls: 'delete',
                disabled: true,
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('deleteGraphPointButton');
                    }
                },
                handler: function() {
                    var html, dialog;
                    // format the confimation message
                    html = _t("Are you sure you want to remove the graph point, {0}? There is no undo.");
                    html = Ext.String.format(html, getSelectedGraphPoint().data.name);

                    // show the dialog
                    dialog = Ext.getCmp('deleteGraphPointDialog');
                    dialog.setText(html);
                    dialog.show();
                }
            }, {
                xtype: 'button',
                id: 'editGraphPointButton',
                iconCls: 'customize',
                disabled: true,
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('editGraphPointButton');
                    }
                },
                handler: displayGraphPointForm
            }],
            selModel: Ext.create('Zenoss.SingleRowSelectionModel', {})
        });
        this.callParent(arguments);
    }
});


/**********************************************************************
 *
 * Graph Point Edit Dialog/Grid
 *
 */

function reloadGraphPoints() {
    var grid = Ext.getCmp('graphPointGrid');
    grid.refresh();
}

/**
 * Call back function from when a user selects a graph point.
 * This shows yet another dialog for editing a graph point
 **/
function displayGraphPointForm() {
    var record = getSelectedGraphPoint();

    function displayEditDialog(response) {
        var win = Ext.create('Zenoss.form.DataSourceEditDialog', {
            record: response.data,
            items: response.form,
            singleColumn: true,
            width: 400,
            title: _t('Edit Graph Point'),
            directFn: router.setInfo,
            id: 'editGraphPointDialog',
            saveHandler: reloadGraphPoints
        });

        win.show();
    }

    // remote call to get the object details
    router.getInfo({uid: record.get("uid")}, displayEditDialog);
}

new Zenoss.HideFitDialog({
    id: 'manageGraphPointsDialog',
    title: _t('Manage Graph Points'),
    items: [{
        xtype: 'graphpointgrid',
        id: 'graphPointGrid',
        ref: 'graphGrid'
    }],
    buttons: [
    {
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        text: _t('Save'),
        handler: function(){
            if (Zenoss.Security.hasPermission('Manage DMD')) {
                var records, uids;
                records = Ext.getCmp('graphPointGrid').getStore().getRange();
                uids = Ext.Array.pluck(Ext.Array.pluck(records, 'data'), 'uid');
                router.setGraphPointSequence({'uids': uids});
            }
        }
    }, {
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        text: _t('Cancel')
    }]
});

Ext.create('Zenoss.dialog.BaseWindow', {
    layout: 'fit',
    id: 'viewGraphDefinitionDialog',
    title: _t('View and Edit Graph Definition'),
    closeAction: 'hide',
    buttonAlign: 'left',
    autoScroll: true,
    plain: true,
    modal: true,
    width: 400,
    height: 500,
    padding: 10,
    buttons: [{
        ref: '../submitButton',
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        text: _t('Submit'),
        disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
        handler: function(submitButton){
            var dialogWindow, basicForm, params;
            dialogWindow = submitButton.refOwner;
            basicForm = dialogWindow.formPanel.getForm();
            params = Ext.applyIf(basicForm.getValues(), {
                uid: dialogWindow.uid,
                hasSummary: false,
                log: false,
                base: false
            });
            basicForm.api.submit(params, function() {
                Ext.getCmp('graphGrid').refresh();
            });
        }
    },{
        xtype: 'HideDialogButton',
        ref: '../cancelButton',
        ui: 'dialog-dark',
        text: 'Cancel'
    }],
    items: {
        xtype: 'form',
        ref: 'formPanel',
        autoScroll: true,
        paramsAsHash: true,
        api: {
            load: router.getGraphDefinition,
            submit: router.setGraphDefinition
        },
        listeners: {
            validitychange: function(formPanel, valid){
                var dialogWindow = Ext.getCmp('viewGraphDefinitionDialog');
                if (Zenoss.Security.hasPermission('Manage DMD')) {
                    dialogWindow.submitButton.setDisabled( ! valid );
                }
            },
            show: function(formPanel){
                formPanel.getForm().load();
            }
        },
        items: [{
            xtype: 'idfield',
            fieldLabel: _t('Name'),
            name: 'newId',
            allowBlank: false
        },{
            xtype: 'numberfield',
            fieldLabel: _t('Height'),
            name: 'height',
            minValue: 0
        },{
            xtype: 'numberfield',
            fieldLabel: _t('Width'),
            name: 'width',
            minValue: 0
        },{
            xtype: 'textfield',
            fieldLabel: _t('Units'),
            name: 'units'
        },{
            xtype: 'checkbox',
            fieldLabel: _t('Logarithmic Scale'),
            name: 'log'
        },{
            xtype: 'checkbox',
            fieldLabel: _t('Base 1024'),
            name: 'base'
        },{
            xtype: 'numberfield',
            fieldLabel: _t('Min Y'),
            name: 'miny'
        },{
            xtype: 'numberfield',
            fieldLabel: _t('Max Y'),
            name: 'maxy'
        },{
            xtype: 'checkbox',
            fieldLabel: _t('Has Summary'),
            name: 'hasSummary'
        }]
    },
    loadAndShow: function(uid) {
        this.uid = uid;
        this.formPanel.getForm().load({
            params: {uid:uid},
            success: function() {
                this.show();
            },
            scope: this
        });
    }
});

new Ext.menu.Menu({
    id: 'graphDefinitionMenu',
    items: [{
        xtype: 'menuitem',
        text: _t('Manage Graph Points'),
        handler: function(){
            var uid, grid;
            uid = getSelectedGraphDefinition().get("uid");
            Ext.getCmp('manageGraphPointsDialog').show();
            grid = Ext.getCmp('graphPointGrid');
            grid.setContext(uid);
        }
    }, {
        xtype: 'menuitem',
        text: _t('View and Edit Details'),
        handler: function(){
            var dialogWindow, uid;
            dialogWindow = Ext.getCmp('viewGraphDefinitionDialog');
            uid = getSelectedGraphDefinition().get("uid");
            dialogWindow.loadAndShow(uid);
        }
    },{
        xtype: 'menuitem',
        text: _t('Custom Graph Definition'),
        handler: function () {
            var win = Ext.getCmp('graphCustomDefinitionDialog'),
                uid = getSelectedGraphDefinition().get("uid");
            win.loadAndShow(uid);
        }
    },{
        xtype: 'menuitem',
        text: _t('Graph Commands'),
        handler: function () {
            var params = {
                uid: getSelectedGraphDefinition().get("uid")
            };

            router.getGraphDefinition(params, function (response) {
                Ext.MessageBox.show({
                    title: _t('Graph Commands'),
                    minWidth: 700,
                    msg: Ext.String.format('<pre>{0}</pre>', response.data.fakeGraphCommands),
                    buttons: Ext.MessageBox.OK
                });
            });
        }
    }]
});

Ext.define("Zenoss.templates.GraphGrid", {
    alias:['widget.graphgrid'],
    extend:"Zenoss.ContextGridPanel",
    constructor: function(config) {
        var me = this;
        Ext.applyIf(config, {
            title: _t('Graph Definitions'),
            store: Ext.create('Zenoss.GraphStore', {}),
            enableDragDrop   : true,
            viewConfig: {
                forcefit: true,
                plugins: {
                    ptype: 'gridviewdragdrop'
                },
                listeners: {
                    /**
                     * Updates the graph order when the user drags and drops them
                     **/
                    drop: function() {
                        var records, uids;
                        records = me.store.getRange();
                        uids = Ext.pluck(Ext.pluck(records, 'data'), 'uid');
                        router.setGraphDefinitionSequence({'uids': uids});
                    }
                }
            },
            listeners: {
                /**
                 * Double click to edit a graph definition
                 **/
                itemdblclick: function()  {
                    var dialogWindow, uid;
                    dialogWindow = Ext.getCmp('viewGraphDefinitionDialog');
                    uid = getSelectedGraphDefinition().get("uid");
                    dialogWindow.loadAndShow(uid);
                }

            },
            selModel: new Zenoss.SingleRowSelectionModel({
             listeners: {
                    select: function() {
                        if (Zenoss.Security.hasPermission('Manage DMD')){
                            Ext.getCmp('deleteGraphDefinitionButton').enable();
                            Ext.getCmp('graphDefinitionMenuButton').enable();
                        }
                    }
                }
            }),
            columns: [{dataIndex: 'name', header: _t('Name'), flex:1, width: 400}],

            tbar: [{
                id: 'addGraphDefinitionButton',
                xtype: 'button',
                iconCls: 'add',
                ref: '../addButton',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('addGraphDefinitionButton');
                    }
                },
                handler: function() {
                    var dialog = Ext.create('Zenoss.dialog.BaseWindow', {
                        title: _t('Add Graph Definition'),
                        buttonAlign: 'left',
                        autoScroll: true,
                        plain: true,
                        width: 300,
                        autoHeight: true,
                        modal: true,
                        padding: 10,
                        items: [{
                            xtype: 'form',
                            listeners: {
                                validitychange: function(formPanel, valid) {
                                    dialog.submitButton.setDisabled( !valid );
                                }
                            },
                            items: [
                                {
                                    xtype: 'idfield',
                                    id: 'graphDefinitionIdTextfield',
                                    fieldLabel: _t('Name'),
                                    allowBlank: false
                                }
                            ]

                        }],
                        buttons: [
                            {
                                xtype: 'DialogButton',
                                ref: '../submitButton',
                                disabled: true,
                                text: _t('Submit'),
                                handler: function() {
                                    var params, callback;
                                    params = {
                                        templateUid: getSelectedTemplate().data.uid,
                                        graphDefinitionId: Ext.getCmp('graphDefinitionIdTextfield').getValue()
                                    };
                                    callback = function(provider, response) {
                                        Ext.getCmp('graphGrid').refresh();
                                    };

                                    router.addGraphDefinition(params, callback);
                                }
                            }, {
                                xtype: 'DialogButton',
                                text: _t('Cancel')
                            }]
                    });
                    dialog.show();
                }
            }, {
                id: 'deleteGraphDefinitionButton',
                xtype: 'button',
                iconCls: 'delete',
                disabled: true,
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('deleteGraphDefinitionButton');
                    }
                },
                handler: function() {
                    var msg, name, html, dialog;
                    msg = _t("Are you sure you want to remove {0}? There is no undo.");
                    name = getSelectedGraphDefinition().data.name;
                    html = Ext.String.format(msg, name);
                    dialog = Ext.getCmp('deleteGraphDefinitionDialog');
                    dialog.setText(html);
                    dialog.show();
                }
            }, {
                id: 'graphDefinitionMenuButton',
                xtype: 'button',
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('graphDefinitionMenuButton');
                    }
                },
                iconCls: 'customize',
                menu: 'graphDefinitionMenu',
                disabled: true
            }]
        });
        this.callParent(arguments);
    }
});


})();

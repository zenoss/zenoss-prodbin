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

addGraphDefinition = function(){
    var templateSelectionModel, params, callback;
    templateSelectionModel = Ext.getCmp('templateTree').getSelectionModel();
    params = {
        templateUid: templateSelectionModel.getSelectedNode().attributes.uid,
        graphDefinitionId: Ext.getCmp('graphDefinitionIdTextfield').getValue()
    };
    callback = function(provider, response) {
        Ext.getCmp('graphGrid').getStore().reload();
    };
    router.addGraphDefinition(params, callback);
};

new Zenoss.HideFormDialog({
    id: 'addGraphDefinitionDialog',
    title: _t('Add Graph Definition'),
    items: [
        {
            xtype: 'textfield',
            id: 'graphDefinitionIdTextfield',
            fieldLabel: _t('ID'),
            allowBlank: false,
            listeners: {
                invalid: function(){
                    Ext.getCmp('addGraphDefinitionSubmit').disable();
                },
                valid: function(){
                    Ext.getCmp('addGraphDefinitionSubmit').enable();
                }
            }
        }
    ],
    listeners: {
        hide: function() {
            Ext.getCmp('graphDefinitionIdTextfield').reset();
        }
    },
    buttons: [
    {
        xtype: 'HideDialogButton',
        id: 'addGraphDefinitionSubmit',
        text: _t('Submit'),
        disabled: true,
        handler: function(button, event) {
            addGraphDefinition();
        }
    }, {
        xtype: 'HideDialogButton',
        text: _t('Cancel')
    }]
});

deleteGraphDefinition = function() {
    var params, callback;
    params = {
        uid: getSelectedGraphDefinition().id
    };
    callback = function(provider, response) {
        Ext.getCmp('deleteGraphDefinitionButton').disable();
        Ext.getCmp('graphDefinitionMenuButton').disable();
        Ext.getCmp('graphGrid').getStore().reload();
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

new Zenoss.MessageDialog({
    id: 'addDataPointToGraphDialog',
    title: _t('Add Data Point'),
    message: 'Not implemented yet.'
});

addThresholdToGraph = function() {
    var params, callback;
    params = {
        graphUid: getSelectedGraphDefinition().id,
        thresholdUid: Ext.getCmp('addThresholdToGraphCombo').getValue()
    };
    callback = function() {
        Ext.getCmp('graphPointGrid').getStore().reload();
    };
    router.addThresholdToGraph(params, callback);
};

new Zenoss.HideFormDialog({
    id: 'addThresholdToGraphDialog',
    title: _t('Add Threshold'),
    items: {
        xtype: 'combo',
        id: 'addThresholdToGraphCombo',
        fieldLabel: _t('Threshold'),
        valueField: 'uid',
        displayField: 'name',
        triggerAction: 'all',
        selectOnFocus: true,
        forceSelection: true,
        editable: false,
        allowBlank: false,
        listeners: {
            invalid: function(){
                Ext.getCmp('addThresholdToGraphSubmit').disable();
            },
            valid: function(){
                Ext.getCmp('addThresholdToGraphSubmit').enable();
            }
        },
        store: {
            xtype: 'directstore',
            directFn: router.getThresholds,
            fields: ['uid', 'name']
        }
    },
    listeners: {
        show: function() {
            var combo, uid;
            combo = Ext.getCmp('addThresholdToGraphCombo');
            combo.reset();
            Ext.getCmp('addThresholdToGraphSubmit').disable();
            uid = getSelectedTemplate().attributes.uid;
            combo.getStore().setBaseParam('uid', uid);
            delete combo.lastQuery;
            combo.doQuery(combo.allQuery, true);
        }
    },
    buttons: [
    {
        xtype: 'HideDialogButton',
        id: 'addThresholdToGraphSubmit',
        text: _t('Submit'),
        disabled: true,
        handler: function(button, event) {
            addThresholdToGraph();
        }
    }, {
        xtype: 'HideDialogButton',
        text: _t('Cancel')
    }]
    
});

new Zenoss.MessageDialog({
    id: 'addCustomToGraphDialog',
    title: _t('Add Custom Graph Point'),
    message: 'Not implemented yet.'
});


Zenoss.GraphPointStore = Ext.extend(Ext.data.DirectStore, {
    constructor: function(config){
        Ext.applyIf(config, {
            directFn: router.getGraphPoints,
            idProperty: 'uid',
            fields: ['uid', 'name', 'type', 'description'],
            root: 'data'
        });
        Zenoss.GraphPointStore.superclass.constructor.call(this, config);
    }
});
Ext.reg('graphpointstore', Zenoss.GraphPointStore);

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

Zenoss.BaseSequenceGrid = Ext.extend(Ext.grid.GridPanel, {
    constructor: function(config){
        Ext.applyIf(config, {
            enableDragDrop: Zenoss.Security.hasPermission('Manage DMD'),
            ddGroup: 'sequenceDDGroup'
        });
        Zenoss.BaseSequenceGrid.superclass.constructor.call(this, config);
    },
    onRender: function() {
        Zenoss.BaseSequenceGrid.superclass.onRender.apply(this, arguments);
        var grid, store;
        grid = this;
        store = this.getStore();
        this.dropZone = new Ext.dd.DropZone(this.view.scroller.dom, {
            ddGroup: 'sequenceDDGroup',
            onContainerOver: function(source, event, data) {
                return this.dropAllowed;
            },
            notifyDrop: function(source, event, data) {
                var sm, rows, cindex, i, rowData;
                sm = grid.getSelectionModel();
                rows = sm.getSelections();
                cindex = source.getDragData(event).rowIndex;
                if (typeof cindex != "undefined") {
                    for (i = 0; i < rows.length; i++) {
                        rowData = store.getById(rows[i].id);
                        store.remove(store.getById(rows[i].id));
                        store.insert(cindex, rowData);
                    }
                    sm.selectRecords(rows);
                }
            }
        });
    }
});

Zenoss.GraphPointGrid = Ext.extend(Zenoss.BaseSequenceGrid, {
    constructor: function(config){
        Ext.applyIf(config, {
            stripeRows: true,
            autoScroll: true,
            border: false,
            autoExpandColumn: 'description',
            store: {xtype: 'graphpointstore'},
            columns: [
                {dataIndex: 'name', header: _t('Name'), width: 150},
                {dataIndex: 'type', header: _t('Type'), width: 150},
                {dataIndex: 'description', header: _t('Description'), id: 'description'}
            ],
            tbar: [{
                xtype: 'button',
                id: 'addGraphPointButton',
                iconCls: 'add',
                tooltip: _t('Add Graph Point'),
                menu: 'graphPointMenu'
            }, {
                xtype: 'button',
                id: 'deleteGraphPointButton',
                iconCls: 'delete',
                tooltip: _t('Delete Graph Point'),
                disabled: true,
                handler: function() {
                    Ext.getCmp('deleteGraphPointDialog').show();
                }
            }]
        });
        Zenoss.GraphPointGrid.superclass.constructor.call(this, config);
    }
});
Ext.reg('graphpointgrid', Zenoss.GraphPointGrid);

new Zenoss.HideFitDialog({
    id: 'manageGraphPointsDialog',
    title: _t('Manage Graph Points'),
    items: [{
        xtype: 'graphpointgrid',
        id: 'graphPointGrid'
    }],
    buttons: [
    {
        xtype: 'HideDialogButton',
        text: _t('Save'),
        handler: function(){
            if (Zenoss.Security.hasPermission('Manage DMD')) {
                var records, uids;
                records = Ext.getCmp('graphPointGrid').getStore().getRange();
                uids = Ext.pluck(records, 'id');
                router.setGraphPointSequence({'uids': uids});
            }
        }
    }, {
        xtype: 'HideDialogButton',
        text: _t('Cancel')
    }]
});

new Zenoss.MessageDialog({
    id: 'viewGraphDefinitionDialog',
    title: _t('View and Edit Graph Definition'),
    message: 'This will allow the user to edit 9 fields that show up in the old UI.'
});

new Ext.menu.Menu({
    id: 'graphDefinitionMenu',
    items: [{
        xtype: 'menuitem',
        text: _t('Manage Graph Points'),
        handler: function(){
            var uid, store;
            uid = getSelectedGraphDefinition().id;
            Ext.getCmp('manageGraphPointsDialog').show();
            store = Ext.getCmp('graphPointGrid').getStore();
            store.setBaseParam('uid', uid);
            store.load();
        }
    }, {
        xtype: 'menuitem',
        text: _t('View and Edit Details'),
        handler: function(){
            Ext.getCmp('viewGraphDefinitionDialog').show();
        }
    }]
});

Zenoss.templates.GraphGrid = Ext.extend(Ext.grid.GridPanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            title: _t('Graph Definitions'),
            store: {xtype: 'graphstore'},
            selModel: new Ext.grid.RowSelectionModel({
                singleSelect: true,
                listeners: {
                    rowdeselect: function() {
                        Ext.getCmp('deleteGraphDefinitionButton').disable();
                        Ext.getCmp('graphDefinitionMenuButton').disable();
                    },
                    rowselect: function() {
                        Ext.getCmp('deleteGraphDefinitionButton').enable();
                        Ext.getCmp('graphDefinitionMenuButton').enable();
                    }
                }
            }),
            colModel: new Ext.grid.ColumnModel({
                columns: [
                    {dataIndex: 'name', header: _t('Name'), width: 400}                    
                ]
            }),
            tbar: [{
                id: 'addGraphDefinitionButton',
                xtype: 'button',
                iconCls: 'add',
                tooltip: _t('Add Graph Definition'),
                handler: function() {
                    Ext.getCmp('addGraphDefinitionDialog').show();
                }
            }, {
                id: 'deleteGraphDefinitionButton',
                xtype: 'button',
                iconCls: 'delete',
                tooltip: _t('Delete Graph Definition'),
                disabled: true,
                handler: function() {
                    var msg, name, html, dialog;
                    msg = _t("Are you sure you want to remove {0}? There is no undo.");
                    name = getSelectedGraphDefinition().data.name;
                    html = String.format(msg, name);
                    dialog = Ext.getCmp('deleteGraphDefinitionDialog');
                    dialog.show();
                    dialog.getComponent('message').update(html);
                }
            }, {
                id: 'graphDefinitionMenuButton',
                xtype: 'button',
                iconCls: 'customize',
                menu: 'graphDefinitionMenu',
                disabled: true
            }]
        });
        Zenoss.templates.GraphGrid.superclass.constructor.call(this, config);
    }
});
Ext.reg('graphgrid', Zenoss.templates.GraphGrid);

})();

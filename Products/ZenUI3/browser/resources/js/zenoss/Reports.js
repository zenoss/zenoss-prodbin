/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.ns('Zenoss.ui.Reports');

Ext.onReady(function () {

var report_panel = new Zenoss.BackCompatPanel({}),
    treesm,
    REPORT_PERMISSION = 'Manage DMD',
    report_tree;

/*
 * Delete a report class
 */
function deleteNode(e) {
    report_tree.deleteSelectedNode();
}

/*
 * add report class to zenpack
 */
function addToZenPack(e) {
    var addtozenpack = new Zenoss.AddToZenPackWindow();
    addtozenpack.setTarget(treesm.getSelectedNode().data.uid);
    addtozenpack.show();
}

function initializeTreeDrop(tree) {

    tree.getView().on('beforedrop', function(element, event, target) {
        if (Zenoss.Security.doesNotHavePermission(REPORT_PERMISSION)) {
            return false;
        }
        // should always only be one selection
        var uid = event.records[0].get("uid"),
            targetUid = target.get("uid");
        if (target.get("leaf") || uid == targetUid) {
            return false;
        }

        Zenoss.remote.ReportRouter.moveNode({
            uid: uid,
            target: targetUid
        }, function(response){
            if(response.success){
               tree.refresh();
            }
        });
        return true;

    });
}

function insertNewNode(tree, data, organizerNode) {
    var newNode = organizerNode.appendChild(data.newNode),
        firstLeafNode = organizerNode.findChild('leaf', true);
    organizerNode.expand();
    report_tree.getSelectionModel().select(newNode);
    return newNode;
}


Ext.define('Zenoss.ReportTreePanel', {
    extend: 'Zenoss.HierarchyTreePanel',
    // Do not automatically select the first filtered result since running
    // a report is so expensive.
    postFilter: Ext.emptFn,
    addNode: function (nodeType, id) {
        var selNode = this.getSelectionModel().getSelectedNode(),
            tree = this,
            newNode;
        if(!selNode.data.uid){
            this.getSelectionModel().selectByPosition({row: 0});
            selNode = this.getSelectionModel().getSelectedNode();
        }
        var parentNode = selNode.leaf ? selNode.parentNode : selNode;
        this.router.addNode({
            nodeType: nodeType,
            contextUid: parentNode.data.uid,
            id: id
        }, function (data) {
            if (data.success) {
                newNode = insertNewNode(tree, data, parentNode);
                if (newNode.data.edit_url) {
                    window.location = newNode.data.edit_url;
                }
                tree.refresh();
            }
        });
    },
    deleteSelectedNode: function () {
        var node = this.getSelectionModel().getSelectedNode();
        if (node.data.leaf) {
            this._confirmDeleteSelectedNode(_t('Delete Report'),
                _t('Confirm report deletion.'));
        } else {
            if (node.childNodes.length < 1) {
                this._deleteSelectedNode();
            } else {
                this._confirmDeleteSelectedNode(_t('Delete Organizer'),
                    _t('Warning! This will delete all of the reports in this group!'));
            }
        }
    },
    _confirmDeleteSelectedNode: function (title, message) {
        Ext.MessageBox.show({
            title: title,
            msg: message,
            fn: function(buttonid) {
                if (buttonid=='ok') {
                    report_tree._deleteSelectedNode();
                }
            },
            buttons: Ext.MessageBox.OKCANCEL
        });
    },
    _deleteSelectedNode: function () {
        var node = this.getSelectionModel().getSelectedNode(),
            sm = this.getSelectionModel(),
            parentNode = node.parentNode,
            uid = node.data.uid,
            params = {uid: uid},
            tree = this;
        function callback(data) {
            if (data.success) {
                sm.select(parentNode);
                parentNode.removeChild(node);
                node.destroy();
                this.addHistoryToken(this.getView(), parentNode);
                this.refresh();
            }
        }
        this.router.deleteNode(params, Ext.Function.bind(callback, this));
    },
    editReport: function () {
        window.location = this.getSelectionModel().getSelectedNode().data.edit_url;
    }
});





treesm = new Zenoss.TreeSelectionModel({
    listeners: {
        'selectionchange': function (sm, newnode) {
            if (newnode == null) {
                return;
            }
            var attrs = newnode[0].data;
            report_panel.setContext(attrs.leaf
                    ? Ext.urlAppend(attrs.uid, 'adapt=false')
                    : '');
            if (Zenoss.Security.hasPermission(REPORT_PERMISSION)) {
                Ext.getCmp('add-organizer-button').setDisabled(attrs.leaf);
                Ext.getCmp('add-to-zenpack-button').setDisabled(attrs.leaf);
                Ext.getCmp('edit-button').setDisabled(!attrs.edit_url);
                Ext.getCmp('delete-button').setDisabled(!attrs.deletable);
            }
        }
    }
});

report_tree = new Zenoss.ReportTreePanel({
    id: 'reporttree',
    cls: 'report-tree',
    ddGroup: 'reporttreedd',
    searchField: true,
    rootVisible: false,
    ddGroup: 'reporttreedd',
    bodyStyle: 'background-color:transparent;',
    directFn: Zenoss.remote.ReportRouter.asyncGetTree,
    router: Zenoss.remote.ReportRouter,
    root: {
        nodeType: 'async',
        id: 'Reports',
        uid: '/zport/dmd/Reports',
        text: _t('Report Classes'),
        allowDrop: false
    },
    selModel: treesm,
    listeners: {
        render: initializeTreeDrop
    },
    dropConfig: { appendOnly: true },
    extraFields: [{
        name: 'deletable',
        type: 'bool'
    }, {
        name: 'edit_url',
        type: 'string'
    }]
});

var treepanel = {
    xtype: 'HierarchyTreePanelSearch',
    bodyStyle: 'background-color:#d4e0ee;',
    items: [report_tree]
};

Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border': false
    },
    items: [{
        id: 'master_panel',
        layout: 'fit',
        region: 'west',
        width: 300,
        maxWidth: 300,
        split: true,
        items: [treepanel]
    }, {
        layout: 'fit',
        region: 'center',
        items: [report_panel]
    }]
});

function createAction(typeName, text) {
    return new Zenoss.Action({
        text: _t('Add ') + text + '...',
        iconCls: 'add',
        permission: REPORT_PERMISSION,
        handler: function () {
            var addDialog = new Zenoss.FormDialog({
                title: _t('Create ') + text,
                modal: true,
                width: 350,
                formId: 'addForm',
                items: [{
                    xtype: 'textfield',
                    fieldLabel: _t('ID'),
                    name: 'name',
                    anchor:'80%',
                    allowBlank: false
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Submit'),
                    ui: 'dialog-dark',
                    handler: function () {
                        var form, newName;
                        form = Ext.getCmp('addForm').getForm();
                        newName = form.findField('name').getValue();
                        report_tree.addNode(typeName, newName);
                    }
                },
                    Zenoss.dialog.CANCEL
                ]
            });
            addDialog.show(this);
        }
    });
}

Ext.getCmp('footer_bar').add({
    id: 'add-organizer-button',
    tooltip: _t('Add report organizer or report'),
    disabled: Zenoss.Security.doesNotHavePermission(REPORT_PERMISSION),
    iconCls: 'add',
    menu: {
        width: 190, // mousing over longest menu item was changing width
        items: [
            createAction('organizer', _t('Report Organizer'))
        ]
    }
});

Zenoss.remote.ReportRouter.getReportTypes({},
    function (data) {
        var menu = Ext.getCmp('add-organizer-button').menu;
        for (var idx = 0; idx < data.reportTypes.length; idx++) {
            var reportType = data.reportTypes[idx],
                    menuText = data.menuText[idx];
            menu.add(createAction(reportType, menuText));
        }
    }
);

Ext.getCmp('footer_bar').add({
    id: 'delete-button',
    disabled: Zenoss.Security.doesNotHavePermission(REPORT_PERMISSION),
    tooltip: _t('Delete an item'),
    iconCls: 'delete',
    handler: deleteNode
});

Ext.getCmp('footer_bar').add({
    xtype: 'tbseparator'
});

Ext.getCmp('footer_bar').add({
    id: 'edit-button',
    disabled: Zenoss.Security.doesNotHavePermission(REPORT_PERMISSION),
    tooltip: _t('Edit a report'),
    iconCls: 'set',
    handler: function() {
        report_tree.editReport();
    }
});

Ext.getCmp('footer_bar').add({
    id: 'add-to-zenpack-button',
    disabled: Zenoss.Security.doesNotHavePermission(REPORT_PERMISSION),
    tooltip: _t('Add to ZenPack'),
    iconCls: 'adddevice',
    handler: addToZenPack
});

});

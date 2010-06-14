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
Ext.ns('Zenoss.ui.Reports');

Ext.onReady(function () {

var addtozenpack,
    report_panel = new Zenoss.BackCompatPanel({}),
    initialContextSet = false,
    treesm,
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
    if (!addtozenpack) {
        addtozenpack = new Zenoss.AddToZenPackWindow();
    }
    addtozenpack.setTarget(treesm.getSelectedNode().attributes.uid);
    addtozenpack.show();
}

function initializeTreeDrop(g) {
    var dz = new Ext.tree.TreeDropZone(g, {
        ddGroup: 'reporttreedd',
        appendOnly: true,
        onNodeDrop: function (target, dd, e, data) {
            if (target.node.attributes.leaf) {
                try {
                    this.tree.selModel.suspendEvents(true);
                    data.node.unselect();
                    return false;
                } finally {
                    this.tree.selModel.resumeEvents();
                }
            }
            var tree = this.tree;
            Zenoss.remote.ReportRouter.moveNode({
                uids: [data.node.attributes.uid],
                target: target.node.attributes.uid
            }, function (cb_data) {
                var parentNode, newNode;
                if (cb_data.success) {
                    try {
                        tree.selModel.suspendEvents(true);
                        parentNode = data.node.parentNode;
                        parentNode.removeChild(data.node);
                        data.node.destroy();
                        newNode = tree.getLoader().createNode(cb_data.newNode);
                        target.node.expand();
                        addNodeToOrganizer(newNode, target.node);
                        tree.update(cb_data.tree);
                    } finally {
                        tree.selModel.resumeEvents();
                    }
                }
            });
            return true;
        }
    });
}

function addNodeToOrganizer(node, organizerNode) {
    var lastIndex = organizerNode.childNodes.length - 1;
    if ((node.leaf) ||
            (lastIndex < 0) ||
            (!organizerNode.childNodes[lastIndex].attributes.leaf)) {
        organizerNode.appendChild(node);
    } else {
        var notAdded = true;
        for (var i = 0; i < organizerNode.childNodes.length; i++) {
            if (organizerNode.childNodes[i].leaf) {
                organizerNode.insertBefore(node,
                        organizerNode.childNodes[i]);
                notAdded = false;
                break;
            }
        }
        if (notAdded) {
            organizerNode.appendChild(node);
        }
    }
    node.select();
}

Zenoss.ReportTreeNodeUI = Ext.extend(Zenoss.HierarchyTreeNodeUI, {
    render: function (bulkRender) {
        var n = this.node,
            a = n.attributes;
        if (n.isLeaf()) {
            a.iconCls = 'leaf';
            a.draggable = true;
            a.allowDrop = false;
            n.text = a.text;
        }
        else {
            a.iconCls = 'severity-icon-small clear';
            a.draggable = false;
            a.allowDrop = true;
            n.text = a.text;
        }
        Zenoss.ReportTreeNodeUI.superclass.render.call(this,
                bulkRender);
    }
});

Zenoss.ReportTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {
    constructor: function (config) {
        config.loader = {
            xtype: 'treeloader',
            directFn: Zenoss.remote.ReportRouter.getTree,
            uiProviders: {
                'report': Zenoss.ReportTreeNodeUI
            },
            getParams: function (node) {
                return [node.attributes.uid];
            }
        };
        Zenoss.ReportTreePanel.superclass.constructor.call(this,
                config);
    },
    addNode: function (nodeType, id) {
        var selectedNode = this.getSelectionModel().getSelectedNode(),
                parentNode;
        if (selectedNode.leaf) {
            parentNode = selectedNode.parentNode;
        } else {
            parentNode = selectedNode;
        }
        parentNode.expand();
        var contextUid = parentNode.attributes.uid,
                params = {nodeType: nodeType, contextUid: contextUid, id: id},
                tree = this;
        function callback(data) {
            if (data.success) {
                var nodeConfig, node, lastIndex;
                nodeConfig = data.newNode;
                node = tree.getLoader().createNode(nodeConfig);
                addNodeToOrganizer(node, parentNode);
                node.expand();
                tree.update(data.tree);
                if (node.attributes.leaf) {
                    window.location = node.attributes.uid + 
                            '/edit' +
                            node.attributes.meta_type;
                }
            }
        }
        this.router.addNode(params, callback);
    },
    deleteSelectedNode: function () {
        var node = this.getSelectionModel().getSelectedNode();
        if (node.childNodes.length < 1) {
            this._deleteSelectedNode();
            return;
        }
        Ext.MessageBox.show({
            title: _t('Delete Organizer'),
            msg: _t('Warning! ' +
                    'This will delete all of the reports in this group!'),
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
                parentNode = node.parentNode,
                uid = node.attributes.uid,
                params = {uid: uid},
                tree = this;
        function callback(data) {
            if (data.success) {
                parentNode.select();
                parentNode.removeChild(node);
                node.destroy();
                tree.update(data.tree);
            }
        }
        this.router.deleteNode(params, callback);
    },
    editReport: function () {
        var node = this.getSelectionModel().getSelectedNode(),
                uid = node.attributes.uid,
                meta_type = node.attributes.meta_type;
        window.location = uid + '/edit' + meta_type;
    }
});

report_panel.addListener('frameload', function(win) {
    var anchors = win.document.getElementsByTagName('a');
    for (var idx = 0; idx < anchors.length; idx++) {
        if (!/\/zport\/dmd\/[rR]eports\//.test(anchors[idx].href)) {
            anchors[idx].onclick = function() {
                window.top.location.href = this.href;
            };
        }
    }
});

treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function (sm, newnode) {
            if (newnode == null) {
                return;
            }
            if (newnode.attributes.leaf && !initialContextSet) {
                initialContextSet = true;
                var uid = newnode.attributes.uid,
                    meta_type = newnode.attributes.meta_type;
                if (meta_type == 'Report') {
                    report_panel.setContext(uid + '?adapt=false');
                } else {
                    report_panel.setContext(uid + '/view' + meta_type);
                }
            }
            Ext.getCmp('add-organizer-button').setDisabled(newnode.attributes.leaf);
            Ext.getCmp('add-to-zenpack-button').setDisabled(newnode.attributes.leaf);
            Ext.getCmp('edit-button').setDisabled(!/^(Device|(Multi)?Graph)Report$/.test(newnode.attributes.meta_type));
            Ext.getCmp('delete-button').setDisabled(!newnode.attributes.deletable);
        }
    }
});

report_tree = new Zenoss.ReportTreePanel({
    id: 'reporttree',
    cls: 'report-tree',
    ddGroup: 'reporttreedd',
    searchField: true,
    enableDD: true,
    router: Zenoss.remote.ReportRouter,
    root: {
        id: 'Reports',
        uid: '/zport/dmd/Reports',
        text: _t('Report Classes'),
        allowDrop: false
    },
    selModel: treesm,
    listeners: {
        render: initializeTreeDrop,
        click: function (node, e) {
            if (node.attributes.leaf) {
                var uid = node.attributes.uid,
                    meta_type = node.attributes.meta_type;
                if (meta_type == 'Report') {
                    report_panel.setContext(uid + '?adapt=false');
                } else {
                    report_panel.setContext(uid + '/view' + meta_type);
                }
            }
        }
    },
    dropConfig: { appendOnly: true }
});

report_tree.expandAll();

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
        split: true,
        items: [report_tree]
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
        handler: function () {
            var addDialog = new Zenoss.FormDialog({
                title: _t('Create ') + text,
                modal: true,
                width: 310,
                formId: 'addForm',
                items: [{
                    xtype: 'textfield',
                    fieldLabel: _t('ID'),
                    name: 'name',
                    allowBlank: false
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Submit'),
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
    tooltip: _t('Delete an item'),
    iconCls: 'delete',
    handler: deleteNode
});

Ext.getCmp('footer_bar').add({
    xtype: 'tbseparator'
});

Ext.getCmp('footer_bar').add({
    id: 'edit-button',
    tooltip: _t('Edit a report'),
    iconCls: 'set',
    handler: function() {
        report_tree.editReport();
    }
});

Ext.getCmp('footer_bar').add({
    id: 'add-to-zenpack-button',
    tooltip: _t('Add to ZenPack'),
    iconCls: 'adddevice',
    handler: addToZenPack
});

});

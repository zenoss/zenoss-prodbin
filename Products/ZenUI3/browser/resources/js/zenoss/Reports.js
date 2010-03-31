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

var addrorg,
    addtozenpack;

/*
 * Add a report class
 */
function addReportOrganizer(e) {
    if (!addrorg) {
        addrorg = new Ext.Window({
            title: _t('Create Report Organizer'),
            layout: 'fit',
            autoHeight: true,
            width: 310,
            closeAction: 'hide',
            plain: true,
            items: [{
                id: 'addrorgform',
                xtype: 'form',
                monitorValid: true,
                defaults: {width: 180},
                autoHeight: true,
                border: false,
                frame: false,
                labelWidth: 100,
                items: [{
                    xtype: 'textfield',
                    fieldLabel: _t('ID'),
                    name: 'rorgname',
                    allowBlank: false
                }],
                buttons: [{
                    text: _t('Cancel'),
                    handler: function () {
                        addrorg.hide();
                    }
                }, {
                    text: _t('Submit'),
                    formBind: true,
                    handler: function () {
                        var form, newrorgname;
                        form = Ext.getCmp('addrorgform').getForm();
                        newrorgname = form.findField('rorgname').getValue();
                        report_tree.addNode('organizer', newrorgname);
                        addrorg.hide();
                    }
                }]
            }]
        });
    }
    addrorg.show(this);
}

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
            if ((target.node.attributes.leaf) || 
                    (target.node == data.node.parentNode)) {
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
                        target.node.appendChild(newNode);
                        newNode.select();
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

Zenoss.ReportTreeNodeUI = Ext.extend(Zenoss.HierarchyTreeNodeUI, {
    render: function (bulkRender) {
        var n = this.node,
            a = n.attributes;
        if (n.isLeaf()) {
            a.iconCls = 'leaf';
            a.draggable = true;
            a.allowDrop = false;
            n.text = a.text;
        } else {
            a.iconCls = 'severity-icon-small clear';
            a.draggable = false;
            a.allowDrop = true;
            n.text = this.buildNodeText(this.node);
        }
        Zenoss.ReportTreeNodeUI.superclass.render.call(this, 
                bulkRender);
    },
    onTextChange : function (node, text, oldText) {
        if ((this.rendered) && (!node.isLeaf())) {
            this.textNode.innerHTML = this.buildNodeText(node);
        }
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
    addNode: function (type, id) {
        var selectedNode = this.getSelectionModel().getSelectedNode(),
                parentNode;
        if (selectedNode.leaf) {
            parentNode = selectedNode.parentNode;
        } else {
            parentNode = selectedNode;
        }
        parentNode.expand();
        var contextUid = parentNode.attributes.uid,
                params = {type: type, contextUid: contextUid, id: id},
                tree = this;
        function callback(data) {
            if (data.success) {
                var nodeConfig, node, lastIndex;
                nodeConfig = data.newNode;
                node = tree.getLoader().createNode(nodeConfig);
                lastIndex = parentNode.childNodes.length - 1;
                if ((node.leaf) || 
                        (lastIndex < 0) ||
                        (!parentNode.childNodes[lastIndex].attributes.leaf)) {
                    parentNode.appendChild(node);
                } else {
                    var notAdded = true;
                    for (var i = 0; i < parentNode.childNodes.length; i++) {
                        if (parentNode.childNodes[i].leaf) {
                            parentNode.insertBefore(node, 
                                    parentNode.childNodes[i]);
                            notAdded = false;
                            break;
                        }
                    }
                    if (notAdded) {
                        parentNode.appendChild(node);
                    }
                }
                node.select();
                node.expand();
                tree.update(data.tree);
            }
        }
        this.router.addNode(params, callback);
    },
    deleteSelectedNode: function () {
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
    }
});

var report_panel = new Zenoss.BackCompatPanel({});

var treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function (sm, newnode) {
            if (newnode.attributes.leaf) {
                report_panel.setContext(newnode.attributes.uid);
                Ext.getCmp('add-organizer-button').disable();
            } else {
                Ext.getCmp('add-organizer-button').enable();
            }
        }
    }
});

var report_tree = new Zenoss.ReportTreePanel({
    id: 'reports',
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
    listeners: { render: initializeTreeDrop },
    dropConfig: { appendOnly: true }
});

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
        width: 275,
        split: true,
        items: [report_tree]
    }, {
        layout: 'fit',
        region: 'center',
        items: [report_panel]
    }]
});

Ext.getCmp('footer_bar').add({
    id: 'add-organizer-button',
    tooltip: _t('Add a report organizer'),
    iconCls: 'add',
    handler: addReportOrganizer
});

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
    id: 'adddevice-button',
    tooltip: _t('Add to ZenPack'),
    iconCls: 'adddevice',
    handler: addToZenPack
});

});

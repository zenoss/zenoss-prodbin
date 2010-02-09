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

Ext.onReady(function(){

var addrorg,
    addrorgtozenpack;

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
                    handler: function(){
                        addrorg.hide();
                    }
                },{
                    text: _t('Submit'),
                    formBind: true,
                    handler: function(){
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
function deleteReportOrganizer(e) {
    if (!report_tree.getSelectionModel().getSelectedNode().leaf) {
        report_tree.deleteSelectedNode();
    }
}

/*
 * add report class to zenpack
 */
function addToZenPack(e) {
    if (!addrorgtozenpack) {
        addrorgtozenpack = new Ext.Window({
            title: _t('Add to Zen Pack'),
            layout: 'fit',
            autoHeight: true,
            width: 310,
            closeAction: 'hide',
            plain: true,
            items: [{
                id: 'addzenpackform',
                xtype: 'form',
                monitorValid: true,
                defaults: {width: 180},
                autoHeight: true,
                border: false,
                frame: false,
                labelWidth: 100,
                items: [{
                    fieldLabel: _t('Zen Pack'),
                    name: 'zpname',
                    xtype: 'combo',
                    allowBlank: false,
                    store: new Ext.data.DirectStore({
                        id: 'myzpstore',
                        fields: ['name'],
                        root: 'packs',
                        totalProperty: 'totalCount',
                        directFn: 
                            Zenoss.remote.ReportRouter.getEligiblePacks
                    }),
                    valueField: 'name', 
                    displayField: 'name',
                    forceSelection: true,
                    triggerAction: 'all',
                    selectOnFocus: true,
                    id: 'zpcombobox',
                }],
                buttons: [{
                    text: _t('Cancel'),
                    handler: function(){
                        addrorgtozenpack.hide();
                    }
                },{
                    text: _t('Submit'),
                    formBind: true,
                    handler: function(){
                        form = Ext.getCmp('addzenpackform');
                        var chosenzenpack = 
                            form.getForm().findField('zpname').getValue();
                        addrorgtozenpack.hide();
                    }
                }]
            }]
        });
    }
    addrorgtozenpack.show(this);
}

function initializeTreeDrop(g) {
    var dz = new Ext.tree.TreeDropZone(g, {
        ddGroup: 'reporttreedd',
        appendOnly: true,
        onNodeDrop: function(target, dd, e, data) {
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
            Zenoss.remote.ReportRouter.moveReports({
                uids: [data.node.attributes.uid],
                target: target.node.attributes.uid
            }, function(cb_data) {
                if(cb_data.success) {
                    try {
                        tree.selModel.suspendEvents(true);
                        nodeConfig = {};
                        Ext.applyIf(nodeConfig, data.node.attributes);
                        desiredUid = target.node.attributes.uid + '/' +
                                nodeConfig['id'];
                        nodeConfig['uid'] = desiredUid;
                        parentNode = data.node.parentNode;
                        parentNode.removeChild(data.node);
                        data.node.destroy();
                        newNode = tree.getLoader().createNode(nodeConfig);
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
    render: function(bulkRender) {
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
    onTextChange : function(node, text, oldText){
        if ((this.rendered) && (!node.isLeaf())) {
            this.textNode.innerHTML = this.buildNodeText(node);
        }
    }
});

Zenoss.ReportTreePanel = Ext.extend(Zenoss.HierarchyTreePanel,{
    constructor: function(config) {
        config.loader = {
            xtype: 'treeloader',
            directFn: Zenoss.remote.ReportRouter.getTree,
            uiProviders: {
                'report': Zenoss.ReportTreeNodeUI
            },
            getParams: function(node) {
                return [node.attributes.uid];
            }
        };
        Zenoss.ReportTreePanel.superclass.constructor.call(this, 
                config);
    },
    addNode: function(type, id) {
        var selectedNode = this.getSelectionModel().getSelectedNode();
        var parentNode;
        if (selectedNode.leaf) {
            parentNode = selectedNode.parentNode;
        } else {
            parentNode = selectedNode;
        }
        var contextUid = parentNode.attributes.uid;
        var params = {type: type, contextUid: contextUid, id: id};
        var tree = this;
        function callback(provider, response) {
            var result = response.result;
            if (result.success) {
                var nodeConfig = response.result.nodeConfig;
                var node = tree.getLoader().createNode(nodeConfig);
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
                tree.update(result.tree);
            } else {
                Ext.Msg.alert('Error', result.msg);
            }
        }
        this.router.addNode(params, callback);
    },
    deleteSelectedNode: function() {
        var node = this.getSelectionModel().getSelectedNode();
        var parentNode = node.parentNode;
        var uid = node.attributes.uid;
        var params = {uid: uid};
        var tree = this;
        function callback(provider, response) {
            var result = response.result;
            if (result.success) {
                parentNode.select();
                parentNode.removeChild(node);
                node.destroy();
                tree.update(result.tree);
            }
        }
        this.router.deleteNode(params, callback);
    },
});

Zenoss.ReportCompatPanel = Ext.extend(Zenoss.BackCompatPanel,{
    setContext: function(uid) {
        if (this.contextUid!=uid){
            this.on('frameload', this.injectViewport, {scope:this, single:true})
            this.contextUid = uid;
            this.setSrc(uid);
        }
    }
});

var report_panel = new Zenoss.ReportCompatPanel({});

var treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function(sm, newnode) {
            if (newnode.attributes.leaf) {
                report_panel.setContext(newnode.attributes.uid);
                Ext.getCmp('add-button').disable();
                Ext.getCmp('delete-button').disable();
            } else {
                Ext.getCmp('add-button').enable();
                Ext.getCmp('delete-button').enable();
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
        items: [report_tree],
    },{
        layout: 'fit',
        region: 'center',
        items: [report_panel],
    }]
});

Ext.getCmp('footer_bar').add({
    id: 'add-button',
    tooltip: _t('Add a report organizer'),
    iconCls: 'add',
    handler: addReportOrganizer
});

Ext.getCmp('footer_bar').add({
    id: 'delete-button', 
    tooltip: _t('Delete a report organizer'),
    iconCls: 'delete',
    handler: deleteReportOrganizer
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

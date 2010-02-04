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

(function(){

Ext.ns('Zenoss');

function initTreeDialogs(tree) {
    
    new Zenoss.HideFormDialog({
        id: 'addNodeDialog',
        title: _t('Add Tree Node'),
        items: [
            {
                xtype: 'combo',
                id: 'typeCombo',
                fieldLabel: _t('Type'),
                displayField: 'type',
                mode: 'local',
                forceSelection: true,
                triggerAction: 'all',
                emptyText: 'Select a type...',
                selectOnFocus: true,
                store: new Ext.data.ArrayStore({
                    fields: ['type'],
                    data: [['Organizer'], ['Class']]
                })
            }, {
                xtype: 'textfield',
                id: 'idTextfield',
                fieldLabel: _t('ID'),
                allowBlank: false
            }
        ],
        listeners: {
            'hide': function(treeDialog) {
                Ext.getCmp('typeCombo').setValue('');
                Ext.getCmp('idTextfield').setValue('');
            }
        },
        buttons: [
            {
                xtype: 'HideDialogButton',
                text: _t('Submit'),
                dialogId: 'addNodeDialog',
                handler: function(button, event) {
                    var type = Ext.getCmp('typeCombo').getValue();
                    var id = Ext.getCmp('idTextfield').getValue();
                    tree.addNode(type, id);
                }
            }, {
                xtype: 'HideDialogButton',
                text: _t('Cancel'),
                dialogId: 'addNodeDialog'
            }
        ]
    });
    
    new Zenoss.MessageDialog({
        id: 'deleteNodeDialog',
        title: _t('Delete Tree Node'),
        message: _t('The selected node will be deleted.'),
        okHandler: function(){
            tree.deleteSelectedNode();
        }
    });
    
}

function buttonClickHandler(buttonId) {
    switch(buttonId) {
        case 'addButton':
            Ext.getCmp('addNodeDialog').show();
            break;
        case 'deleteButton':
            Ext.getCmp('deleteNodeDialog').show();
            break;
    }
}

/**
 * @class Zenoss.HierarchyTreePanel
 * @extends Ext.tree.TreePanel
 * The primary way of navigating one or more hierarchical structures. A
 * more advanced Subsections Tree Panel. Configurable as a drop target.
 * Accepts array containing one or more trees (as nested arrays). In at
 * least one case data needs to be asynchronous. Used on screens:
 *   Device Classification Setup Screen
 *   Devices
 *   Device
 *   Event Classification
 *   Templates
 *   Manufacturers
 *   Processes
 *   Services
 *   Report List
 * @constructor
 */

Zenoss.HierarchyTreeNodeUI = Ext.extend(Ext.tree.TreeNodeUI, {

    buildNodeText: function(node) {
        var b = [];
        var t = node.attributes.text;
        if (node.isLeaf()) {
            b.push(t.text);
        } else {
            b.push('<strong>' + t.text + '</strong>');
        }
        if (t.count!=undefined) {
            b.push('<span class="node-extra">(' + t.count);
            b.push((t.description || 'instances') + ')</span>');
        }
        return b.join(' ');
    },

    render: function(bulkRender) {
        var n = this.node,
            a = n.attributes;
        if (a.text && Ext.isObject(a.text)) {
            n.text = this.buildNodeText(this.node);
        }
        Zenoss.HierarchyTreeNodeUI.superclass.render.call(this, bulkRender);
    },

    onTextChange : function(node, text, oldText){
        if(this.rendered){
            this.textNode.innerHTML = this.buildNodeText(node);
        }
    }
});

Zenoss.HierarchyRootTreeNodeUI = Ext.extend(Zenoss.HierarchyTreeNodeUI, {

    buildNodeText: function(node) {
        var b = [];
        var t = node.attributes.text;

        b.push(t.substring(t.lastIndexOf('/')));

        if (t.count!=undefined) {
            b.push('<span class="node-extra">(' + t.count);
            b.push((t.description || 'instances') + ')</span>');
        }
        return b.join(' ');
    }
});

Zenoss.HierarchyTreePanel = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            cls: 'hierarchy-panel',
            useArrows: true,
            border: false,
            autoScroll: true,
            containerScroll: true,
            selectRootOnLoad: true
        });
        if (config.directFn && !config.loader) {
            config.loader = {
                xtype: 'treeloader',
                directFn: config.directFn,
                uiProviders: {
                    'hierarchy': Zenoss.HierarchyTreeNodeUI
                },
                getParams: function(node) {
                    return [node.attributes.uid];
                }
            };
            Ext.destroyMembers(config, 'directFn');
        }
        var root = config.root || {};
        Ext.applyIf(root, {
            nodeType: 'async',
            id: root.id,
            uid: root.uid,
            text: _t(root.text || root.id)
        });
        config.listeners = Ext.applyIf(config.listeners || {}, {
            buttonClick: buttonClickHandler
        });
        this.router = config.router;
        config.loader.baseAttrs = {iconCls:'severity-icon-small clear'};
        Zenoss.HierarchyTreePanel.superclass.constructor.apply(this,
            arguments);
        initTreeDialogs(this);
    },
    initEvents: function() {
        Zenoss.HierarchyTreePanel.superclass.initEvents.call(this);
        if (this.selectRootOnLoad && !Ext.History.getToken()) {
            this.getRootNode().on('load', function(node){
                node.select()
            });
        }
        this.on('click', function(node, event) {
            Ext.History.add(
                this.id + Ext.History.DELIMITER + node.getPath()
            );
        }, this);
    },
    update: function(data) {
        function doUpdate(root, data) {
            Ext.each(data, function(datum){
                var node = root.findChild('id', datum.id);
                if(node) {
                    node.attributes = datum;
                    node.setText(node.attributes.text);
                    doUpdate(node, datum.children);
                }
            });
        }
        doUpdate(this.getRootNode(), data);

    },
    selectByPath: function(escapedId) {
        var id = unescape(escapedId);
        this.expandPath(id, 'id', function(t, n){
            if (n && !n.isSelected()) {
                n.fireEvent('click', n);
            }
        });
    },
    selectByToken: function(token) {
        if (!this.root.loaded) {
            this.loader.on('load',function(){this.selectByPath(token)}, this);
        } else {
            this.selectByPath(token);
        }
    },
    afterRender: function() {
        Zenoss.HierarchyTreePanel.superclass.afterRender.call(this);
        this.root.ui.addClass('hierarchy-root');
        Ext.removeNode(this.root.ui.getIconEl());
        if (this.searchField) {
            this.filter = new Ext.tree.TreeFilter(this, {
                clearBlank: true,
                autoClear: true
            });
            this.searchField = this.add({
                xtype: 'searchfield',
                bodyStyle: {padding: 10},
                listeners: {
                    valid: this.filterTree,
                    scope: this
                }
            });
        }
        this.getRootNode().expand();
    },
    filterTree: function(e) {
        var text = e.getValue();
        if (this.hiddenPkgs) {
            Ext.each(this.hiddenPkgs, function(n){n.ui.show()});
        }
        this.hiddenPkgs = [];
        if (!text) {
            this.filter.clear();
            return;
        }
        this.expandAll();
        var re = new RegExp(Ext.escapeRe(text), 'i');
        this.filter.filterBy(function(n){
            var match = false;
            Ext.each(n.id.split('/'), function(s){
                match = match || re.test(s);
            });
            return !n.isLeaf() || match;
        });
        this.root.cascade(function(n){
            if(!n.isLeaf() && n.ui.ctNode.offsetHeight<3){
                n.ui.hide();
                this.hiddenPkgs.push(n);
            }
        }, this);
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
                parentNode.appendChild(node);
                node.select();
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
        function callback(provider, response) {
            parentNode.select();
            parentNode.removeChild(node);
            node.destroy();
        }
        this.router.deleteNode(params, callback);
    }
}); // HierarchyTreePanel

Ext.reg('HierarchyTreePanel', Zenoss.HierarchyTreePanel);

})();


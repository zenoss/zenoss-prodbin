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

(function () {

Ext.ns('Zenoss');

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
        // everything should be a span or a text node or it won't be picked up
        // correctly as a drag-and-drop handle
        var b = [];
        var t = node.attributes.text;
        if (node.isLeaf()) {
            b.push(t.text);
        } else {
            b.push('<span style="font-weight: bold;">' + t.text + '</span>');
        }
        if (t.count!==undefined) {
            b.push('<span class="node-extra">(' + t.count);
            b.push((t.description || 'instances') + ')</span>');
        }
        return b.join(' ');
    },

    render: function(bulkRender) {
        var n = this.node,
            a = n.attributes;

        // Hack this in here because baseAttrs doesn't work on loader
        n.hasChildNodes = function() {
            return (a.children && a.children.length>0);
        }.createDelegate(n);

        if (a.text && Ext.isObject(a.text)) {
            n.text = this.buildNodeText(this.node);
        }
        Zenoss.HierarchyTreeNodeUI.superclass.render.call(this, bulkRender);
    },

    onTextChange : function(node, text, oldText){
        if(this.rendered){
            this.textNode.innerHTML = this.buildNodeText(node);
        }
    },
    
    getDDHandles : function(){
        // include the child span nodes of the text node as drop targets
        var ddHandles, spans;
        ddHandles = Zenoss.HierarchyTreeNodeUI.superclass.getDDHandles.call(this);
        spans = Ext.query('span', this.textNode);
        return ddHandles.concat(spans);
    }

});

Zenoss.HierarchyRootTreeNodeUI = Ext.extend(Zenoss.HierarchyTreeNodeUI, {

    buildNodeText: function(node) {
        var b = [];
        var t = node.attributes.text;

        b.push(t.substring(t.lastIndexOf('/')));

        if (t.count!==undefined) {
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
            buttonClick: this.buttonClickHandler
        });
        this.router = config.router;
        config.loader.baseAttrs = {iconCls:'severity-icon-small clear'};
        Zenoss.HierarchyTreePanel.superclass.constructor.apply(this,
            arguments);
        this.initTreeDialogs(this, config);
    },
                                           
    initTreeDialogs: function(tree, config) {
    
        new Zenoss.HideFormDialog({
            id: 'addNodeDialog',
            title: _t('Add Tree Node'),
            items: config.addNodeDialogItems,
            listeners: {
                'hide': function(treeDialog) {
                    Ext.getCmp('typeCombo').setValue('');
                    Ext.getCmp('idTextfield').setValue('');
                }
            },
            buttons: [{
                xtype: 'HideDialogButton',
                text: _t('Submit'),
                handler: function(button, event) {
                    var type = Ext.getCmp('typeCombo').getValue();
                    var id = Ext.getCmp('idTextfield').getValue();
                    tree.addNode(type, id);
                }
             }, {
                xtype: 'HideDialogButton',
                text: _t('Cancel')
            }]
        });

        // the delete message is somewhat janky but pretty much if it is not
        // defined in the object's config then the "DefaultMessage" will be used "
        var message = '<span id="deleteMessage">' + config.deleteMessage +
            '</span>';
        tree.deleteDialog = new Zenoss.MessageDialog({
            id: 'deleteNodeDialog',
            title: _t('Delete Tree Node'),
            message: message,
            defaultMessage:  _t('The selected node will be deleted'),
            width:330,
            okHandler: function(){
                tree.deleteSelectedNode();
            },
            setDeleteMessage: function(msg){
                if (msg === null) {
                    msg = this.defaultMessage;
                }
                this.msg = msg;
                var span = Ext.getDom('deleteMessage');
                if (span){
                    span.innerHTML = msg;
                }
            }
        });
        
    },
    setCorrectDeleteMessage: function() {
        var dialog = Ext.getCmp('deleteNodeDialog');
        
        // if the delete message was not declared in the definition
        if (Ext.isEmpty(dialog.msg)){
            dialog.msg = dialog.defaultMessage;
        }
        dialog.setDeleteMessage(dialog.msg);
    },
    buttonClickHandler: function(buttonId) {
        switch(buttonId) {
            case 'addButton':
                Ext.getCmp('addNodeDialog').show();
                break;
            case 'deleteButton':
                Ext.getCmp('deleteNodeDialog').show();
                this.setCorrectDeleteMessage();
                break;
            default:
                break;
        }
    },
    initEvents: function() {
        Zenoss.HierarchyTreePanel.superclass.initEvents.call(this);
        if (this.selectRootOnLoad && !Ext.History.getToken()) {
            this.getRootNode().on('load', function(node){
                node.select();
            });
        }
        this.addEvents('filter');
        this.on('click', function(node, event) {
            Ext.History.add(this.id + Ext.History.DELIMITER + node.id);
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
    selectByToken: function(token) {
        var selNode = function () {
                var parts = unescape(token).split('.'),
                    curpath = parts.slice(0,4).join('.'),
                    curnode = this.root;
                parts = parts.slice(4);
                parts.reverse();
                while (!Ext.isEmpty(parts)) {
                    if (curnode) {
                        curnode.expand();
                        curpath += '.'+parts.pop(0);
                        curnode = curnode.findChild('id', curpath);
                    } else {
                        break;
                    }
                }
                if (curnode) {
                    curnode.select();
                }
            }.createDelegate(this);
        if (!this.root.loaded) {
            this.loader.on('load', selNode, this);
        } else {
            selNode();
        }
    },
    afterRender: function() {
        Zenoss.HierarchyTreePanel.superclass.afterRender.call(this);
        this.root.ui.addClass('hierarchy-root');
        Ext.removeNode(this.root.ui.getIconEl());
        this.filter = new Ext.tree.TreeFilter(this, {
            clearBlank: true,
            autoClear: true
        });
        if (this.searchField) {
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
        this.fireEvent('filter', e);
        if (this.hiddenPkgs) {
            Ext.each(this.hiddenPkgs, function(n){n.ui.show();});
        }
        this.hiddenPkgs = [];
        if (!text) {
            this.filter.clear();
            return;
        }
        this.expandAll();
        var re = new RegExp(Ext.escapeRe(text), 'i');
        this.root.cascade(function(n){
            var attr = n.id.slice('.zport.dmd'.length);
            if (!n.isRoot) {
                if (re.test(attr)) {
                    var parentNode = n.parentNode;
                    while (parentNode) {
                        if (!parentNode.hidden) {
                            break;
                        }
                        parentNode.ui.show();
                        parentNode = parentNode.parentNode;
                    }
                    // the cascade is stopped on this branch
                    return false;
                } else {
                    n.ui.hide();
                    this.hiddenPkgs.push(n);
                }
            }
            // continue cascading down the tree from this node
            return true;
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
                // if you don't call expand on the parentNode you will get a 
                // javascript error that does not make sense on the callback 
                parentNode.expand();
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

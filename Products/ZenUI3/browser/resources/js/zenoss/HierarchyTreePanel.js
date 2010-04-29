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

var nodeTemplate = new Ext.Template('<span style="font-weight:bold">{text}</span>',
                                    '<span class="node-extra">({count})</span>');
nodeTemplate.compile();

Zenoss.HierarchyTreeNodeUI = Ext.extend(Ext.tree.TreeNodeUI, {
    buildNodeText: function(node) {
        // everything should be a span or a text node or it won't be picked up
        // correctly as a drag-and-drop handle
        var b = [];
        var t = node.attributes.text;

        var textOverride = node.getDepth() === 1 ? node.getOwnerTree().getRootNode().attributes.text : null;

        if ( Ext.isObject(t) ) {
            b.push(nodeTemplate.apply(t));
        }
        else {
            b.push(textOverride || t.text);
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

        if ( n.getDepth() === 1 ) {
            this.addClass('hierarchy-root');
        }
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

Zenoss.HierarchyTreePanel = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            cls: 'hierarchy-panel',
            useArrows: true,
            border: false,
            autoScroll: true,
            containerScroll: true,
            selectRootOnLoad: true,
            rootVisible: false
        });

        if ( config.router ) {
            Ext.applyIf(config, {
                addNodeFn: config.router.addNode,
                deleteNodeFn: config.router.deleteNode
            });
        }
        else {
            Ext.applyIf(config, {
                addNodeFn: Ext.emptyFn,
                deleteNodeFn: Ext.emptyFn
            });
        }

        if (config.directFn && !config.loader) {
            config.loader = new Ext.tree.TreeLoader({
                directFn: config.directFn,
                uiProviders: {
                    'hierarchy': Zenoss.HierarchyTreeNodeUI
                },
                getParams: function(node) {
                    return [node.attributes.uid];
                }
            });
            Ext.destroyMembers(config, 'directFn');
        }
        var root = config.root || {};
        Ext.applyIf(root, {
            nodeType: 'async',
            id: root.id,
            uid: root.uid,
            text: _t(root.text || root.id),
            // Use null so the root won't render
            uiProvider: null
        });
        config.loader.baseAttrs = {
            iconCls: 'severity-icon-small clear',
            uiProvider: 'hierarchy'
        };

        Zenoss.HierarchyTreePanel.superclass.constructor.apply(this,
            arguments);
    },
    initEvents: function() {
        Zenoss.HierarchyTreePanel.superclass.initEvents.call(this);
        if (this.selectRootOnLoad && !Ext.History.getToken()) {
            this.getRootNode().on('expand', function() {
                // The first child is our real root
                if ( this.getRootNode().firstChild ) {
                    this.getRootNode().firstChild.select();
                }
            }, this);
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
    selectByToken: function(nodeId) {
        nodeId = unescape(nodeId);

        var selNode = function () {
            var sel = this.getSelectionModel().getSelectedNode();
            if ( !(sel && nodeId === sel.id) ) {
                var path = this.getNodePathById(nodeId);
                this.selectPath(path);
            }
        }.createDelegate(this);

        if (!this.root.loaded) {
            this.getRootNode().on('load', selNode, this);
        } else {
            selNode();
        }
    },
    getNodePathById: function(nodeId) {
        var part,
            depth = this.root.attributes.uid.split('/').length - 1,
            parts = nodeId.split('.'),
            curpath = parts.slice(0, depth).join('.');

        parts = parts.slice(depth);

        var path = [this.root.getPath()];
        while ( part = parts.shift() ) {
            curpath = [curpath, part].join('.');
            path.push(curpath);
        }

        return path.join(this.pathSeparator);
    },
    afterRender: function() {
        Zenoss.HierarchyTreePanel.superclass.afterRender.call(this);

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
        this.getRootNode().expand(false, true, function(node) {
            node.expandChildNodes();
        });
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
        this.addChildNode({type: type, id: id});
    },

    addChildNode: function(params) {
        var selectedNode = this.getSelectionModel().getSelectedNode();
        var parentNode;
        if (selectedNode.leaf) {
            parentNode = selectedNode.parentNode;
        } else {
            parentNode = selectedNode;
        }
        var contextUid = parentNode.attributes.uid;
        Ext.applyIf(params, {
            contextUid: contextUid
        });

        this.addTreeNode(params);
    },

    addTreeNode: function(params) {
        var callback = function (provider, response) {
            var result = response.result;
            if (result.success) {
                // look for another node on result and assume it's the new node, grab it's id
                // TODO would be best to normalize the names of result node
                var nodeId;
                Ext.iterate(result, function(key, value) {
                    if ( key != 'success' && Ext.isObject(value) && value.id ) {
                        nodeId = value.id;
                        return false;
                    }
                }, this);

                this.getRootNode().reload(function() {
                    if ( nodeId ) {
                        this.selectByToken(nodeId);
                    }
                }, this);
            }
            else {
                Ext.Msg.alert('Error', result.msg);
            }
        };

        this.addNodeFn(params, callback.createDelegate(this));
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
        this.deleteNodeFn(params, callback);
    }
}); // HierarchyTreePanel

Ext.reg('HierarchyTreePanel', Zenoss.HierarchyTreePanel);

})();

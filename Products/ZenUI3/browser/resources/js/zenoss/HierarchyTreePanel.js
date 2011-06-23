/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
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
    renderElements: function(n, a, targetNode, bulkRender) {
        // if children was explicitly set use it, otherwise assume the tree to be
        // asynchronous
        if (Ext.isDefined(a.children)) {
            // Hack this in here because baseAttrs doesn't work on loader
            n.hasChildNodes = function() {
                return (a.children && a.children.length>0);
            }.createDelegate(n);
        }

        Zenoss.HierarchyTreeNodeUI.superclass.renderElements.apply(this, arguments);

        this.textNode = Ext.DomHelper.overwrite(this.textNode, {
            tag: 'span',
            children: [
                { tag: 'span', cls: 'node-text' },
                { tag: 'span', cls: 'node-extra' }
            ]
        }, true);
        this.textNodeBody = this.textNode.child('.node-text');
        this.textNodeExtra = this.textNode.child('.node-extra');

        if ( n.getDepth() === this.node.getOwnerTree().rootDepth ) {
            this.addClass('hierarchy-root');
        }

        this.onTextChange(this.node, a.text, null);
    },
    onTextChange: function(node, data, oldText) {
        if ( this.rendered ) {
            if ( !Ext.isObject(data) ) {
                data = { text: data, count: null };
            }

            var ownerTree = this.node.getOwnerTree(),
                textOverride = this.node.getDepth() === ownerTree.rootDepth ? ownerTree.getRootNode().attributes.text : null;
            if ( textOverride ) {
                data.text = textOverride;
            }

            // Just update the existing elements instead of replacing them so that the dd drop targets
            // stay the same
            this.textNodeBody.update(data.text);
            if ( Ext.isDefined(data.count) && data.count !== null ) {
                this.textNodeExtra.update('(' + data.count + ')');
                this.textNodeExtra.show();
            }
            else {
                this.textNodeExtra.update('');
                this.textNodeExtra.hide();
            }
        }
    },
    getDDHandles : function(){
        // include the child span nodes of the text node as drop targets
        var ddHandles = Zenoss.HierarchyTreeNodeUI.superclass.getDDHandles.call(this);
        return ddHandles.concat([this.textNodeBody, this.textNodeExtra]);
    }

});

Zenoss.HierarchyTreePanelSearch = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        var oldConfig = config;
        config = {
            items: [{
                xtype: 'searchfield',
                bodyStyle: {padding: 10},
                enableKeyEvents: true,
                ref: 'searchfield'
            }, {
                xtype: 'panel',
                items: oldConfig.items,
                flex: 1,
                autoScroll: true,
                regSearchListeners: function(listeners) {
                    this.ownerCt.searchfield.on(listeners);
                }
            }],
            layout: {
                type: 'vbox',
                align: 'stretch'
            }
        };

        Zenoss.HierarchyTreePanelSearch.superclass.constructor.call(this, config);
    }
});

Ext.reg('HierarchyTreePanelSearch', Zenoss.HierarchyTreePanelSearch);

Zenoss.treeContextMenu = function(node, e) {
    // Register the context node with the menu so that a Menu Item's handler function can access
    // it via its parentMenu property.
    var tree = node.getOwnerTree();
    if (!tree.contextMenu) {
        tree.contextMenu = new Ext.menu.Menu({
            items: [{
                ref: 'refreshtree',
                text: _t('Refresh Tree'),
                handler: function(item, e) {
                    var node = item.parentMenu.contextNode,
                    tree = node.getOwnerTree();
                    tree.getRootNode().reload(function(){
                        tree.getRootNode().expand();
                        if (tree.getRootNode().childNodes.length){
                            tree.getRootNode().childNodes[0].expand();
                        }
                    });
                }
            },{
                ref: 'expandall',
                text: _t('Expand All'),
                handler: function(item, e) {
                    var node = item.parentMenu.contextNode,
                    tree = node.getOwnerTree();
                    tree.expandAll();
                }
            },{
                ref: 'collapsall',
                text: _t('Collapse All'),
                handler: function(item, e) {
                    var node = item.parentMenu.contextNode,
                    tree = node.getOwnerTree();
                    tree.collapseAll();
                    // by default we usually expand the first child
                    tree.getRootNode().expand();
                    if (tree.getRootNode().childNodes.length){
                        tree.getRootNode().childNodes[0].expand();
                    }
                }
            },'-',{
                ref: 'expandnode',
                text: _t('Expand Node'),
                handler: function(item, e) {
                    var node = item.parentMenu.contextNode,
                        tree;
                    if (node) {
                        node.expand(true, true);
                    }
                }
            },{
                ref: 'newwindow',
                text: _t('Open in New Window'),
                handler: function(item, e) {
                    var node = item.parentMenu.contextNode,
                    tree, path,
                    href = window.location.protocol + "//" + window.location.host + window.location.pathname;
                    if (node && node.attributes.uid) {
                        tree = node.getOwnerTree();
                        path = tree.createDeepLinkPath(node);
                        window.open(href + "#" + path);
                    }
                }
            }]
        });
    }
    var c = tree.contextMenu;
    c.contextNode = node;
    c.showAt(e.getXY());
};

Zenoss.HierarchyTreePanel = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config) {
        config.listeners = config.listeners || {};
        Ext.applyIf(config.listeners, {
            contextmenu: Zenoss.treeContextMenu
        });

        Ext.applyIf(config, {
            cls: 'hierarchy-panel',
            useArrows: true,
            border: false,
            autoScroll: true,
            relationshipIdentifier: null,
            containerScroll: true,
            selectRootOnLoad: true,
            rootVisible: false,
            rootDepth: config.rootVisible ? 0 : 1,
            loadMask: true,
            allowOrganizerMove: true
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
                },
                listeners: {
                    beforeload: function(){
                        this.on('afterlayout', function(){
                            this.showLoadMask(true);
                        }, this, {single:true});
                    }.createDelegate(this),
                    load: function(){
                        this.showLoadMask(false);
                    }.createDelegate(this)
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
            uiProvider: config.rootVisible ? 'hierarchy' : null
        });
        config.loader.baseAttrs = {
            iconCls: 'severity-icon-small clear',
            uiProvider: 'hierarchy'
        };

        this.stateHash = {};
        if(config.stateful){
            this.stateEvents = this.stateEvents || [];
            this.stateEvents.push('expandnode', 'collapsenode');
        }

        Zenoss.HierarchyTreePanel.superclass.constructor.apply(this, arguments);
    },
    getState:function() {
            return {stateHash:this.stateHash};
    },
    applyState: function(state) {
        if(state) {
            Ext.apply(this, state);
            this.setStateListener();
        }
    },
    setStateListener: function(){
            this.root.on({
                load:{ scope:this, fn:function() {
                    for(var p in this.stateHash) {
                        if(this.stateHash.hasOwnProperty(p)) {
                            this.expandPath(this.stateHash[p]);
                        }
                    }
                }}
            });
    },
    showLoadMask: function(bool) {
        if (!this.loadMask) { return; }
        var container = this.container;
        container._treeLoadMask = container._treeLoadMask || new Ext.LoadMask(this.container);
        var mask = container._treeLoadMask,
            _ = bool ? mask.show() : [mask.hide(), mask.disable()];
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
        this.on('click', this.addHistoryToken, this);

        this.on({
             beforeexpandnode:function(node) {
                this.stateHash[node.id] = node.getPath();
            },
             beforecollapsenode:function(node) {
                delete this.stateHash[node.id];
                var tPath = node.getPath();
                for(var t in this.stateHash) {
                    if(this.stateHash.hasOwnProperty(t)) {
                        if(-1 !== this.stateHash[t].indexOf(tPath)) {
                            delete this.stateHash[t];
                        }
                    }
                }
            }
        });    // add some listeners for state
    },


    addHistoryToken: function(node) {
        Ext.History.add(this.id + Ext.History.DELIMITER + node.id);
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
    createDeepLinkPath: function(node) {
        var path = this.id + Ext.History.DELIMITER + node.attributes.uid.replace(/\//g,'.');
        return path;
    },
    getNodePathById: function(nodeId) {
        var part,
            depth = this.root.attributes.uid.split('/').length - this.rootDepth,
            parts = nodeId.split('.'),
            curpath = parts.slice(0, depth).join('.');

        parts = parts.slice(depth);

        var path = [this.root.getPath()];
        while ( part = parts.shift() ) {
            // this adjusts the path for things like "Service.Linux.devices.Dev1"
            // where "devices" is the relationshipIdentifier"
            if (this.relationshipIdentifier && part == this.relationshipIdentifier){
                curpath = [curpath, part, parts.shift()].join('.');
            }else{
                curpath = [curpath, part].join('.');
            }

            path.push(curpath);
        }

        return path.join(this.pathSeparator);
    },
    afterRender: function() {
        Zenoss.HierarchyTreePanel.superclass.afterRender.call(this);
        var liveSearch = Zenoss.settings.enableLiveSearch,
            listeners = {
                scope: this,
                keypress: function(field, e) {
                    if (e.getKey() === e.ENTER) {
                        this.filterTree(field);
                    }
                }
            };

        if (liveSearch) {
            listeners.valid = this.filterTree;
        }
        if (this.searchField && this.ownerCt.regSearchListeners) {
            this.ownerCt.regSearchListeners(listeners);
        }
        this.getRootNode().expand(false, true, function(node) {
            node.expandChildNodes();
        });
    },
    filterTree: function(e) {
        var text = e.getValue(),
            root = this.getRootNode();
        this.fireEvent('filter', e);
        if (this.hiddenPkgs) {
            Ext.each(this.hiddenPkgs, function(n){n.ui.show();});
        }
        this.hiddenPkgs = [];
        if (!text) {
            // reset the tree to the initial state
            this.collapseAll();
            if (root) {
                root.expand();
                if (root.childNodes) {
                    root.childNodes[0].expand();
                }
            }
            return;
        }
        this.expandAll();
        var re = new RegExp(Ext.escapeRe(text), 'i');
        this.root.cascade(function(n){
            var attr = n.attributes.text;
            if (Ext.isObject(attr)) {
                attr = attr.text;
            }
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
            // Only update the UI if the response indicates success
            if (Zenoss.util.isSuccessful(response)) {
                parentNode.select();
                parentNode.removeChild(node);
                node.destroy();
            }
        }
        // all hierarchytreepanel's have an invisible root node with depth of 0
        if (node.getDepth() <= 1) {
            Zenoss.message.error(_t("You can not delete the root node"));
            return;
        }
        this.deleteNodeFn(params, callback);
    },

    canMoveOrganizer: function(organizerUid, targetUid) {
        var orgPieces = organizerUid.split('/'),
            targetPieces = targetUid.split('/');

        // make sure we can actually move organizers
        if (!this.allowOrganizerMove) {
            return false;
        }

        // Relying on a coincidence that the third item
        // is the top level organizer (e.g. Locations, Groups)
        return orgPieces[3] === targetPieces[3];
    }
}); // HierarchyTreePanel

Ext.reg('HierarchyTreePanel', Zenoss.HierarchyTreePanel);

})();

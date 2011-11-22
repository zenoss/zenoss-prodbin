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

(function() {

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

/**
 * Base Tree Selection model for zenoss. Defines
 * the getSelectedNode method that existed in 3.X trees.
 **/
Ext.define('Zenoss.TreeSelectionModel', {
    extend: 'Ext.selection.TreeModel',
    getSelectedNode: function() {
        var selections = this.getSelection();
        if (selections.length) {
            return selections[0];
        }
        return null;
    }
});

Ext.define('Zenoss.HierarchyTreePanelSearch', {
    extend: 'Ext.Panel',
    alias: ['widget.HierarchyTreePanelSearch'],
    constructor: function(config) {
        var oldConfig = config;
        config = {
            cls: 'x-hierarchy-search-panel',
            bodyStyle: 'background-color:#d4e0ee;',
            border:false,
            defaults:{border:false},
            items: [{
                xtype: 'searchfield',
                id: config.id || Ext.id(),
                hidden: !Zenoss.settings.enableTreeFilters,
                cls: 'x-hierarchy-search',
                enableKeyEvents: true,
                ref: 'searchfield'
            }, {
                xtype: 'panel',
                ui: 'hierarchy',
                padding:'5px 0 0 0',
                items: oldConfig.items,
                flex: 1,
                autoScroll: true,
                regSearchListeners: function(listeners) {
                    this.ownerCt.query('.searchfield')[0].on(listeners);
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

/**
 *  Right click handlers for nodes.
 **/
Zenoss.treeContextMenu = function(view, node, item, index, e, opti) {
    // Register the context node with the menu so that a Menu Item's handler function can access
    // it via its parentMenu property.
    var tree = view.panel;
    if (!tree.contextMenu) {
        tree.contextMenu = new Ext.menu.Menu({
            items: [{
                ref: 'refreshtree',
                text: _t('Refresh Tree'),
                handler: function(item, e) {
                    var node = item.parentMenu.contextNode;
                    var tree = item.parentMenu.tree;
                    tree.getStore().load({
                        callback: function() {
                            tree.getRootNode().expand();
                            if (tree.getRootNode().childNodes.length) {
                                tree.getRootNode().childNodes[0].expand();
                            }
                        }
                    });
                }
            },{
                ref: 'expandall',
                text: _t('Expand All'),
                handler: function(item, e) {
                    var node = item.parentMenu.contextNode,
                    tree = item.parentMenu.tree;
                    tree.expandAll();
                }
            },{
                ref: 'collapsall',
                text: _t('Collapse All'),
                handler: function(item, e) {
                    var node = item.parentMenu.contextNode,
                    tree = item.parentMenu.tree;
                    tree.collapseAll();
                    // by default we usually expand the first child
                    tree.getRootNode().expand();
                    if (tree.getRootNode().childNodes.length) {
                        tree.getRootNode().childNodes[0].expand();
                    }
                }
            },'-', {
                ref: 'expandnode',
                text: _t('Expand Node'),
                handler: function(item, e) {
                    var node = item.parentMenu.contextNode;
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
                    href = window.location.protocol + '//' + window.location.host + window.location.pathname;
                    if (node && node.data.uid) {
                        tree = item.parentMenu.tree;
                        path = tree.createDeepLinkPath(node);
                        window.open(href + '#' + path);
                    }
                }
            }]
        });
    }
    var c = tree.contextMenu;
    c.tree = tree;
    c.contextNode = node;
    e.preventDefault();
    c.showAt(e.getXY());
};


/**
 * @class Zenoss.HierarchyTreePanel
 * @extends Ext.tree.TreePanel
 * Base classe for most of the trees that appear on the left hand side
 * of various pages
 **/
Ext.define('Zenoss.HierarchyTreePanel', {
    extend: 'Ext.tree.TreePanel',
    alias: ['widget.HierarchyTreePanel'],
    constructor: function(config) {
        Ext.applyIf(config, {
            enableDragDrop:true
        });
        config.listeners = config.listeners || {};
        Ext.applyIf(config.listeners, {
            itemcontextmenu: Zenoss.treeContextMenu,
            scope: this
        });

        config.viewConfig = config.viewConfig || {}; 
        if(config.enableDragDrop){
            Ext.applyIf(config.viewConfig, {
                loadMask: true,
                plugins: {
                    ptype: 'treeviewdragdrop',
                    enableDrag: Zenoss.Security.hasPermission('Change Device'),
                    enableDrop: Zenoss.Security.hasPermission('Change Device'),
                    ddGroup: config.ddGroup
                }
            });
        }else{
            Ext.applyIf(config.viewConfig, {        
                loadMask:true
            });
        }
        Ext.applyIf(config, {
            ui: 'hierarchy',
            frame: false,
            useArrows: true,
            autoScroll: true,
            relationshipIdentifier: null,
            containerScroll: true,
            selectRootOnLoad: true,
            rootVisible: false,
            rootDepth: config.rootVisible ? 0 : 1,
            allowOrganizerMove: true,
            hideHeaders: true,
            layout: 'fit',
            columns: [{
                xtype: 'treecolumn',
                flex: 1,
                dataIndex: 'text',
                renderer: function(value, l, n) {
                    if (Ext.isString(value)) {
                        return value;
                    }
                    var parentNode = n.parentNode;                    
                    if(parentNode.data.root == true){   
                        return Ext.String.format("<span class='rootNode'>{0} <span title='{1}'>({2})</span></span>", value.text, value.description, value.count); 
                    }else{
                        return Ext.String.format("<span class='subNode'>{0}</span> <span title='{1}'>({2})</span>", value.text, value.description, value.count);
                    }
                    
                }
            }]

        });
        if (config.router) {
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
        var root = config.root || {};
        if (config.directFn && !config.loader) {
            var modelId = Ext.String.format('Zenoss.tree.{0}Model', config.id);

            var model = Ext.define(modelId, {
                extend: 'Ext.data.Model',
                treeId: config.id,
                idProperty: config.idProperty || 'uid',
                getOwnerTree: function() {
                    return Ext.getCmp(this.treeId);
                },
                proxy: {
                    type: 'direct',
                    directFn: config.directFn,
                    paramOrder: ['uid']
                },
                fields: [{
                    name: 'hidden',
                    type: 'boolean'
                }, {
                    name: 'leaf',
                    type: 'boolean'
                }, {
                    name: 'uid',
                    type: 'string'
                }, {
                    name: 'text',
                    type: 'object'
                }, {
                    name: 'id',
                    type: 'string'
                }, {
                    name: 'path',
                    type: 'string'
                }, {
                    name: 'iconCls',
                    type: 'string'
                }, {
                    name: 'uuid',
                    type: 'string'
                }].concat(config.extraFields || [])
            });
            config.store = new Ext.create('Ext.data.TreeStore', {
                model: modelId,
                nodeParam: 'uid',
                defaultRootId: root.id,
                uiProviders: {
                    // 'hierarchy': Zenoss.HierarchyTreeNodeUI
                }
            });
            Ext.destroyMembers(config, 'directFn', 'ddGroup');
        }
        Ext.applyIf(root, {
            id: root.id,
            uid: root.uid,
            text: _t(root.text || root.id)
        });
        this.root = root;
        this.stateHash = {};
        if (config.stateful) {
            this.stateEvents = this.stateEvents || [];
            this.stateEvents.push('expandnode', 'collapsenode');
        }

        Zenoss.HierarchyTreePanel.superclass.constructor.apply(this, arguments);
    },
    setNodeVisible: function(nodeId, visible) {
        var node = this.getNodeById(nodeId),
            view = this.getView(),
            el = Ext.fly(view.getNodeByRecord(node));
        if (el) {
            el.setVisibilityMode(Ext.Element.DISPLAY);
            el.setVisible(visible);
        }
    },
    getState: function() {
            return {stateHash: this.stateHash};
    },
    applyState: function(state) {
        if (state) {
            Ext.apply(this, state);
            this.setStateListener();
        }
    },
    setStateListener: function() {
            this.store.on({
                load: { scope: this, fn: function() {
                    for (var p in this.stateHash) {
                        if (this.stateHash.hasOwnProperty(p)) {
                            this.expandPath(this.stateHash[p]);
                        }
                    }
                }}
            });
    },
    initEvents: function() {
        var me = this;
        Zenoss.HierarchyTreePanel.superclass.initEvents.call(this);
  
        if (this.selectRootOnLoad && !Ext.History.getToken()) {
            this.getRootNode().on('expand', function() {
                // The first child is our real root
                if (this.getRootNode().firstChild) {
                    me.addHistoryToken(this.getRootNode().firstChild);
                    me.getRootNode().firstChild.expand();
                    me.getSelectionModel().select(this.getRootNode().firstChild);
                }
            }, this, {single: true});
        }else {

            // always expand the first shown root if we can
            this.getRootNode().on('expand', function() {
                if (this.getRootNode().firstChild) {
                    this.getRootNode().firstChild.expand();
                }
            }, this, {single: true});
        }
        this.addEvents('filter');
        this.on('click', this.addHistoryToken, this);
        this.on({
             beforeexpandnode: function(node) {
                this.stateHash[node.id] = node.getPath();
            },
             beforecollapsenode: function(node) {
                delete this.stateHash[node.id];
                var tPath = node.getPath();
                for (var t in this.stateHash) {
                    if (this.stateHash.hasOwnProperty(t)) {
                        if (-1 !== this.stateHash[t].indexOf(tPath)) {
                            delete this.stateHash[t];
                        }
                    }
                }
            }
        });    // add some listeners for state
    },
    addHistoryToken: function(node) {
        Ext.History.add(this.id + Ext.History.DELIMITER + node.get('id'));
    },
    update: function(data) {
        function doUpdate(root, data) {
            Ext.each(data, function(datum) {
                var node = root.findChild('id', datum.id);
                if (node) {
                    node.data = datum;
                    node.setText(node.data.text);
                    doUpdate(node, datum.children);
                }
            });
        }
        doUpdate(this.getRootNode(), data);

    },
    selectByToken: function(nodeId) {
        nodeId = unescape(nodeId);
        var root = this.getRootNode(),
            selNode = Ext.bind(function() {
            var sel = this.getSelectionModel().getSelectedNode(),
                uid, child;
            if (!(sel && nodeId === sel.id)) {
                if (nodeId.indexOf('/') == -1) {
                    uid = nodeId.replace(/\./g, '/');
                }else {
                    uid = nodeId;
                }
                child = root.findChild('uid', uid, true);

                // try the id as well
                if (Ext.isEmpty(child)) {
                    child = root.findChild('id', nodeId, true);
                }
                if (child) {
                    this.getSelectionModel().select(child);
                    this.expandToChild(child);
                }
            }
        }, this);

        if (!root.isLoaded()) {
            // Listen on expand because if we listen on the store's load expand
            // gets double-called.
            root.on('expand', selNode, this, {single: true});
        } else {
            selNode();
        }
    },
    /**
     * This takes a node anywhere in the hierarchy and
     * will go back up to the parents and expand until it hits
     * the root node. This is a workaround for selectPath being nonfunctional
     * in Ext4
     *@param Ext.data.NodeInterface child
     **/
    expandToChild: function(child) {
        var parentNode = child.parentNode;

        // go back up and expand to this point
        while (parentNode) {
            // at the pseudo root nothing is further up
            if (Ext.isEmpty(parentNode.get('path'))) {
                break;
            }

            if (!parentNode.isExpanded() && parentNode.hasChildNodes()) {
                parentNode.expand();
            }
            parentNode = parentNode.parentNode;
        }
    },
    createDeepLinkPath: function(node) {
        var path = this.id + Ext.History.DELIMITER + node.data.uid.replace(/\//g, '.');
        return path;
    },
    getNodePathById: function(nodeId) {
        var part,
            depth = this.root.uid.split('/').length - this.rootDepth,
            parts = nodeId.split('.'),
            curpath = parts.slice(0, depth).join('.');

        parts = parts.slice(depth);

        var path = [this.getRootNode().data.uid];

        while (part = parts.shift()) {
            // this adjusts the path for things like "Service.Linux.devices.Dev1"
            // where "devices" is the relationshipIdentifier"
            if (this.relationshipIdentifier && part == this.relationshipIdentifier) {
                curpath = [curpath, part, parts.shift()].join('.');
            }else {
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
            listeners.change = this.filterTree;
        }
        if (this.searchField && this.ownerCt.regSearchListeners) {
            this.ownerCt.regSearchListeners(listeners);
        }
        this.getRootNode().expand(false, true, function(node) {
            node.expandChildNodes();
        });
    },
    filterTree: function(e) {
        if (!this.onFilterTask) {
            this.onFilterTask = new Ext.util.DelayedTask(function() {
                 this.doFilter(e);
            }, this);
        }

        this.onFilterTask.delay(500);
    },
    expandAll: function() {
        // we have a hidden pseudo-root so we need to
        // expand all from the first visible root
        if (this.getRootNode().firstChild) {
            this.getRootNode().firstChild.expand(true);
        }else {
            this.callParent(arguments);
        }
    },
    doFilter: function(e) {
        var text = e.getValue(),
            me = this,
            root = this.getRootNode();
        this.fireEvent('filter', e);
        if (this.hiddenPkgs) {
            Ext.each(this.hiddenPkgs, function(n) {
                me.setNodeVisible(n.getId(), true);
            });
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

        root.cascadeBy(function(n) {
            var attr = n.data.text;
            if (Ext.isObject(attr)) {
                attr = attr.text;
            }

            if (!n.isRoot()) {
                if (re.test(attr)) {

                    var parentNode = n.parentNode;
                    while (parentNode) {
                        me.setNodeVisible(parentNode.getId(), true);
                        parentNode.expand();
                        parentNode = parentNode.parentNode;
                    }
                    // the cascade is stopped on this branch
                    return false;
                } else {
                    me.setNodeVisible(n.getId(), false);
                    this.hiddenPkgs.push(n);
                }
            }
            // continue cascading down the tree from this node
            return true;
        }, this);

        this.doLayout();
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
        var contextUid = parentNode.data.uid;
        Ext.applyIf(params, {
            contextUid: contextUid
        });

        this.addTreeNode(params);
    },

    addTreeNode: function(params) {
        var callback = function(provider, response) {
            var result = response.result;
            var me = this;
            if (result.success) {
                // look for another node on result and assume it's the new node, grab it's id
                // TODO would be best to normalize the names of result node
                var nodeId = Zenoss.env.PARENT_CONTEXT + '/' + params.id;
                this.getStore().load({
                    callback: function() {
                        me.selectByToken(nodeId);
                    }
                });

            }
            else {
                Ext.Msg.alert('Error', result.msg);
            }
        };

        this.addNodeFn(params, Ext.bind(callback, this));
    },

    deleteSelectedNode: function() {
        var node = this.getSelectionModel().getSelectedNode();
        var me = this;
        var parentNode = node.parentNode;
        var uid = node.get('uid');
        var params = {uid: uid};
        function callback(provider, response) {
            // Only update the UI if the response indicates success
            if (Zenoss.util.isSuccessful(response)) {
                me.getStore().load({
                    callback: function() {
                        me.selectByToken(parentNode.get('uid'));
                    }
                });


            }
        }

        // all hierarchytreepanel's have an invisible root node with depth of 0
        if (node.getDepth() <= 1) {
            Zenoss.message.error(_t('You can not delete the root node'));
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
    },
    refresh: function(callback, scope) {
        this.getStore().load({
            scope: this,
            callback: function() {
                this.getRootNode().expand();
                Ext.callback(callback, scope || this);
                if (this.getRootNode().childNodes.length) {
                    this.getRootNode().childNodes[0].expand();
                }
            }
        });
    }
}); // HierarchyTreePanel

})();

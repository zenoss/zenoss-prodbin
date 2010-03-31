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

Zenoss.SlidingCardLayout = Ext.extend(Ext.layout.CardLayout, {
    setActiveItem: function(index) {
        var C = this.container,
            B = C.body,
            card = C.getComponent(index),
            active = this.activeItem,
            activeIndex = C.items.items.indexOf(active);
        if(card!=active) {
            if(active) {
                if(card) {
                    C.fireEvent('beforecardchange', C, card, index, active, activeIndex);
                    if (!card.rendered) {
                        this.renderItem(card, index, C.getLayoutTarget());
                    }
                    card.show();
                    if(card.doLayout && (this.layoutOnCardChange || 
                                         !card.rendered)) {
                        card.doLayout();
                    }
                    var _done = 0;
                    function shiftsCallback() {
                        _done++;
                        if (_done==2) 
                            C.fireEvent('cardchange', C, card, index, active,
                                        activeIndex);
                    }
                    var x = B.getX(),
                        w = B.getWidth(),
                        s = [x - w, x + w],
                        cfg = {
                            duration: 0.25,
                            easing: 'easeInStrong',
                            opacity: 0,
                            callback: shiftsCallback
                        };
                    card.el.setY(B.getY());
                    card.el.setX((activeIndex < index ? s[1] : s[0]));
                    active.el.shift(Ext.applyIf({
                        x: activeIndex < index ? s[0] : s[1]
                    }, cfg));
                    card.el.shift(Ext.applyIf({
                        x:x,
                        opacity: 1
                    }, cfg));
                }
            }
            this.activeItem = card;
            this.layout();
        }

    }

});

Ext.Container.LAYOUTS['slide'] = Zenoss.SlidingCardLayout;


Zenoss.HorizontalSlidePanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        this.headerText = new Ext.Toolbar.TextItem({
            html: (config && config.text) ? config.text : ''
        });
        config = Ext.applyIf(config || {}, {
            cls: 'subselect',
            border: false,
            defaults: {
                border: false
            },
            layout: 'slide',
            activeItem: 0
        });
        var items = [];
        Ext.each(config.items, function(item, index){
            var headerText = new Ext.Toolbar.TextItem({
                html: (item && item.text) ? item.text : ''
            });
            var navButton = new Ext.Button({
                text: (item && item.buttonText) ? item.buttonText : '',
                cls: index ? 'toleft' : 'toright',
                handler: function() {
                    this.layout.setActiveItem(index ? 0 : 1);
                    
                },
                scope: this
            }, this);
            navButton.hide();
            items.push({
                layout: 'fit',
                border: false,
                defaults: {
                    border: false
                },
                tbar: {
                    border: false,
                    cls: 'subselect-head',
                    height: 37,
                    items: [headerText, '->', navButton]
                },
                items:[item],
                listeners: {
                    render: function(card) {
                        card.card = card.items.items[0];
                        card.card.parentCard = card;
                        card.headerText = headerText;
                        card.navButton = navButton;
                        var setHeaderText = function(text) {
                            this.headerText.setText(text);
                        };
                        var setButtonText = function(text) {
                            this.navButton.setText(text);
                        };
                        card.setHeaderText = setHeaderText.createDelegate(card);
                        card.setButtonText = setButtonText.createDelegate(card);
                    }
                }
            });
        }, this);
        config.items = items;
        Zenoss.HorizontalSlidePanel.superclass.constructor.call(this, config);
    },
    initEvents: function() {
        this.addEvents('beforecardchange');
        this.addEvents('cardchange');
        Zenoss.HorizontalSlidePanel.superclass.initEvents.call(this);
    }
});

Ext.reg('horizontalslide', Zenoss.HorizontalSlidePanel);


Ext.ns('Zenoss.nav');

var ZN = Zenoss.nav;

ZN.register = function (obj) {
    for (var type in obj) {
        var items = ZN[type] = ZN[type] || [],
            toadd = obj[type];
        Ext.each(toadd, function(item) {
            if (!(item in items)) {
                items.push(item);
            }
        });
    }
};

Zenoss.SubselectionNodeUI = Ext.extend(Ext.tree.TreeNodeUI, {
    render: function() {
        Zenoss.SubselectionNodeUI.superclass.render.call(this);
        Ext.removeNode(this.getIconEl());
    }
});

Zenoss.SubselectionNode = Ext.extend(Ext.tree.TreeNode, {
    constructor: function(config) {
        Ext.applyIf(config, {
            leaf: true,
            uiProvider: Zenoss.SubselectionNodeUI
        });
        Zenoss.SubselectionNode.superclass.constructor.call(this, config);
        this.addEvents('render');
    },
    render: function(bulkRender) {
        Zenoss.SubselectionNode.superclass.render.call(this, bulkRender);
        this.fireEvent('render', this);
    }

});

Ext.tree.TreePanel.nodeTypes.subselect = Zenoss.SubselectionNode;


Zenoss.SubselectionPanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        var id = config.id || Ext.id();
        Ext.applyIf(config, {
            id: id,
            layout: 'fit',
            border: false,
            bodyStyle: { 'margin-top' : 10 },
            items: [{
                xtype:'treepanel',
                selModel: new Ext.tree.DefaultSelectionModel({
                    listeners: {
                        selectionchange: function(sm, node) {
                            if (node) {
                                var action = node.attributes.action;
                                if (action) {
                                    if (Ext.isString(this.target)) {
                                        this.target = Ext.getCmp(this.target);
                                    }
                                    action.call(node, node, this.target);
                                }
                            }
                        },
                        scope: this
                    }
                }),
                id: 'subselecttreepanel' + id,
                border: false,
                rootVisible: false,
                root : {nodeType: 'node'}            }]
        });
        Zenoss.SubselectionPanel.superclass.constructor.call(this, config);
    },
    initComponent: function() {
        Zenoss.SubselectionPanel.superclass.initComponent.call(this);
        this.treepanel = Ext.getCmp('subselecttreepanel' + this.id);
    },
    setContext: function(uid) {
        var type = Zenoss.types.type(uid),
            nodes = Zenoss.nav[type];
        if (nodes) {
            Ext.each(nodes, function(node) {
                Ext.applyIf(node, {
                    nodeType: 'subselect'
                });
            });
            var root = new Ext.tree.AsyncTreeNode({
                children: nodes,
                listeners: {
                    load: function(node){
                        var toselect = node.firstChild;
                        if (toselect) {
                            if (toselect.rendered) {
                                toselect.select();
                            } else {
                                toselect.on('render', function(node){
                                    node.select();
                                });
                            }
                        }
                    },
                    scope: this
                }
            });
            this.treepanel.setRootNode(root);
        }
    }
});

Zenoss.DetailNavTreePanel = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config){
        Ext.applyIf(config, {
            autoHeight: true,
            selModel: new Ext.tree.DefaultSelectionModel({
                listeners: {
                    selectionchange: function(sm, node) {
                        var itemSelModel;
                        if (node) {
                            this.ownerCt.onSelectionChange(this.ownerCt, node);
                            this.ownerCt.items.each(function(item){
                                itemSelModel = item.getSelectionModel();
                                if ( itemSelModel !== sm && itemSelModel.getSelectedNode() ) {
                                    itemSelModel.getSelectedNode().unselect(true);
                                }
                            });
                        }
                    },
                    scope: this
                }
            }),
            id: 'subselecttreepanel' + config.idSuffix,
            ref: 'subselecttreepanel',
            border: false,
            rootVisible: false,
            cls: 'x-tree-noicon',
            root : {nodeType: 'node'}
        });
        Zenoss.DetailNavTreePanel.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        //called to load the nav tree
        this.ownerCt.contextId = uid;
        this.setRootNode([]);
        this.ownerCt.getNavConfig(uid);
    }
});
Ext.reg('detailnavtreepanel', Zenoss.DetailNavTreePanel);

Ext.reg('subselection', Zenoss.SubselectionPanel);
/**
 * Used to manage and display detail navigation tree for a contextId
 * 
 * @class Zenoss.DetailNavPanel
 * @extends Zenoss.SubselectionPanel
 */
Zenoss.DetailNavPanel = Ext.extend(Zenoss.SubselectionPanel,{
    /**
     * @cfg {function} onGetNavConfig abstract function; hook to provide more nav items
     * @param {string} uid; item to get nav items for
     */
    onGetNavConfig: function(uid){ return []; },
    /**
     * Called when an item in detail nav is selected
     * @param {object} this, the DetailNavPanel
     * @param {object} the navigation node selected
     */
    onSelectionChange: Ext.emptyFn,
    /**
     * Filter out from being in the detail nav; used to filter out nav nodes
     * and the content panels. Return true if it should be kept, false otherwise
     * @param {DetailNavPanel}
     * @param {Object} config
     */
    filterNav: function(detailNav, config) {return true;},
    /**
     * The object id for which the detail navigation belongs to
     */
    contextId: null,
    /**
     * Menu ids used to get non dialog menus to be used in navigation;
     * Empty or null if no nav from old menu items is desired
     */
    menuIds: ['More','Manage','Edit', 'Actions','Add','TopLevel'],
    /**
     * map of nav id to panel configuration
     */
    panelConfigMap: null,
    constructor: function(config) {
        Ext.applyIf(config, {
            id: Ext.id(),
            layout: 'fit',
            border: false,
            bodyStyle: { 'margin-top' : 10 }
        });
        config.items = this.getConfigItems(config.id, config.items);
        Zenoss.DetailNavPanel.superclass.constructor.call(this, config);
    },initEvents: function() {
        this.addEvents( 
        /**
         * @event navloaded
         * Fires after the navigation has been loaded
         * @param {DetailNavPanel} this The DetailNavPanel
         * @param {Object} The Navigation config loaded
         */'navloaded' );
        Zenoss.DetailNavPanel.superclass.initEvents.call(this);
    },
    setContext: function(uid) {
        this.items.each(function(item){
            item.setContext(uid);
        });
    },
    getNavConfig: function(uid){
        //Direct call to get nav configs from server
        var me = this;
        var myCallback = function(provider, response) {
            var detailConfigs = response.result.detailConfigs;
            var filterFn = function(val) {
                return this.filterNav(this, val);
            };
            detailConfigs = Zenoss.util.filter(detailConfigs, filterFn, this);
            var panelMap = [];
            Ext.each(detailConfigs, function(val) {
                panelMap[val.id] = val;
            });
            this.panelConfigMap = panelMap;
            var nodes = this.onGetNavConfig(this.contextId);
            if (!Ext.isDefined(nodes) || nodes === null){
                nodes = [];
            }
            if (detailConfigs){
                nodes = nodes.concat(detailConfigs);
            }
            this.setNavTree(nodes);
        };
        var args = {
            'uid': uid
        };
        if (this.menuIds !== null && this.menuIds.length >= 1){
            args['menuIds'] = this.menuIds;
        } 
        Zenoss.remote.DetailNavRouter.getDetailNavConfigs(args, myCallback, this);
    },
    setNavTree: function(nodes){
        //get any configs registered by the page
        if (nodes) {
            Ext.each(nodes, function(node) {
                Ext.applyIf(node, {
                    nodeType: 'subselect'
                });
            });
            var root = new Ext.tree.AsyncTreeNode({
                children: nodes,
                listeners: {
                    load: function(node){
                        var toselect = node.firstChild;
                        if (toselect) {
                            if (toselect.rendered) {
                                toselect.select();
                            } else {
                                toselect.on('render', function(node){
                                    node.select();
                                });
                            }
                        }
                    },
                    scope: this
                }
            });
            this.treepanel.setRootNode(root);
            Ext.each(nodes, function(navConfig){
                this.fireEvent('navloaded', this, navConfig);
            }, this);
            
        }
    },
    getConfigItems: function(id, otherItems){
        var firstItem = this.getFirstItem(id);
        return [ firstItem ].concat(otherItems || []);
    },
    getFirstItem: function(id){
        return {
            xtype:'detailnavtreepanel',
            idSuffix: id
        };
    }
});

Ext.reg('detailnav', Zenoss.DetailNavPanel);
})();

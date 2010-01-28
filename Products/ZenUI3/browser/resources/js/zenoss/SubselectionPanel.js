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

    },

});

Ext.Container.LAYOUTS['slide'] = Zenoss.SlidingCardLayout;


Zenoss.HorizontalSlidePanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        this.headerText = new Ext.Toolbar.TextItem({
            html: (config && config.text) ? config.text : ''
        });
        var config = Ext.applyIf(config || {}, {
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
                    items: [headerText, '->', navButton],
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
                        }
                        var setButtonText = function(text) {
                            this.navButton.setText(text);
                        }
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
        })
    }
}

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
        Ext.applyIf(config, {
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
                id: 'subselecttreepanel',
                border: false,
                rootVisible: false,
                root : {nodeType: 'node'}            }]
        });
        Zenoss.SubselectionPanel.superclass.constructor.call(this, config);
    },
    initComponent: function() {
        Zenoss.SubselectionPanel.superclass.initComponent.call(this);
        this.treepanel = Ext.getCmp('subselecttreepanel');
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
                                    node.select()
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

Ext.reg('subselection', Zenoss.SubselectionPanel);


})();
